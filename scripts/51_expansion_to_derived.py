"""Rebuild the pilot-lineage derived tables from the fleet's per-recording expansion outputs, so the
analysis scripts (04/06/33/47/48/...) regenerate on the FULL dataset.

Memory-safe by design: per-recording feature parquets are ~11 MB each and there are ~13k of them
(~100+ GB concatenated), so we STREAM one file at a time and compute per-recording (region) and
(region, stage) medians incrementally — never concatenating the whole corpus.

Inputs (local, synced from S3 by fleet/reanalyze.sh):
  data/derived/expansion/features/<rid>.parquet   cols: bdsp_id,age,sex,label,stage,region,+FEATCOLS
  data/derived/expansion/gate/<rid>.json          gate probs
  data/derived/expansion/provenance/<rid>.json    bdsp_id,age,sex,label,...

Outputs (pilot-lineage paths the analyses read):
  data/derived/recording_features.parquet  (+ _py)         one row per (bdsp_id, region), median over segments
  data/derived/stage_recording_features.parquet            one row per (bdsp_id, region, stage)
  data/derived/recording_asymmetry.parquet (+ _py)         homologous L-R log asymmetry (approx; see NOTE)
  data/derived/gate_probs.parquet                          bdsp_id, p_abnormal, p_focal, p_generalized, p_slowing, label
  metadata/cohort_metadata_full.csv  (+ overwrites cohort_metadata.csv, pilot backed up)

NOTE (asymmetry): the exact pilot asym is median_seg(logL - logR); with no per-segment id across regions
here we use median_seg(logL) - median_seg(logR). Close, not identical — slightly shifts lateralization
AUROCs. To make it exact in future runs, emit a per-segment index from scripts/30 process_one.
"""
from __future__ import annotations
import glob, io, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

FEAT = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
        "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
LOGB = {"delta": "log_delta", "theta": "log_theta", "alpha": "log_alpha", "beta": "log_beta", "gamma": "log_gamma"}
PAIRS = {"temporal": ("L_temporal", "R_temporal"), "parasagittal": ("L_parasagittal", "R_parasagittal"),
         "ch_Fp1-F7": ("Fp1-F7", "Fp2-F8"), "ch_F7-T3": ("F7-T3", "F8-T4"),
         "ch_T3-T5": ("T3-T5", "T4-T6"), "ch_T5-O1": ("T5-O1", "T6-O2"),
         "ch_Fp1-F3": ("Fp1-F3", "Fp2-F4"), "ch_F3-C3": ("F3-C3", "F4-C4"),
         "ch_C3-P3": ("C3-P3", "C4-P4"), "ch_P3-O1": ("P3-O1", "P4-O2")}
EXP = os.environ.get("EXP_DIR", "data/derived/expansion")      # local dir OR rclone remote (bdsp:...)
DER = Path(os.environ.get("DER_OUT", "data/derived"))          # override for safe testing
META = Path(os.environ.get("META_OUT", "metadata"))
REMOTE = ":" in EXP and not Path(EXP).exists()                 # stream from S3 instead of local disk
RC = os.path.expanduser(os.environ.get("RCLONE_BIN", "~/.local/bin/rclone"))


def list_files(sub, ext):
    if REMOTE:
        out = subprocess.run([RC, "lsf", f"{EXP}/{sub}/"], capture_output=True, text=True).stdout
        return [f"{EXP}/{sub}/{l.strip()}" for l in out.splitlines() if l.strip().endswith(ext)]
    return [str(p) for p in sorted((Path(EXP) / sub).glob(f"*{ext}"))]


def read_parquet_any(path):
    if REMOTE:
        return pd.read_parquet(io.BytesIO(subprocess.run([RC, "cat", path], capture_output=True).stdout))
    return pd.read_parquet(path)


def read_json_any(path):
    if REMOTE:
        return json.loads(subprocess.run([RC, "cat", path], capture_output=True, text=True).stdout or "{}")
    return json.loads(Path(path).read_text())


