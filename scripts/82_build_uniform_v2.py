"""Build the uniform reference table with BOTH cohorts on the IDENTICAL extract.py + Morgoth pipeline:
cohort from the fleet recompute (cohort_recompute/) + overnight expansion (expansion features). Every
feature is now cross-comparable, so the union-of-both-cohorts normal is valid for ALL features. Same
schema/labels as scripts/70; adds src (cohort|expansion) + clean_normal/is_abnormal from labels_unified.

Run: PYTHONPATH=src python scripts/82_build_uniform_v2.py <cohort_recompute_dir> <expansion_dir ...>
"""
from __future__ import annotations
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd

COHORT_DIR = sys.argv[1]
EXP_DIRS = [a for a in sys.argv[2:] if Path(a).is_dir()]
FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
         "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
OUT = "data/derived/channel_stage_features.parquet"


def aggregate(dirs, src):
    files = [f for d in dirs for f in glob.glob(f"{d}/*.parquet")]
    print(f"aggregating {len(files)} {src} recordings...", flush=True)
    rows = []
    for i, f in enumerate(files):
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
        a["bdsp_id"] = d.bdsp_id.iloc[0]
        a["age"] = d.age.iloc[0] if "age" in d else np.nan
        a["sex"] = d.sex.iloc[0] if "sex" in d else np.nan
        rows.append(a)
        if (i + 1) % 2000 == 0: print(f"  {i+1}/{len(files)}", flush=True)
    e = pd.concat(rows, ignore_index=True); e["src"] = src
    return e


def main():
    coh = aggregate([COHORT_DIR], "cohort")
    exp = aggregate(EXP_DIRS, "expansion")
    exp = exp[~exp.bdsp_id.isin(set(coh.bdsp_id))]                  # cohort wins on any overlap
    both = pd.concat([coh, exp], ignore_index=True)
    both["sex"] = both.sex.astype(str).str[0].str.upper()
    both = both[both.stage.isin(["W", "N1", "N2", "N3", "REM"])]
    lu_path = "data/derived/labels_unified.parquet"
    if Path(lu_path).exists():
        lu = pd.read_parquet(lu_path)[["bdsp_id", "clean_normal", "is_abnormal"]].drop_duplicates("bdsp_id")
        both = both.merge(lu, on="bdsp_id", how="left")
        both["clean_normal"] = both.clean_normal.where(both.src == "cohort", True)   # expansion assumed normal
        both["is_abnormal"] = both.is_abnormal.fillna(False)
    both.to_parquet(OUT)
    print(f"wrote {OUT}: {len(both)} rows, {both.bdsp_id.nunique()} recordings "
          f"(cohort {coh.bdsp_id.nunique()} + expansion {exp.bdsp_id.nunique()}) — ALL extract.py pipeline")
    print("clean_normal:", both[both.clean_normal == True].bdsp_id.nunique(),
          "| abnormal:", both[both.is_abnormal == True].bdsp_id.nunique())
    print("by src:", both.groupby("src").bdsp_id.nunique().to_dict())


if __name__ == "__main__":
    main()
