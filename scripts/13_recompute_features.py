"""Recompute ALL features from raw EEG with our Python extractor (reproducible; no MATLAB).

Replaces the precomputed Growth_curves features with features computed by features/extract.py from the
raw segments_raw recordings. Produces the same schema as scripts/03 so all downstream (curves,
discrimination, stage analysis) runs unchanged on Python-derived features.

Outputs (the _py alias was retired 2026-07 now that MATLAB features are gone; these ARE canonical —
see docs/DATA_INVENTORY.md):
  data/derived/recording_features.parquet, recording_asymmetry.parquet, segment_features.parquet
Run: python scripts/13_recompute_features.py [limit]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
from morgoth_slowing.io.raw import load_raw_eeg
from morgoth_slowing.io import segments as seg_io
from morgoth_slowing.features import extract as ex, recording as rec

RAWROOT = Path("data/raw/segments_raw")
GROUPS = {"normal": "normal", "focal": "focal_slow", "general": "general_slow"}
OUT = Path("data/derived"); OUT.mkdir(parents=True, exist_ok=True)


def main(limit=None):
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["key"] = meta.bdsp_id + "_" + meta.eeg_datetime
    mk = meta.set_index("key")[["age", "sex", "label"]].to_dict("index")

    reg_rows, asym_rows, seg_rows = [], [], []
    files = [(lbl, f) for grp, lbl in GROUPS.items()
             for f in sorted((RAWROOT / grp).glob("sub-*.mat"))]
    if limit:
        files = files[:limit]
    n = len(files); done = 0
    for lbl, f in files:
        if done % 500 == 0:
            print(f"  {done}/{n}")
        done += 1
        p = seg_io.parse_filename(f)
        m = mk.get(f"{p['bdsp_id']}_{p['eeg_datetime']}", {})
        try:
            data, chs, fs = load_raw_eeg(f)
            tensor, _ = ex.extract(data, chs, fs)
            rows, segs, asym = rec.recording_features_tensor(tensor)
        except Exception as e:
            print("  skip", f.name, type(e).__name__, e); continue
        base = {"bdsp_id": p["bdsp_id"], "age": m.get("age"), "sex": m.get("sex"), "label": m.get("label")}
        for r in rows:                                   # recording-level: all 6 regions + 18 channels
            reg_rows.append({**base, **r})
        asym_rows.append({**base, **asym})               # 2 region + 8 channel homologous pairs
        for s in segs:                                   # segment-level: only 6 aggregated regions (size)
            if s["region"] in rec.AGG_REGIONS:
                seg_rows.append({"bdsp_id": p["bdsp_id"], "label": m.get("label"), **s})

    pd.DataFrame(reg_rows).to_parquet(OUT / "recording_features.parquet")
    pd.DataFrame(asym_rows).to_parquet(OUT / "recording_asymmetry.parquet")
    pd.DataFrame(seg_rows).to_parquet(OUT / "segment_features.parquet")
    print(f"wrote {len(reg_rows)} region-rows from {done} recordings (Python-recomputed features)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
