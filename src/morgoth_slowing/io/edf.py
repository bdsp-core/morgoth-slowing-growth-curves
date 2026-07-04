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


def _uv_scale(unit):
    """Physical-dimension string -> factor to microvolts."""
    u = (unit or "").strip().lower()
    if u in ("uv", "µv", "microvolt", "microvolts"):
        return 1.0
    if u in ("mv", "millivolt", "millivolts"):
        return 1e3
    if u in ("v", "volt", "volts"):
        return 1e6
    return 1.0                             # unknown -> assume already uV (EDF convention)


def load_edf_referential(path, target_fs=TARGET_FS):
    """Return (data (n_samp, 19) float32 uV, ch_names=CANON, fs=200).

    Reads ONE channel at a time via pyedflib and resamples it to target_fs before moving on, so peak
    memory is ~(one raw channel + the 19-channel float32 output) rather than the whole 30-50 ch file at
    float64 (which OOMs 16 GB on multi-hour recordings). Missing canonical channels -> row-mean fill;
    raises if too few present.
    """
    import pyedflib
    from fractions import Fraction
    from scipy.signal import resample_poly

    f = pyedflib.EdfReader(str(path))
    try:
        labels = f.getSignalLabels()
        fss = f.getSampleFrequencies()
        up2canon = {c.upper(): c for c in CANON}
        idx = {}                           # canonical -> signal index (first occurrence)
        for i, lab in enumerate(labels):
            canon = up2canon.get(_clean(lab))
            if canon and canon not in idx:
                idx[canon] = i
        present = [c for c in CANON if c in idx]
        if len(present) < 15:
            raise ValueError(f"only {len(present)}/19 referential channels in {path}")

        # reference output length from the first present channel
        i0 = idx[present[0]]
        n = int(round(f.getNSamples()[i0] * target_fs / fss[i0]))
        out = np.full((n, len(CANON)), np.nan, dtype=np.float32)
        for j, c in enumerate(CANON):
            if c not in idx:
                continue
            i = idx[c]
            x = f.readSignal(i).astype(np.float64) * _uv_scale(f.getPhysicalDimension(i))  # -> uV
            if abs(fss[i] - target_fs) > 1e-3:
                frac = Fraction(target_fs / fss[i]).limit_denominator(1000)
                x = resample_poly(x, frac.numerator, frac.denominator)
            if len(x) >= n:                # align all channels to n (truncate / edge-pad)
                x = x[:n]
            else:
                x = np.pad(x, (0, n - len(x)), mode="edge")
            out[:, j] = x.astype(np.float32)
            del x
    finally:
        f._close()

    # fill any missing canonical channel with the row-mean of present (keeps bipolar derivations finite)
    if len(present) < len(CANON):
        mean = np.nanmean(out, axis=1)
        for j, c in enumerate(CANON):
            if c not in idx:
                out[:, j] = mean
    return out, CANON, target_fs
