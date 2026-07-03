"""Validate the Python feature extractor against JJ's precomputed Growth_curves features.

We have both raw (segments_raw, v7.3 .mat) and precomputed features (Growth_curves) for the same
recordings. Recompute with extract.py and compare per-channel band powers (correlation) so we can
confirm/tune BANDS + multitaper params before recomputing the whole cohort in Python.
Run: python scripts/12_validate_extractor.py [n_files]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from morgoth_slowing.features import extract as ex
from morgoth_slowing.io import segments as seg_io
from morgoth_slowing.io.raw import load_raw_eeg

RAW = Path("data/raw/segments_raw/normal")
FEAT = Path("data/raw/Growth_curves/features/normal")
BANDS6 = ["delta", "theta", "alpha", "beta", "gamma", "total"]


def main(n=3):
    raws = sorted(RAW.glob("sub-*.mat"))[:n]
    per_band = {b: [] for b in BANDS6}
    for rp in raws:
        stem = rp.stem
        fp = next(FEAT.glob(stem + "*.mat"), None) or next(FEAT.glob("sub-" + seg_io.parse_filename(rp)["bdsp_id"] + "*.mat"), None)
        if fp is None:
            print("no feature match for", stem); continue
        data, chs, fs = load_raw_eeg(rp)
        mine, segs = ex.extract(data, chs, fs)           # (n_seg,18,31)
        jj = np.stack([np.asarray(r[3], float) for r in loadmat(fp, squeeze_me=True, struct_as_record=False)["res"]])
        m = min(len(mine), len(jj)); mine, jj = mine[:m], jj[:m]
        valid = np.isfinite(jj).all(axis=2) & (jj[:, :, :6] > 0).all(axis=2)
        for bi, b in enumerate(BANDS6):
            a = mine[:, :, bi][valid]; c = jj[:, :, bi][valid]
            ok = np.isfinite(a) & np.isfinite(c) & (a > 0) & (c > 0)
            if ok.sum() > 10:
                r = np.corrcoef(np.log(a[ok]), np.log(c[ok]))[0, 1]
                per_band[b].append(r)
        print(f"{stem[:26]}: segs mine={len(mine)} jj={len(jj)}")
    print("\n=== log-power correlation (mine vs JJ), mean over files ===")
    for b in BANDS6:
        v = per_band[b]
        print(f"  {b:6s}: r={np.mean(v):.3f} (n_files={len(v)})" if v else f"  {b}: n/a")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
