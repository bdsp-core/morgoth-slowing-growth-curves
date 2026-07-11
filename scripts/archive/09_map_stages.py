"""Map morgoth staging CSVs -> per-segment sleep stage for the 15-s feature segments.

Reads data/derived/staging/<group>/*.csv, aligns to each recording's res segment start/end, and
writes data/derived/segment_stages.parquet (bdsp_id, segment, stage). Run after staging.
Run: python scripts/09_map_stages.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from morgoth_slowing.io import staging

STAGING = Path("data/derived/staging")
RAW = Path("data/raw/Growth_curves")
OUT = Path("data/derived/segment_stages.parquet")


def main():
    frames = []
    for group_dir in sorted(STAGING.glob("*")):
        if not group_dir.is_dir():
            continue
        n = len(list(group_dir.glob("sub-*.csv")))
        if not n:
            continue
        print(f"mapping {n} staged recordings in {group_dir.name} ...")
        df = staging.build_segment_stage_table(group_dir, RAW, OUT)  # writes each time; keep last
        df["group"] = group_dir.name
        frames.append(df)
    alldf = pd.concat(frames, ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    alldf.to_parquet(OUT)
    print(f"wrote {OUT}: {alldf.bdsp_id.nunique()} recordings, {len(alldf)} segment-stages")
    print("stage distribution:\n", alldf.stage.value_counts(normalize=True).round(3).to_string())


if __name__ == "__main__":
    main()
