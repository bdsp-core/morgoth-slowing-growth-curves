"""Robust loader for raw EEG segment .mat files (mixed formats across groups).

normal/ = MATLAB v5 (scipy): data (n_ch, n_samp), 19 channels, no EKG.
focal/general/ = MATLAB v7.3 (h5py): data (n_samp, n_ch), 20 channels incl EKG.
Returns a common (data[n_samp, n_ch], ch_names, fs).
"""
from __future__ import annotations
import numpy as np

# expected referential EEG channels (order-independent; extractor indexes by name)
EEG_CH = {"Fp1", "F3", "C3", "P3", "F7", "T3", "T5", "O1", "Fz", "Cz", "Pz",
          "Fp2", "F4", "C4", "P4", "F8", "T4", "T6", "O2"}


def _orient(data):
    """-> (n_samples, n_channels): channels is the small dimension."""
    data = np.asarray(data, float)
    if data.ndim != 2:
        raise ValueError(f"bad data ndim {data.ndim}")
    return data.T if data.shape[0] < data.shape[1] else data


def load_raw_eeg(path):
    """Return (data (n_samp, n_ch), ch_names list, fs float). Handles v5 and v7.3."""
    try:
        from scipy.io import loadmat
        m = loadmat(path, squeeze_me=True, struct_as_record=False)
        fs = float(np.asarray(m["Fs"]).ravel()[0])
        chs = [str(c).strip() for c in np.atleast_1d(m["channels"])]
        data = _orient(m["data"])
        return data, chs, fs
    except NotImplementedError:
        import h5py
        with h5py.File(path, "r") as f:
            fs = float(np.array(f["Fs"]).ravel()[0])
            ch = f["channels"]
            refs = ch[0] if ch.ndim == 2 else ch[:]
            chs = ["".join(chr(c) for c in np.array(f[r]).ravel()) for r in refs]
            data = _orient(np.array(f["data"]))
        return data, chs, fs
