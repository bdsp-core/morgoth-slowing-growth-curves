#!/usr/bin/env python3
"""Distil the per-segment deviation field into a small cache the figures can be rebuilt from.

The `results` tier is meant to be the fast, iterate-on-figures loop, but two of its producers read
`segment_deviation/` -- 6 GB spread over ~27k hive partitions -- so in practice regenerating any figure meant
pulling gigabytes first. Nothing in the tier needs the per-region detail: Figures S5 and S6 use the six
WHOLE-HEAD z columns and the stage label, and both subsample anyway.

This writes that subset once, as a single parquet of a few tens of MB, so a fresh machine can rebuild every
figure from the flat tables plus this file. Sampling is seeded, so the cache IS the canonical sample and the
figures are deterministic from it rather than from whichever segments a given run happened to draw.

Run: PYTHONPATH=src python3 scripts/83_build_figure_cache.py [--per-rec 60]
"""
from __future__ import annotations
import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

DEV = "data/derived/segment_deviation"
OUT = Path("data/derived/figure_cache")
FEATS = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR", "rel_alpha"]
COLS = [f"z__whole_head__{f}" for f in FEATS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-rec", type=int, default=60,
                    help="segments sampled per recording (seeded; bounds the cache size)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    parts = sorted(glob.glob(f"{DEV}/eeg_id=*/part.parquet"))
    if not parts:
        raise SystemExit(f"no partitions under {DEV}/ -- run scripts/43 first, or sync the derived data")
    print(f"distilling {len(parts):,} partitions ...", flush=True)

    frames = []
    for k, f in enumerate(parts, 1):
        eid = f.split("eeg_id=")[1].split("/")[0]
        try:
            d = pd.read_parquet(f, columns=["segment", "stage"] + COLS)
        except Exception:
            continue
        if len(d) > a.per_rec:
            d = d.sample(a.per_rec, random_state=0)
        d.insert(0, "eeg_id", eid)
        frames.append(d)
        if k % 5000 == 0:
            print(f"   {k:,}/{len(parts):,}", flush=True)

    out = pd.concat(frames, ignore_index=True)
    # float32 halves the file for a precision no figure resolves; stage as category costs almost nothing
    for c in COLS:
        out[c] = out[c].astype("float32")
    out["stage"] = out["stage"].astype("category")
    out["eeg_id"] = out["eeg_id"].astype("category")
    dest = OUT / "wholehead_z.parquet"
    out.to_parquet(dest, compression="zstd", index=False)
    mb = dest.stat().st_size / 1e6
    print(f"\nwrote {dest}  ({len(out):,} rows, {out.eeg_id.nunique():,} recordings, {mb:.1f} MB)")
    print(f"replaces {DEV}/ for the results tier "
          f"({sum(Path(p).stat().st_size for p in parts) / 1e9:.1f} GB -> {mb / 1000:.3f} GB)")


if __name__ == "__main__":
    main()
