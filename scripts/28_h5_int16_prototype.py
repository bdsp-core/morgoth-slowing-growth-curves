"""Validate lossless int16 EDF->H5 (space-saving) + morgoth-compatible loader.

Confirms: int16-H5 reconstructs the EDF physical signal bit-exactly, and is far smaller than both the
EDF and the float64 morgoth-H5. The loader (load_h5_int16) is the conversion a morgoth `_load_h5`
update must apply. Run: python scripts/28_h5_int16_prototype.py
"""
from __future__ import annotations
import glob, os
import numpy as np
from morgoth_slowing.io.h5_int16 import edf_to_h5_int16, load_h5_int16

EDF_DIR = "data/raw/h5_pilot/edf"
F64_DIR = "data/raw/h5_pilot/h5"


def main():
    import pyedflib
    edfs = sorted(glob.glob(f"{EDF_DIR}/*.edf"))
    print(f"{'file':40} {'EDF MB':>7} {'int16 MB':>9} {'f64 MB':>8} {'int16/EDF':>9} {'max|d|uV':>9}")
    for e in edfs:
        h = "/tmp/" + os.path.basename(e).replace(".edf", "_int16.h5")
        edf_to_h5_int16(e, h)
        recon, fs = load_h5_int16(h)
        f = pyedflib.EdfReader(e); labels = f.getSignalLabels(); md = 0.0
        for i, l in enumerate(labels):
            if l in recon:
                md = max(md, float(np.max(np.abs(f.readSignal(i) - recon[l]))))
        f._close()
        f64 = next((x for x in glob.glob(f"{F64_DIR}/*") if os.path.basename(e)[:20] in x), None)
        f64mb = os.path.getsize(f64) / 1e6 if f64 else float("nan")
        edfmb, hmb = os.path.getsize(e) / 1e6, os.path.getsize(h) / 1e6
        print(f"{os.path.basename(e)[:40]:40} {edfmb:7.1f} {hmb:9.1f} {f64mb:8.1f} {hmb/edfmb:9.2f} {md:9.2e}")


if __name__ == "__main__":
    main()
