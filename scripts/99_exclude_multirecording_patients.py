"""Drop patients who contributed more than one recording.

`bdsp_id = SiteID + BDSPPatientID` identifies a **patient at a site, not a recording**. The feature tables
(`channel_stage_features`, `segment_features`) are keyed on `bdsp_id` with the date stripped, and nearly every
analysis calls `labels_unified.drop_duplicates("bdsp_id")` — so for a patient with two recordings, one
recording's features are silently paired with the other's labels.

MBW's decision (2026-07-09): drop those patients rather than promote the key end-to-end.

Writes `data/derived/excluded_bdsp_ids.parquet` (bdsp_id, n_recordings, reason). Every downstream analysis
should filter it out. Reports the impact on the cohort and on each label class.

Run: python scripts/99_exclude_multirecording_patients.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

OUT = "data/derived/excluded_bdsp_ids.parquet"


def main():
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype=str)
    n = meta.groupby("bdsp_id").size().rename("n_recordings")
    dup = n[n > 1].reset_index()
    dup["reason"] = "bdsp_id is a patient-at-site key; >1 recording collapses features onto one label"
    dup.to_parquet(OUT)

    print(f"cohort_metadata rows        : {len(meta):,}")
    print(f"unique bdsp_id              : {meta.bdsp_id.nunique():,}")
    print(f"patients with >1 recording  : {len(dup):,}  ({len(dup)/meta.bdsp_id.nunique():.2%} of patients)")
    print(f"recordings they account for : {int(dup.n_recordings.sum()):,} "
          f"({dup.n_recordings.sum()/len(meta):.2%} of recordings)")

    lu = pd.read_parquet("data/derived/labels_unified.parquet")
    ex = set(dup.bdsp_id)
    keep = lu[~lu.bdsp_id.isin(ex)].drop_duplicates("bdsp_id")
    drop = lu[lu.bdsp_id.isin(ex)].drop_duplicates("bdsp_id")
    print(f"\nlabels_unified: {lu.bdsp_id.nunique():,} unique -> {keep.bdsp_id.nunique():,} retained "
          f"({drop.bdsp_id.nunique():,} dropped)")
    for c in ["clean_normal", "is_abnormal", "has_focal_slow", "has_gen_slow"]:
        if c in lu:
            print(f"  {c:16s} retained {int(keep[c].sum()):6,}   dropped {int(drop[c].sum()):5,}")

    # are the dropped patients systematically different? (restudied patients skew abnormal)
    if "is_abnormal" in lu:
        pk, pd_ = keep.is_abnormal.mean(), drop.is_abnormal.mean()
        print(f"\nabnormal rate: retained {pk:.3f} vs dropped {pd_:.3f}  "
              f"({'dropped patients skew ABNORMAL — state this in Methods' if pd_ > pk else 'comparable'})")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
