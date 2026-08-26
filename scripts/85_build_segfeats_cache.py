#!/usr/bin/env python3
"""Per-segment model features for EVERY recording, so the focal chain trains on the same set anywhere.

`single_model_segfeats.parquet` holds these features, but only for the ~10k recordings scripts/53 sampled.
That made training-set membership depend on the install: on a full machine the focal chain drew its sample
from every recording in segment_master, and on a figure-loop machine only from what happened to be cached, so
the two produced different models and different numbers.

This builds the same features for all ~27k recordings, from the same seg_feats() the pipeline already uses,
so membership is identical whether or not segment_master is present. Must be built once on a full install.

Run: PYTHONPATH=src python3 scripts/85_build_segfeats_cache.py [--limit N]
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
spec = importlib.util.spec_from_file_location("m53", "scripts/53_single_model_features.py")
m53 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m53)
sys.argv = _argv

OUT = Path("data/derived/figure_cache")
DEST = OUT / "segfeats_all.parquet"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    m53._SEGFEATS_IDX = {}                      # build from segment_master, never from a partial cache

    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    ages = dict(zip(lab.eeg_id, lab.age))
    # panel recordings carry their age in the panel workbook rather than the report labels
    try:
        occ = pd.read_parquet("data/derived/occasion_features.parquet")[["fid", "age"]].drop_duplicates("fid")
        pan = pd.read_parquet("data/derived/panel_v6_scores.parquet")[["eeg_id", "fid"]]
        ages.update(dict(zip(*pan.merge(occ, on="fid", how="left")[["eeg_id", "age"]].values.T)))
    except Exception:
        pass

    ids = sorted(p.name.split("=")[1] for p in Path(m53.SM).glob("eeg_id=*"))
    if a.limit:
        ids = ids[:a.limit]
    todo = [(i, float(ages.get(i, np.nan))) for i in ids]
    print(f"computing per-segment features for {len(todo):,} recordings ...", flush=True)

    frames, done = [], 0
    with ThreadPoolExecutor(max_workers=14) as ex:
        for eid, sf in zip((i for i, _ in todo),
                           ex.map(lambda t: m53.seg_feats(*t), todo)):
            done += 1
            if sf is not None and len(sf):
                sf = sf.copy()
                sf["eeg_id"] = eid
                frames.append(sf)
            if done % 2500 == 0:
                print(f"   {done:,}/{len(todo):,} ({len(frames):,} with features)", flush=True)

    d = pd.concat(frames, ignore_index=True)
    for c in d.columns:
        if str(d[c].dtype).startswith("float"):
            d[c] = d[c].astype("float32")
    d["eeg_id"] = d["eeg_id"].astype("category")
    d.to_parquet(DEST, compression="zstd", index=False)
    print(f"\nwrote {DEST}  ({len(d):,} rows, {d.eeg_id.nunique():,} recordings, "
          f"{DEST.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
