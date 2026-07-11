"""Combine cohort (.mat-derived) + expansion (fleet) into ONE uniform per-(recording, region, stage)
reference table with all 18 bipolar channels + 6 aggregate regions. Any region (e.g. central C3/C4)
is then derivable identically for every recording.

Run: python scripts/70_build_uniform_reference.py <cohort_channel_stage.parquet> <expansion_feat_dir...>
"""
from __future__ import annotations
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd

COHORT = sys.argv[1]
EXP_DIRS = [a for a in sys.argv[2:] if Path(a).is_dir()]
FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
         "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
OUT = "data/derived/channel_stage_features.parquet"


def aggregate_expansion():
    rows = []
    files = [f for d in EXP_DIRS for f in glob.glob(f"{d}/*.parquet")]
    print(f"aggregating {len(files)} expansion recordings...")
    for f in files:
        try:
            d = pd.read_parquet(f)
        except Exception:
            continue
        if not {"region", "stage", "bdsp_id"}.issubset(d.columns):
            continue
        have = [c for c in FEATS if c in d.columns]
        g = d.groupby(["region", "stage"])[have].median()
        n = d.groupby(["region", "stage"]).size().rename("n_seg")
        a = g.join(n).reset_index()
        a["bdsp_id"] = d.bdsp_id.iloc[0]; a["age"] = d.age.iloc[0]; a["sex"] = d.sex.iloc[0]
        rows.append(a)
    e = pd.concat(rows, ignore_index=True)
    e["label"] = "normal"
    return e


def main():
    coh = pd.read_parquet(COHORT)
    coh["src"] = "cohort"
    exp = aggregate_expansion()
    exp["src"] = "expansion"
    exp = exp[~exp.bdsp_id.isin(set(coh.bdsp_id))]                     # cohort wins if overlap
    both = pd.concat([coh, exp], ignore_index=True)
    both["sex"] = both.sex.astype(str).str[0].str.upper()             # 'Male'/'Female'/'M'/'F' -> M/F
    both = both[both.stage.isin(["W", "N1", "N2", "N3", "REM"])]
    # Attach AUTHORITATIVE re-derived labels (the `label` column above is a placeholder). Cohort rows get
    # clean_normal / is_abnormal from labels_unified; expansion rows have no report -> clean_normal=True
    # (fleet manifest selected normal overnight EEGs). Keeps `src` so the two sources can always be split
    # (they are NOT fully comparable — see memory: cohort/expansion harmonization).
    lu_path = "data/derived/labels_unified.parquet"
    if Path(lu_path).exists():
        lu = pd.read_parquet(lu_path)[["bdsp_id", "clean_normal", "is_abnormal"]]
        both = both.merge(lu, on="bdsp_id", how="left")
        both["clean_normal"] = both.clean_normal.where(both.src == "cohort", True)  # expansion assumed clean
        both["is_abnormal"] = both.is_abnormal.fillna(False)
    both.to_parquet(OUT)
    print(f"wrote {OUT}: {len(both)} rows, {both.bdsp_id.nunique()} recordings "
          f"(cohort {coh.bdsp_id.nunique()} + expansion {exp.bdsp_id.nunique()})")
    print("clean_normal recordings:", both[both.clean_normal == True].bdsp_id.nunique(),
          "| abnormal:", both[both.is_abnormal == True].bdsp_id.nunique())
    print("regions:", both.region.nunique(), "| by src:", both.groupby('src').bdsp_id.nunique().to_dict())
    n3 = both[(both.stage == "N3") & (both.region == "whole_head")]
    print("normal-N3 recordings:", n3.bdsp_id.nunique(),
          "| by age band:", pd.cut(n3.age, [0, 1, 3, 13, 18, 45, 75, 200]).value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
