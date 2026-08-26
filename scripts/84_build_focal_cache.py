#!/usr/bin/env python3
"""Precompute the per-channel focal features so the focal chain stops needing the 59 GB table.

scripts/64 derives spatial-focality and interhemispheric-asymmetry features by pivoting segment x channel,
which is the one thing in the results tier that genuinely needs per-segment PER-CHANNEL band powers -- i.e.
segment_master/. But its output is a handful of SCALARS per recording, so what has to be portable is the
result, not the input: caching feats() collapses 59 GB to a couple of MB and makes 55_recording_model,
vanputten_panel_s7 and sandor100_external_validation runnable on a figure-loop install.

`age` is deliberately NOT cached. It is an input feature the caller supplies, not something derived from the
signal, and freezing it would silently pin every recording to whatever age this build happened to see.

Run: PYTHONPATH=src python3 scripts/84_build_focal_cache.py [--limit N]
"""
from __future__ import annotations
import argparse
import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

_argv = sys.argv[:]
sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("m64", "scripts/64_focal_v2_experiment.py")
m64 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m64)
sys.argv = _argv

OUT = Path("data/derived/figure_cache")
DEST = OUT / "focal_channel_feats.parquet"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    ids = sorted(p.name.split("=")[1] for p in Path(m64.SM).glob("eeg_id=*"))
    if a.limit:
        ids = ids[:a.limit]
    if not ids:
        raise SystemExit(f"no partitions under {m64.SM}/ -- this cache must be built on a full install")
    print(f"computing per-channel focal features for {len(ids):,} recordings ...", flush=True)

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=14) as ex:
        # nan age -> feats() falls back to its own default; the column is dropped below either way
        for r in ex.map(m64.feats, [(i, float("nan")) for i in ids]):
            done += 1
            if r is not None:
                rows.append(r)
            if done % 2500 == 0:
                print(f"   {done:,}/{len(ids):,} ({len(rows):,} with features)", flush=True)

    d = pd.DataFrame(rows)
    if "age" in d.columns:
        d = d.drop(columns=["age"])                 # caller-supplied, never cached
    for c in d.columns:
        if c != "eeg_id":
            d[c] = d[c].astype("float32")
    d.to_parquet(DEST, compression="zstd", index=False)
    mb = DEST.stat().st_size / 1e6
    print(f"\nwrote {DEST}  ({len(d):,} recordings, {len(d.columns) - 1} features, {mb:.1f} MB)")
    print("scripts/64 will now prefer this over reading segment_master.")


if __name__ == "__main__":
    main()
