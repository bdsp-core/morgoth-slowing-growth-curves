#!/usr/bin/env python3
"""Build data/derived/recording_meta.parquet + recording_labels.parquet — the two canonical per-recording
tables Table 1 (SAP §10) reads.

WHY NOT scripts/33: that assembles the ledger from the per-eeg `.done` sidecars, which live in S3 and are
not on this machine (and the creds have since expired). Every field Table 1 needs is recoverable from the
segment_summary partitions that ARE local, so we derive them instead of re-downloading 27k sidecars:
    recording_seconds / n_segments / n_usable / frac_artifact / stage_frac  <- segment_summary
    age                                                                     <- metadata/ages_v6.parquet
    sex / src / panel / label fields                                        <- v6 manifest + labels_sap
`included` = the recording produced usable (non-artifact) segments, which IS the run's inclusion criterion.

AGE: taken ONLY from metadata/ages_v6.parquet (tracked in git; 99.6% exact, >89 binned to 90 for HIPAA
Safe Harbor). Never from the manifest, whose `age` is integer and partly wrong.
Run: PYTHONPATH=src python scripts/34_recording_meta_from_segments.py"""
import glob, os
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor

STAGES = ["W", "N1", "N2", "N3", "REM"]
SS = "data/derived/segment_summary"


def one(f):
    try:
        d = pd.read_parquet(f, columns=["eeg_id", "segment", "t_start_s", "stage", "artifact_flag", "p_slowing"])
    except Exception:
        return None
    if d.empty:
        return None
    n = len(d)
    ok = ~d.artifact_flag.astype(bool)
    n_ok = int(ok.sum())
    # segment step is 14 s; recording span = last segment start + one 15 s window
    secs = float(d.t_start_s.max()) + 15.0 if d.t_start_s.notna().any() else np.nan
    u = d[ok]
    sf = {f"frac_{s}": float((u.stage == s).mean()) if n_ok else 0.0 for s in STAGES}
    return {"eeg_id": d.eeg_id.iloc[0], "n_segments": n, "n_usable": n_ok,
            "frac_artifact": 1.0 - n_ok / n, "recording_seconds": secs, "stage_frac": sf,
            "p_slowing_mean": float(u.p_slowing.mean()) if n_ok and u.p_slowing.notna().any() else np.nan}


if __name__ == "__main__":
    files = sorted(glob.glob(f"{SS}/eeg_id=*/part.parquet"))
    print(f"scanning {len(files):,} segment_summary partitions ...", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        for i, r in enumerate(ex.map(one, files, chunksize=64)):
            if r:
                rows.append(r)
            if (i + 1) % 5000 == 0:
                print(f"  {i+1:,}/{len(files):,}", flush=True)
    meta = pd.DataFrame(rows)
    print(f"segment-derived: {len(meta):,} recordings")

    man = pd.read_parquet("data/manifest/report_manifest_v6.parquet").drop_duplicates("eeg_id")
    ages = pd.read_parquet("metadata/ages_v6.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")

    # recording_meta carries METADATA ONLY. The label fields live in recording_labels and Table 1 merges
    # them on eeg_id — duplicating them here produced a _x/_y column collision that crashed Table 1.
    MAN = [c for c in ["eeg_id", "patient_id", "sex", "bids_task", "panel", "panel_set"]
           if c in man.columns]
    meta = meta.merge(man[MAN], on="eeg_id", how="left")
    meta["age"] = meta.eeg_id.map(ages.age)                     # AUTHORITATIVE, HIPAA-safe
    meta["age_source"] = meta.eeg_id.map(ages.age_source)
    meta["sex"] = meta.sex.astype(str).str[:1].str.upper().where(lambda s: s.isin(["F", "M"]))
    meta["src"] = np.where(meta.get("bids_task").eq("rEEG"), "cohort", "expansion")
    if "panel" not in meta:
        meta["panel"] = False
    meta["panel"] = meta.panel.fillna(False).astype(bool)
    meta["included"] = meta.n_usable > 0                         # produced usable segments
    meta.to_parquet("data/derived/recording_meta.parquet", index=False)

    # recording_labels: label fields keyed on eeg_id (Table 1 merges this onto meta)
    LCOL = [c for c in ["eeg_id", "clean_pair", "clean_normal", "is_abnormal", "has_focal_slow",
                        "has_gen_slow", "focal_side", "focal_region", "focal_band",
                        "gen_topography", "gen_band"] if c in man.columns]
    rl = man[LCOL].copy()
    for c in ["slowing_positive", "slowing_focal", "slowing_gen_pathologic", "slowing_gen_physiologic"]:
        if c in lab.columns:
            rl = rl.merge(lab[["eeg_id", c]], on="eeg_id", how="left")
    rl.to_parquet("data/derived/recording_labels.parquet", index=False)

    inc = meta[meta.included & ~meta.panel]
    print(f"\nwrote data/derived/recording_meta.parquet  {meta.shape}")
    print(f"wrote data/derived/recording_labels.parquet {rl.shape}")
    print(f"included (non-panel): {len(inc):,} recordings / {inc.patient_id.nunique():,} patients")
    print(f"age: {inc.age.notna().sum():,} known, median {inc.age.median():.1f}, max {inc.age.max():.1f} "
          f"(HIPAA: must be <= 90)")
    print(f"length min: median {(inc.recording_seconds/60).median():.1f}  |  >1h: "
          f"{(inc.recording_seconds/60 > 60).mean()*100:.1f}%")
