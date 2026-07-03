"""LOCAL pilot of the full-recording slowing-ingestion pipeline (to validate before the AWS full wave).

Per recording: pull BIDS EDF -> harmonize (io/edf) -> artifact-reject (features/artifact) -> featurize
(features/extract) -> sleep-stage the full recording (morgoth ss_hm_1) -> map stages to 15-s segments
-> per (region, stage) medians -> append to data/derived/expansion_pilot_features.parquet. Drops raw.

Selection is done at the RECORDING level from the repository eeg-metadata (which carries EDF path
components) joined to the report-derived finding flags; filters to 6-48h, report-labeled, NOT already
in metadata/cohort_metadata.csv.

Run: python scripts/26_slowing_ingest_pilot.py [N]   (default N=6)
"""
from __future__ import annotations
import sys, subprocess, tempfile, shutil
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import savemat, loadmat
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.features import extract as ex, recording as rec, artifact as af
from morgoth_slowing.io import staging as st

RC = str(Path.home() / ".local/bin/rclone")
REPO = "bdsp-opendata-repository/EEG"
SCRATCH = Path("/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad")
M2 = "/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad/morgoth2"
VENV = str(Path("~/Desktop/GithubRepos/morgoth-slowing-growth-curves/.venv/bin/python").expanduser())
OUT = Path("data/derived"); STAGES = ["W", "N1", "N2", "N3", "REM"]


def rclone(args):
    subprocess.run([RC] + args, check=True, capture_output=True)


