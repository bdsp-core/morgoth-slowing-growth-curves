"""Panel EEG loaders so the expert-panel recordings featurize through the SAME pipeline as BDSP recordings.

Two non-BIDS sources (SAP §3.6):
  OccasionNoise — full ~50-min EDFs whose headers declare one stray byte before the data block (pyedflib
                  rejects the 00.00.00 startdate); `read_occasion_edf` repairs the header + reads via MNE.
  MoE           — one 15-s referential segment per event, stored as MATLAB v7.3 (HDF5); `read_moe_mat`
                  reads it via h5py.

Both return `(data (n_samp, n_ch) µV, channel_names, fs)` matching `io.edf.load_edf_referential` so the
worker's bipolar/feature/stage/gate path is unchanged. Lifted from scripts/93 (OccasionNoise) + scripts/97
(MoE), which validated them in the Phase-A / MoE analyses.
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np

RENAME = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}   # 10-20 (new) -> double-banana names
NEEDED = ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "C3", "C4",
          "P3", "P4", "O1", "O2", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz"]


def _repair_edf(path):
    """Rewrite a corrected copy if the EDF declares header_bytes = 256*(n_sig+1)+1 (one stray byte).
    The signal data is intact. Returns the original path if no repair is needed."""
    path = Path(path)
    h = open(path, "rb").read(256)
    ns = int(h[252:256]); declared = int(h[184:192]); correct = 256 * (ns + 1)
    if declared == correct:
        return path
    raw = open(path, "rb").read(); body = raw[declared:]
    if len(body) % (2 * ns) != 0:
        raise RuntimeError(f"{path.name}: header {declared} vs {correct}, and body is not sample-aligned")
    hdr = bytearray(raw[:correct]); hdr[184:192] = f"{correct:<8d}".encode()
    out = path.with_name(path.stem + "_fixed.edf"); out.write_bytes(bytes(hdr) + body)
    return out


def read_occasion_edf(path):
    """OccasionNoise EDF -> (data µV (n_samp, 19), NEEDED, 200.0, age, sex)."""
    import mne, warnings
    warnings.filterwarnings("ignore")
    path = _repair_edf(path)
    raw = mne.io.read_raw_edf(str(path), preload=True, verbose="ERROR")
    raw.rename_channels({c: RENAME.get(c.strip(), c.strip()) for c in raw.ch_names})
    missing = [c for c in NEEDED if c not in raw.ch_names]
    if missing:
        raise RuntimeError(f"OccasionNoise {Path(path).name}: missing channels {missing}")
    raw.pick(NEEDED)
    if abs(raw.info["sfreq"] - 200.0) > 1e-6:
        raw.resample(200.0, verbose="ERROR")
    data = raw.get_data().T * 1e6                            # MNE volts -> µV, (n_samp, 19)
    hdr = open(path, "rb").read(88)[8:88].decode("latin-1")  # patient field: "11.0 F X X"
    m = re.match(r"\s*([\d.]+)\s+([MF])", hdr)
    age = float(m.group(1)) if m else np.nan
    sex = m.group(2) if m else "U"
    return data.astype(np.float32), NEEDED, 200.0, age, sex


def read_moe_mat(path):
    """MoE event .mat (MATLAB v7.3/HDF5) -> (data (n_samp, n_ch) µV, channels, fs). One 15-s segment."""
    import h5py
    with h5py.File(path, "r") as h:
        data = np.array(h["data"][()], dtype=np.float32)     # (n_samp, n_ch)
        fs = float(np.array(h["Fs"][()]).flatten()[0])
        refs = np.array(h["channels"][()]).flatten()
        ch = ["".join(chr(int(c)) for c in np.array(h[r][()]).flatten()) for r in refs]
    return data, ch, fs
