"""Phase A: compute region-level features for every recording -> data/derived/.

Outputs:
  recording_features.parquet   one row per (recording, region), median over segments + age/sex/label
  recording_asymmetry.parquet  one row per recording, L/R log-ratios + age/sex/label
  segment_features.parquet     one row per (recording, region, segment) — for scoring (Phase D)
Run: python scripts/03_compute_features.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from scipy.io import loadmat

from morgoth_slowing.io import segments as seg_io
from morgoth_slowing.features import recording as rec

RAW = Path("data/raw/Growth_curves")
OUT = Path("data/derived"); OUT.mkdir(parents=True, exist_ok=True)


def main(limit=None):
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["key"] = meta.bdsp_id + "_" + meta.eeg_datetime
    meta_by_key = meta.set_index("key")[["age", "age_valid", "sex", "label"]].to_dict("index")

    reg_rows, asym_rows, seg_rows = [], [], []
    files = [f for _, d in seg_io.iter_label_dirs(RAW) for f in sorted(d.glob("sub-*.mat"))]
    if limit:
        files = files[:limit]
    n = len(files)
    for i, f in enumerate(files):
        if i % 1000 == 0:
            print(f"  {i}/{n}")
        p = seg_io.parse_filename(f)
        bid = p["bdsp_id"]
        m = meta_by_key.get(f"{bid}_{p['eeg_datetime']}", {})
        try:
            res = loadmat(f, squeeze_me=True, struct_as_record=False)["res"]
            rows, segs, asym = rec.recording_features(res)
        except Exception as e:
            print("  skip", f.name, e); continue
        base = {"bdsp_id": bid, "age": m.get("age"), "sex": m.get("sex"), "label": m.get("label")}
        for r in rows:
            reg_rows.append({**base, **r})
        asym_rows.append({**base, **asym})
        for s in segs:
            seg_rows.append({"bdsp_id": bid, "label": m.get("label"), **s})

    pd.DataFrame(reg_rows).to_parquet(OUT / "recording_features.parquet")
    pd.DataFrame(asym_rows).to_parquet(OUT / "recording_asymmetry.parquet")
    pd.DataFrame(seg_rows).to_parquet(OUT / "segment_features.parquet")
    print(f"wrote {len(reg_rows)} region-rows, {len(asym_rows)} recordings, {len(seg_rows)} segment-rows")


if __name__ == "__main__":
    import sys
    main(limit=int(sys.argv[1]) if len(sys.argv) > 1 else None)
