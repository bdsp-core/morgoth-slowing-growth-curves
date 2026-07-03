"""Load full BIDS EDF recordings into the referential montage our extractor expects.

The repository EDFs differ from the pre-segmented clips: fs varies (e.g. 256 Hz), 30-50 channels,
mixed naming/case, old vs new 10-20 nomenclature. This harmonizes to the 19 referential channels
(Fp1..O2) at 200 Hz so features/extract.py + morphology + staging run unchanged.
"""
from __future__ import annotations
import numpy as np

CANON = ["Fp1", "F3", "C3", "P3", "F7", "T3", "T5", "O1", "Fz", "Cz", "Pz",
         "Fp2", "F4", "C4", "P4", "F8", "T4", "T6", "O2"]
# new->old 10-20 aliases (T7=T3, etc.) mapped to our canonical names
ALIAS = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}
TARGET_FS = 200.0


def _clean(name):
    n = name.upper().replace("EEG ", "").replace("-REF", "").replace("-LE", "").replace("-AVG", "").strip()
    n = n.split("-")[0].strip()          # "C3-A1" -> "C3"
    n = ALIAS.get(n, n)
    return n


def load_edf_referential(path, target_fs=TARGET_FS):
    """Return (data (n_samp, 19), ch_names=CANON, fs=200). Missing canonical channels -> zeros
    (extract's allow-missing behavior); raises if too few present."""
    import mne
    raw = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
    if abs(raw.info["sfreq"] - target_fs) > 1e-3:
        raw.resample(target_fs, verbose="ERROR")
    # map cleaned (UPPERCASE) name -> canonical -> channel index (first occurrence)
    up2canon = {c.upper(): c for c in CANON}
    idx = {}
    for i, c in enumerate(raw.ch_names):
        canon = up2canon.get(_clean(c))
        if canon and canon not in idx:
            idx[canon] = i
    present = [c for c in CANON if c in idx]
    if len(present) < 15:
        raise ValueError(f"only {len(present)}/19 referential channels in {path}")
    X = raw.get_data()                    # (n_ch, n_samp) volts
    n = X.shape[1]
    out = np.full((n, len(CANON)), np.nan)
    for j, c in enumerate(CANON):
        if c in idx:
            out[:, j] = X[idx[c]] * 1e6   # V -> uV
    # fill any missing canonical channel with the mean of present (keeps bipolar derivations finite)
    if len(present) < len(CANON):
        mean = np.nanmean(out, axis=1)
        for j, c in enumerate(CANON):
            if c not in idx:
                out[:, j] = mean
    return out, CANON, target_fs
