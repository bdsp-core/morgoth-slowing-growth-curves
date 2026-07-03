"""Per-segment artifact / flat-segment rejection.

Full clinical recordings contain flat/disconnected stretches, movement/electrode artifact, and EMG
that must be excluded so norms (and per-patient scores) are computed on clean brain signal only.
Operates on a bipolar segment (n_samples, n_ch). Returns a mask of usable segments + reasons.
"""
from __future__ import annotations
import numpy as np
from scipy.signal.windows import dpss

# thresholds (µV / relative); tune against manual review (see docs/artifact_rejection_plan.md)
FLAT_UV = 1.0          # median channel p2p below this = flat/disconnected
HIAMP_UV = 500.0       # channel p2p above this = movement/electrode pop
EMG_REL = 0.55         # fraction of power >20 Hz above this = muscle
FLAT_FRAC = 0.5        # >this fraction of channels flat -> reject segment


def _emg_frac(seg, fs):
    """Fraction of 1-45 Hz power above 20 Hz (EMG proxy), median over channels."""
    x = seg.T  # (n_ch, n_samp)
    n = x.shape[-1]
    tap = dpss(n, 4, Kmax=7)
    fr = np.fft.rfftfreq(n, 1 / fs)
    S = (np.abs(np.fft.rfft(x[:, None, :] * tap[None], axis=-1)) ** 2).mean(1)
    band = (fr >= 1) & (fr < 45); hi = (fr >= 20) & (fr < 45)
    tot = S[:, band].sum(1) + 1e-12
    return np.median(S[:, hi].sum(1) / tot)


def segment_usable(seg, fs=200.0):
    """seg: (n_samp, n_ch) bipolar. Return (usable: bool, reason: str)."""
    p2p = np.ptp(seg, axis=0)                        # per-channel peak-to-peak (µV)
    flat_frac = float(np.mean(p2p < FLAT_UV))
    if flat_frac > FLAT_FRAC or np.median(p2p) < FLAT_UV:
        return False, "flat"
    if np.max(p2p) > HIAMP_UV:
        return False, "high_amplitude"
    if _emg_frac(seg, fs) > EMG_REL:
        return False, "emg"
    return True, "ok"


def usable_mask(bip, seg_indices, fs=200.0):
    """Return boolean array over segments (True = usable) + reason counts."""
    mask = np.zeros(len(seg_indices), bool); reasons = {}
    for i, (s, e) in enumerate(seg_indices):
        ok, r = segment_usable(bip[s:e], fs)
        mask[i] = ok; reasons[r] = reasons.get(r, 0) + 1
    return mask, reasons
