#!/usr/bin/env python3
"""§4 DESCRIPTION — step 1: read structured descriptors off the per-segment deviation field.

The description comes out of the SAME field the detector uses (data/derived/segment_deviation: a stage- and
age-matched z per region × feature per 15 s segment). Per recording we read off:

  TYPE / AMOUNT   whole-head delta-excess z (log_delta) and theta-excess z (log_theta): {p90, mean, prev>1.5}
  LATERALITY      left-minus-right region z (temporal, parasagittal), on delta; signed (+ = left)
  ANT-POST        anterior-minus-posterior region z on delta (+ = frontal-predominant)
  PEAK REGION     the region with the largest delta z (localises a focus)
  PERSISTENCE     prevalence (frac abnormal segments), longest continuous run (min), n episodes

Orientation: high z = abnormal for the excess features; rel_alpha is flipped. Written both per recording
(description_recording.parquet) and per (recording × sleep stage) (description_stage.parquet, for D5).
Run: PYTHONPATH=src python3 scripts/56_description_descriptors.py
"""
from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd

DEV = "data/derived/segment_deviation"
REGIONS = ["anterior", "posterior", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
SEG_MIN = 14.0 / 60.0                                   # 15 s epoch, 14 s step -> minutes per segment
THR = 1.5                                               # a segment is "abnormal" for a band when its z exceeds this


def wh(d, feat):
    return d[f"z__whole_head__{feat}"].to_numpy()


def descz(d):
    """band-amount aggregates for one (recording or stage-subset) segment frame."""
    out = {}
    for band, feat in [("delta", "log_delta"), ("theta", "log_theta")]:
        v = wh(d, feat); v = v[np.isfinite(v)]
        if len(v):
            out[f"{band}_p90"] = np.quantile(v, .9); out[f"{band}_mean"] = v.mean()
            out[f"{band}_prev"] = float((v > THR).mean())
    for band, feat in [("reldelta", "rel_delta"), ("tar", "log_TAR")]:
        v = wh(d, feat); v = v[np.isfinite(v)]
        if len(v):
            out[f"{band}_p90"] = np.quantile(v, .9)
    return out


def one(eid):
    f = f"{DEV}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        return None
    try:
        d = pd.read_parquet(f)
    except Exception:
        return None
    if d.empty:
        return None
    d = d.sort_values("t_start_s")
    rec = {"eeg_id": eid, "n_seg": len(d)}
    rec.update(descz(d))
    # laterality & ant-post on delta excess (left - right; anterior - posterior), averaged over segments
    def diff(a, b, feat):
        x = (d[f"z__{a}__{feat}"] - d[f"z__{b}__{feat}"]).to_numpy(); x = x[np.isfinite(x)]
        return float(x.mean()) if len(x) else np.nan
    rec["lat_temporal"] = diff("L_temporal", "R_temporal", "log_delta")
    rec["lat_parasag"] = diff("L_parasagittal", "R_parasagittal", "log_delta")
    lt, lp = rec["lat_temporal"], rec["lat_parasag"]
    rec["lat_signed"] = lt if abs(np.nan_to_num(lt)) >= abs(np.nan_to_num(lp)) else lp   # dominant asymmetry, +=left
    rec["antpost"] = diff("anterior", "posterior", "log_delta")                           # + = frontal-predominant
    # peak region by delta p90, and per-region magnitude (for region dose-response, not a confusion matrix)
    reg_score = {}
    for r in REGIONS:
        v = d[f"z__{r}__log_delta"].to_numpy(); v = v[np.isfinite(v)]
        if len(v):
            reg_score[r] = np.quantile(v, .9); rec[f"reg_{r}"] = float(reg_score[r])
    if reg_score:
        rec["peak_region"] = max(reg_score, key=reg_score.get)
        rec["peak_region_z"] = reg_score[rec["peak_region"]]
        # lobe-collapsed magnitudes: temporal = max(L,R) temporal; frontal = anterior; posterior = posterior
        rec["lobe_temporal"] = float(max(reg_score.get("L_temporal", np.nan), reg_score.get("R_temporal", np.nan)))
        rec["lobe_frontal"] = float(reg_score.get("anterior", np.nan))
        rec["lobe_posterior"] = float(reg_score.get("posterior", np.nan))
    # persistence on "any slowing" (delta OR theta abnormal)
    ab = ((wh(d, "log_delta") > THR) | (wh(d, "log_theta") > THR))
    rec["prevalence"] = float(np.mean(ab))
    if ab.any():
        runs = np.diff(np.concatenate([[0], ab.astype(int), [0]]))
        lens = np.where(runs == -1)[0] - np.where(runs == 1)[0]
        rec["longest_run_min"] = float(lens.max() * SEG_MIN); rec["n_episodes"] = int(len(lens))
    else:
        rec["longest_run_min"] = 0.0; rec["n_episodes"] = 0
    # per-stage amounts (for D5)
    stage_rows = []
    for st, ds in d.groupby("stage", observed=True):
        if st not in ("W", "N1", "N2", "N3", "REM") or len(ds) < 3:
            continue
        sr = {"eeg_id": eid, "stage": st, "n_seg": len(ds)}
        sr.update(descz(ds)); sr["prevalence"] = float((((wh(ds, "log_delta") > THR) | (wh(ds, "log_theta") > THR)).mean()))
        stage_rows.append(sr)
    return rec, stage_rows


def main():
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    ids = [i for i in lab[(lab.clean_pair == True) &                                       # noqa: E712
                          (~lab.eeg_id.astype(str).str.startswith(("MOE_", "ON_")))].eeg_id
           if os.path.exists(f"{DEV}/eeg_id={i}")]
    print(f"reading descriptors from the deviation field for {len(ids):,} report recordings ...", flush=True)
    recs, stages = [], []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for r in ex.map(one, ids):
            if r is not None:
                recs.append(r[0]); stages.extend(r[1])
    R = pd.DataFrame(recs)
    R.to_parquet("data/derived/description_recording.parquet", index=False)
    pd.DataFrame(stages).to_parquet("data/derived/description_stage.parquet", index=False)
    print(f"wrote description_recording.parquet ({len(R):,}) + description_stage.parquet ({len(stages):,} rows)")
    print("  columns:", [c for c in R.columns])


if __name__ == "__main__":
    main()
