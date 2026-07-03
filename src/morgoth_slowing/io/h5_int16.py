"""Lossless int16 EDF->H5 storage (space-saving), with a morgoth-compatible loader.

EDF already stores each sample as int16 digital + a per-channel linear transform
(physical = digital*gain + offset, derived from physical/digital min-max). Storing float64 Volts
(the current morgoth-H5) quadruples size for zero added information. Here we store the ORIGINAL
int16 digital + gain/offset -> bit-exact, ~1/4 the float64 size (and < EDF after gzip + dropping
dead channels). The loader reconstructs the exact same Volts morgoth reads today.
"""
from __future__ import annotations
import numpy as np, h5py


def edf_to_h5_int16(edf_path, h5_path, keep_labels=None):
    """Write kept channels as int16 digital + per-channel gain/offset. Returns dict of stats.
    keep_labels: list of EDF channel labels to keep (default: all)."""
    import pyedflib
    f = pyedflib.EdfReader(str(edf_path))
    labels = f.getSignalLabels()
    fs_all = f.getSampleFrequencies()
    keep = [i for i, l in enumerate(labels) if (keep_labels is None or l in keep_labels)]
    with h5py.File(h5_path, "w") as h5:
        h5.attrs["sampling_rate"] = int(round(fs_all[keep[0]]))
        h5.attrs["format"] = "int16+gain"
        h5.attrs["source_edf"] = str(edf_path).split("/")[-1]
        g = h5.create_group("signals")
        for i in keep:
            dig = f.readSignal(i, digital=True).astype(np.int16)     # original int16 samples
            pmin, pmax = f.getPhysicalMinimum(i), f.getPhysicalMaximum(i)
            dmin, dmax = f.getDigitalMinimum(i), f.getDigitalMaximum(i)
            gain = (pmax - pmin) / (dmax - dmin)
            offset = pmin - dmin * gain                              # physical = dig*gain + offset
            unit = f.getPhysicalDimension(i).strip()
            # fold physical-unit -> Volts into gain/offset so the loader is trivial and matches the
            # existing float64-H5 (mne Volts) convention exactly. EDF physical is usually µV.
            scale = 1e-6 if unit.lower() in ("uv", "µv", "microvolt", "microvolts") else 1.0
            gain *= scale; offset *= scale
            ds = g.create_dataset(labels[i], data=dig.reshape(-1, 1),
                                  compression="gzip", shuffle=True)
            ds.attrs["gain"] = float(gain); ds.attrs["offset"] = float(offset)
            ds.attrs["unit"] = "V"; ds.attrs["orig_unit"] = unit; ds.attrs["fs"] = float(fs_all[i])
    f._close()
    return {"n_kept": len(keep)}


def load_h5_int16(h5_path):
    """Reconstruct {channel: physical_signal (float64, EDF units)} + fs. This is the conversion a
    morgoth `_load_h5` update must apply: physical = digital*gain + offset."""
    out = {}
    with h5py.File(h5_path, "r") as h5:
        fs = float(h5.attrs["sampling_rate"])
        for name, ds in h5["signals"].items():
            dig = np.asarray(ds[:, 0], dtype=np.float64)
            out[name] = dig * ds.attrs["gain"] + ds.attrs["offset"]
    return out, fs