def select(n):
    meta = pd.concat([pd.read_csv(f, low_memory=False) for f in (SCRATCH / "eegmeta").glob("S000*_eeg_metadata*.csv")])
    fnd = pd.concat([pd.read_csv(f, low_memory=False) for f in (SCRATCH / "reports").glob("S000*_EEG__reports_findings.csv")])
    fnd["pid"] = fnd.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    fnd["date"] = pd.to_datetime(fnd["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    hr = lambda c: fnd[c].astype(str).str.contains("report", case=False, na=False)
    fnd = fnd.assign(rnorm=hr("normal").astype(int), rfoc=hr("foc slowing").astype(int), rgen=hr("gen slowing").astype(int))
    meta["pid"] = meta.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    meta["date"] = pd.to_datetime(meta.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    meta["dur_h"] = meta.DurationInSeconds / 3600
    j = meta.merge(fnd[["pid", "date", "rnorm", "rfoc", "rgen"]], on=["pid", "date"], how="inner")
    j = j[(j.dur_h > 6) & (j.dur_h < 48) & ((j.rnorm | j.rfoc | j.rgen) > 0)]
    cohort = set(pd.read_csv("metadata/cohort_metadata.csv").bdsp_id.str.replace(r"^S000\d", "", regex=True))
    j = j[~j.pid.isin(cohort)]
    # balance: a few normal + focal + generalized
    picks = pd.concat([j[j.rnorm == 1].head(n // 2), j[j.rfoc == 1].head(n - n // 2), j[j.rgen == 1].head(2)]).drop_duplicates("pid").head(n)
    return picks


def edf_path(row):
    site = row.SiteID; bf = row.BidsFolder; ses = row.SessionID
    d = f"{REPO}/bids/{site}/{bf}/ses-{ses}/eeg"
    out = subprocess.run([RC, "lsf", f"bdsp:{d}"], capture_output=True, text=True)
    edfs = [l for l in out.stdout.splitlines() if l.endswith(".edf")]
    return f"{d}/{edfs[0]}" if edfs else None


def stage_dir(indir, outdir):
    subprocess.run(["bash", "-lc",
        f"cd {M2} && PYTORCH_ENABLE_MPS_FALLBACK=1 OMP_NUM_THREADS=1 {VENV} finetune_classification.py "
        f"--abs_pos_emb --model base_patch200_200 --predict --task_model checkpoints/ss_hm_1.pth "
        f"--dataset SLEEPPSG --data_format mat --sampling_rate 0 --already_format_channel_order no "
        f"--already_average_montage no --allow_missing_channels yes --max_length_hour no "
        f"--eval_sub_dir {indir} --eval_results_dir {outdir} --prediction_slipping_step_second 5 "
        f"--polarity 1 --rewrite_results no --num_workers 0 --device mps"], check=True, capture_output=True)


def main(n=6):
    picks = select(n)
    print(f"selected {len(picks)} recordings: normal {picks.rnorm.sum()} foc {picks.rfoc.sum()} gen {picks.rgen.sum()}")
    work = Path(tempfile.mkdtemp()); sin = work / "in"; sout = work / "out"; sin.mkdir(); sout.mkdir()
    recs = {}  # id -> dict(seg tensor rows, seg start/end, meta)
    for _, r in picks.iterrows():
        ep = edf_path(r)
        if not ep:
            print("  no EDF for", r.pid); continue
        rid = f"{r.SiteID}{r.pid}_{r.date}"
        local = work / (rid + ".edf")
        try:
            rclone(["copy", f"bdsp:{ep}", str(work)])
            src = next(work.glob("*.edf")); src.rename(local)
            data, chs, fs = load_edf_referential(str(local))
            bip = ex.to_bipolar(ex.preprocess(data, fs), chs)
            segidx = ex.segment_indices(bip.shape[0])
            mask, reasons = af.usable_mask(bip, segidx, fs)
            # features per usable segment
            feats = []
            for i, (s, e) in enumerate(segidx):
                if not mask[i]:
                    continue
                fr, psd = ex.multitaper_psd(bip[s:e].T, fs)
                feats.append((s, e, ex.features_31(ex.band_powers(fr, psd))))
            # write staging .mat (full recording, referential) for morgoth
            # morgoth mat format: data as (n_ch, n_samp) like segments_raw; channels as string array
            savemat(str(sin / (rid + ".mat")),
                    {"Fs": float(fs), "channels": np.array(chs),
                     "data": data.T.astype(np.float64)}, do_compression=True)
            recs[rid] = {"feats": feats, "usable": int(mask.sum()), "total": len(segidx),
                         "reasons": reasons, "age": r.AgeAtVisit, "sex": r.SexDSC,
                         "label": "normal" if r.rnorm else ("focal_slow" if r.rfoc else "general_slow")}
            local.unlink(missing_ok=True)  # drop raw
            print(f"  {rid}: {mask.sum()}/{len(segidx)} usable ({reasons})")
        except Exception as ex_:
            print("  FAIL", rid, type(ex_).__name__, ex_)
    if not recs:
        print("no recordings ingested"); return
    print("staging", len(recs), "recordings...")
    stage_dir(str(sin), str(sout))
    ncsv = len(list(sout.glob("*.csv")))
    print(f"  staging produced {ncsv} CSVs; ids expect {list(recs)[:2]}...; got {[p.stem for p in list(sout.glob('*.csv'))[:2]]}")
    # map stages + aggregate per region x stage
    rows = []
    for rid, R in recs.items():
        csv = sout / (rid + ".csv")
        pred = pd.read_csv(csv).pred_class.to_numpy() if csv.exists() else None
        for (s, e, feat) in R["feats"]:
            # stage of this segment = staging window at its center
            stage = "Other"
            if pred is not None:
                wi = int(((s + e) / 2 / 200.0) / 5.0)
                if 0 <= wi < len(pred):
                    stage = st.STAGE.get(int(pred[wi]), "Other")
            rowbase = {"bdsp_id": rid, "age": R["age"], "sex": R["sex"], "label": R["label"], "stage": stage}
            for reg, chans in rec.REGIONS.items():
                bp = feat[chans, :6]
                d = rec._derived(np.nanmean(np.where(bp > 0, bp, np.nan), axis=0, keepdims=True))
                rows.append({**rowbase, "region": reg, **{k: float(v[0]) for k, v in d.items()}})
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "expansion_pilot_features.parquet")
    shutil.rmtree(work, ignore_errors=True)
    print(f"\nwrote {OUT}/expansion_pilot_features.parquet: {len(df)} rows, {df.bdsp_id.nunique()} recordings")
    wh = df[df.region == "whole_head"]
    print("stage dist:", wh.stage.value_counts().to_dict())
    print("rel_delta by stage (whole_head):", wh.groupby("stage").rel_delta.median().round(3).to_dict())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