def main():
    feats = list_files("features", ".parquet")
    if not feats:
        print(f"no feature parquets under {EXP}/features — nothing to do", file=sys.stderr); sys.exit(1)
    print(f"streaming {len(feats)} recordings from {EXP}/features  (remote={REMOTE})")
    have = [c for c in FEAT if c in read_parquet_any(feats[0]).columns]   # probe schema once

    def work(f):
        """Read one recording, return (rec_rows, stage_rows) — per-region + per-(region,stage) medians."""
        try:
            d = read_parquet_any(f)
        except Exception as e:
            print(f"  skip {os.path.basename(f)}: {e}"); return [], []
        meta = {"bdsp_id": d["bdsp_id"].iloc[0], "age": d["age"].iloc[0],
                "sex": d["sex"].iloc[0], "label": d["label"].iloc[0]}
        gr = d.groupby("region"); med = gr[have].median(); n = gr.size()
        recs = [{**meta, "region": region, "n_segments": int(n[region]), **row.to_dict()}
                for region, row in med.iterrows()]
        gs = d.groupby(["region", "stage"]); smed = gs[have].median(); sn = gs.size()
        stages = [{**meta, "region": region, "stage": stage, "n_seg": int(sn[(region, stage)]), **row.to_dict()}
                  for (region, stage), row in smed.iterrows()]
        return recs, stages

    rec_rows, stage_rows = [], []
    workers = int(os.environ.get("REANALYZE_WORKERS", "24"))     # parallel S3 reads (I/O-bound)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (recs, stages) in enumerate(ex.map(work, feats)):
            rec_rows.extend(recs); stage_rows.extend(stages)
            if (i + 1) % 1000 == 0:
                print(f"  {i+1}/{len(feats)}", flush=True)

    rf = pd.DataFrame(rec_rows)
    DER.mkdir(parents=True, exist_ok=True)
    rf.to_parquet(DER / "recording_features.parquet")
    rf.to_parquet(DER / "recording_features_py.parquet")               # R7: both filenames
    print(f"recording_features: {rf.bdsp_id.nunique()} recordings, {len(rf)} rows")
    pd.DataFrame(stage_rows).to_parquet(DER / "stage_recording_features.parquet")
    print(f"stage_recording_features: {len(stage_rows)} rows")

    # homologous asymmetry from per-recording region medians (approx; see NOTE)
    med_idx = rf.set_index(["bdsp_id", "region"])
    arows = []
    for bid, sub in med_idx.groupby(level=0):
        s = sub.droplevel(0)
        r = {"bdsp_id": bid, "age": s["age"].iloc[0], "sex": s["sex"].iloc[0], "label": s["label"].iloc[0]}
        for name, (L, R) in PAIRS.items():
            if L in s.index and R in s.index:
                for band, col in LOGB.items():
                    if col in s.columns:
                        r[f"asym_{name}_{band}"] = float(s.loc[L, col]) - float(s.loc[R, col])
        arows.append(r)
    asym = pd.DataFrame(arows)
    asym.to_parquet(DER / "recording_asymmetry.parquet")
    asym.to_parquet(DER / "recording_asymmetry_py.parquet")
    print(f"recording_asymmetry: {len(asym)} recordings")

    # gate probs from the gate JSONs
    grows = []
    for g in list_files("gate", ".json"):
        try:
            j = read_json_any(g)
        except Exception:
            continue
        grows.append({"bdsp_id": j.get("bdsp_id", os.path.basename(g)[:-5]),
                      "p_abnormal": j.get("normal_head_prob"),
                      "p_focal": j.get("p_focal"), "p_generalized": j.get("p_generalized")})
    gp = pd.DataFrame(grows).drop_duplicates("bdsp_id")
    if not gp.empty:
        gp["p_slowing"] = gp[["p_focal", "p_generalized"]].max(axis=1)
        lab = rf[["bdsp_id", "label"]].drop_duplicates("bdsp_id")
        gp = gp.merge(lab, on="bdsp_id", how="left")
        gp.to_parquet(DER / "gate_probs.parquet")
        print(f"gate_probs: {len(gp)} recordings")

    # cohort metadata (full) — write a full copy; overwrite the pilot one (backed up) so scripts pick it up
    cm_full = rf[["bdsp_id", "age", "sex", "label"]].drop_duplicates("bdsp_id")
    META.mkdir(parents=True, exist_ok=True)
    cm_full.to_csv(META / "cohort_metadata_full.csv", index=False)
    pilot = META / "cohort_metadata.csv"
    if pilot.exists() and not (META / "cohort_metadata_pilot.csv").exists():
        (META / "cohort_metadata_pilot.csv").write_text(pilot.read_text())     # one-time backup
    # union: keep any extra pilot columns where present, else the full age/sex/label
    if pilot.exists():
        old = pd.read_csv(pilot)
        keep = [c for c in old.columns if c not in ("age", "sex", "label")]
        merged = cm_full.merge(old[keep], on="bdsp_id", how="left") if "bdsp_id" in old.columns else cm_full
    else:
        merged = cm_full
    merged.to_csv(pilot, index=False)
    print(f"cohort_metadata: {len(merged)} recordings (pilot backed up to cohort_metadata_pilot.csv)")


if __name__ == "__main__":
    main()
