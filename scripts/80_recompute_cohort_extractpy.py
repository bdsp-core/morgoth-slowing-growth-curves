"""Recompute the ROUTINE COHORT features with extract.py (the SAME code as the overnight expansion) so
BOTH cohorts are pipeline-identical and every feature (incl. TAR/DAR/alpha) is cross-comparable -> the
union-of-both-cohorts normal is valid for all features.

For each cohort recording: pull its raw rEEG EDF, run extract.py on the FIRST N segments (which align 1:1
with the JJ .mat / segment_stages — the .mat used the first ~10 min on the same 15s/14s grid), attach the
existing re-staging (segment_stages), and aggregate per (region, stage) with the identical scripts/69
schema. Parallel (pull-bound). Output: data/derived/cohort_channel_stage_extractpy.parquet.

Run: PYTHONPATH=src python scripts/80_recompute_cohort_extractpy.py [n_limit] [workers]
"""
from __future__ import annotations
import sys, os, re, glob, subprocess, tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np, pandas as pd
if not hasattr(np, "trapz"): np.trapz = np.trapezoid          # numpy>=2 compat for extract.py
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.features import extract as ex

SC = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad"
MATDIR, SEG = f"{SC}/mat_normal", f"{SC}/seg/segment_stages.parquet"
OUT = "data/derived/cohort_channel_stage_extractpy.parquet"
CH = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",
      "Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2", "Fz-Cz", "Cz-Pz"]
AGG = {"L_temporal": [0, 1, 2, 3], "R_temporal": [4, 5, 6, 7], "L_parasagittal": [8, 9, 10, 11],
       "R_parasagittal": [12, 13, 14, 15], "midline": [16, 17], "whole_head": list(range(18))}
FIDX = {"log_delta": 0, "log_theta": 1, "log_alpha": 2, "log_beta": 3, "log_gamma": 4, "log_total": 5}
RELIDX = {"rel_delta": 6, "rel_theta": 7, "rel_alpha": 8, "DTR": 11, "DAR": 12, "TAR": 16}  # TAR=16 (fixed)
FEATS = list(FIDX) + list(RELIDX) + ["low_freq_rel"]


def edf_url(bid, ses):
    site = bid[:5]
    return f"s3:bdsp-opendata-repository/EEG/bids/{site}/sub-{bid}/ses-{ses}/eeg/sub-{bid}_ses-{ses}_task-rEEG_eeg.edf"


def worker(task):
    bid, ses, stages = task
    url = edf_url(bid, ses)
    with tempfile.TemporaryDirectory() as td:
        lp = f"{td}/x.edf"
        if subprocess.run(["rclone", "copyto", url, lp], capture_output=True).returncode:
            return ("noedf", bid, None)
        try:
            data, chs, fs = load_edf_referential(lp)
            bip = ex.to_bipolar(ex.preprocess(data.astype(np.float32), fs), chs)
            segidx = ex.segment_indices(bip.shape[0])
            n = min(len(stages), len(segidx))
            if n < 5: return ("short", bid, None)
            arr = np.stack([ex.features_31(ex.band_powers(*ex.multitaper_psd(bip[s:e].T, fs)))
                            for s, e in segidx[:n]])           # (n, 18, 31)
        except Exception as e:
            return ("fail", bid, f"{type(e).__name__}:{e}")
    stg = np.array(stages[:n])
    feat = {name: np.log(np.clip(arr[:, :, i], 1e-12, None)) for name, i in FIDX.items()}
    feat.update({name: arr[:, :, i] for name, i in RELIDX.items()})
    feat["low_freq_rel"] = arr[:, :, 6] + arr[:, :, 7]
    rows = []
    for region, idxs in list(AGG.items()) + [(c, [i]) for i, c in enumerate(CH)]:
        reg = {name: np.nanmean(v[:, idxs], axis=1) for name, v in feat.items()}   # (n,)
        rdf = pd.DataFrame(reg); rdf["stage"] = stg
        for st, g in rdf.groupby("stage"):
            if st not in ("W", "N1", "N2", "N3", "REM"): continue
            r = {"bdsp_id": bid, "region": region, "stage": st, "n_seg": len(g)}
            for name in FEATS: r[name] = float(np.nanmedian(g[name]))
            rows.append(r)
    return ("ok", bid, rows)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    ss = pd.read_parquet(SEG)
    stmap = {b: g.sort_values("segment").stage.tolist() for b, g in ss.groupby("bdsp_id")}
    # ses from the .mat filename (sub-{bid}_ses-{N}_{date}.mat)
    tasks = []
    for mp in sorted(glob.glob(f"{MATDIR}/sub-*_ses-*.mat")):
        mm = re.match(r"sub-(.+?)_ses-(\d+)_", os.path.basename(mp))
        if not mm: continue
        bid, ses = mm.group(1), mm.group(2)
        if bid in stmap: tasks.append((bid, ses, stmap[bid]))
    tasks = tasks[:limit]
    print(f"recomputing {len(tasks)} cohort recordings via extract.py, {workers} workers", flush=True)
    allrows, stats = [], {"ok": 0, "noedf": 0, "short": 0, "fail": 0}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(worker, t): t[0] for t in tasks}
        for i, fu in enumerate(as_completed(futs)):
            status, bid, rows = fu.result()
            stats[status] += 1
            if status == "ok": allrows.extend(rows)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(tasks)}  {stats}", flush=True)
    df = pd.DataFrame(allrows)
    df.to_parquet(OUT)
    print(f"DONE: {stats} | wrote {OUT}: {len(df)} rows, {df.bdsp_id.nunique()} recordings", flush=True)


if __name__ == "__main__":
    main()
