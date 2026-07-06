"""Merge the N3-expansion fleet outputs (report-normal overnight EEGs) into the cohort's
stage_recording_features, so the stage growth curves (scripts/10) refit with adult/pediatric N3.

The fleet writes per-segment features (window x region). We aggregate each recording to per-(region,
stage) medians (+ n_seg), keep the aggregate regions the curves use, tag as clean-normal, and append
to stage_recording_features.parquet (original backed up). Idempotent-ish: new bdsp_ids only.

Run: python scripts/65_merge_n3_expansion.py <features_dir>
"""
from __future__ import annotations
import sys, glob
from pathlib import Path
import pandas as pd, numpy as np

FEATDIR = sys.argv[1]
DER = Path("data/derived")
AGG_REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal", "midline"]
FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
         "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
MIN_SEG = 3


def main():
    files = glob.glob(f"{FEATDIR}/*.parquet")
    print(f"aggregating {len(files)} expansion recordings...")
    rows = []; bad = 0
    for f in files:
        try:
            d = pd.read_parquet(f)
        except Exception:
            bad += 1; continue                           # skip partially-downloaded/corrupt files
        if not {"region", "stage", "bdsp_id", "age", "sex", "label"}.issubset(d.columns):
            bad += 1; continue                           # skip incomplete (mid-download) files
        d = d[d.region.isin(AGG_REGIONS)]
        if d.empty:
            continue
        g = d.groupby(["region", "stage"])
        agg = g[FEATS].median()
        agg["n_seg"] = g.size()
        agg = agg.reset_index()
        agg["bdsp_id"] = d.bdsp_id.iloc[0]; agg["age"] = d.age.iloc[0]
        agg["sex"] = d.sex.iloc[0]; agg["label"] = d.label.iloc[0]
        rows.append(agg)
    new = pd.concat(rows, ignore_index=True)
    new = new[new.n_seg >= MIN_SEG]
    new["sex"] = new.sex.astype(str).str[0].str.upper()      # 'Male'/'Female' -> 'M'/'F' (cohort convention)
    # clean-normal flags (these are report-normal overnight studies)
    new["label"] = "normal"; new["lab_focal"] = 0; new["lab_gen"] = 0; new["lab_clean_normal"] = 1
    print(f"new expansion rows: {len(new)} over {new.bdsp_id.nunique()} recordings")
    print("new N3 recordings by age band:")
    n3 = new[(new.stage == "N3") & (new.region == "whole_head")]
    print(pd.cut(n3.age, [0, 3, 6, 13, 18, 30, 45, 60, 75, 200]).value_counts().sort_index().to_dict())

    srf = pd.read_parquet(DER / "stage_recording_features.parquet")
    bak = DER / "stage_recording_features_cohort.parquet"
    if not bak.exists():
        srf.to_parquet(bak); print(f"backed up original cohort table -> {bak}")
    else:
        srf = pd.read_parquet(bak)                       # always merge onto the pristine cohort base
    new = new[~new.bdsp_id.isin(srf.bdsp_id)]            # only genuinely new recordings
    cols = [c for c in srf.columns if c in new.columns]
    merged = pd.concat([srf, new[cols]], ignore_index=True)
    merged.to_parquet(DER / "stage_recording_features.parquet")
    print(f"merged: cohort {srf.bdsp_id.nunique()} + expansion {new.bdsp_id.nunique()} "
          f"= {merged.bdsp_id.nunique()} recordings")
    # N3 normal coverage before/after
    for name, t in [("cohort", srf), ("merged", merged)]:
        n3n = t[(t.stage == "N3") & (t.label == "normal") & (t.region == "whole_head")]
        print(f"  {name}: normal-N3 recordings = {n3n.bdsp_id.nunique()}, "
              f"age {n3n.age.min():.0f}-{n3n.age.max():.0f}")


if __name__ == "__main__":
    main()
