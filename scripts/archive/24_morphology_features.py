"""Compute P1 morphology features (slow-band centroid/peak/spread) for the cohort from raw EEG.

Output: data/derived/morphology_features.parquet (bdsp_id, region, slow_centroid, slow_peak,
slow_spread, age, sex, label). Enables a faithful band-composition call (delta vs theta vs mixed).
Run: python scripts/24_morphology_features.py [limit]
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
from morgoth_slowing.io.raw import load_raw_eeg
from morgoth_slowing.io import segments as seg_io
from morgoth_slowing.features import morphology as mo

RAWROOT = Path("data/raw/segments_raw")
GROUPS = {"normal": "normal", "focal": "focal_slow", "general": "general_slow"}
OUT = Path("data/derived")


def main(limit=None):
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["key"] = meta.bdsp_id + "_" + meta.eeg_datetime
    mk = meta.set_index("key")[["age", "sex", "label"]].to_dict("index")
    files = [f for grp in GROUPS for f in sorted((RAWROOT / grp).glob("sub-*.mat"))]
    if limit:
        files = files[:limit]
    rows = []
    for i, f in enumerate(files):
        if i % 500 == 0:
            print(f"  {i}/{len(files)}")
        p = seg_io.parse_filename(f); m = mk.get(f"{p['bdsp_id']}_{p['eeg_datetime']}", {})
        try:
            data, chs, fs = load_raw_eeg(f)
            for r in mo.recording_morphology(data, chs, fs):
                rows.append({"bdsp_id": p["bdsp_id"], "age": m.get("age"), "sex": m.get("sex"),
                             "label": m.get("label"), **r})
        except Exception as e:
            print("  skip", f.name, type(e).__name__, e)
    pd.DataFrame(rows).to_parquet(OUT / "morphology_features.parquet")
    print("wrote data/derived/morphology_features.parquet", len(rows), "rows")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
