"""Band powers, relative powers, and slowing ratios (feature_spec §1).

All in log units. Absolute AND relative are reported separately (see §7 interpretation table).
"""
from __future__ import annotations
import numpy as np

DEFAULT_BANDS = {
    "delta": (0.5, 4.0), "theta": (4.0, 7.0), "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0), "low_freq": (0.5, 7.0), "broadband": (0.5, 30.0),
}


def band_auc(freqs: np.ndarray, psd: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Integrate PSD over [lo, hi] per channel (trapezoid). Returns (n_channels,)."""
    raise NotImplementedError("Phase 2")


def log_band_powers(freqs, psd, bands=DEFAULT_BANDS) -> dict:
    """Return {band: log absolute power} per channel."""
    raise NotImplementedError("Phase 2")


def slowing_features(freqs, psd) -> dict:
    """Return absolute/relative delta & theta, LF, DAR, TAR, median freq, SEF, alpha-peak, LF-AUC.

    Δ_abs, Θ_abs, LF_abs = log P[band]
    Δ_rel = log(P[0.5-4]/P[0.5-30]);  Θ_rel = log(P[4-7]/P[0.5-30])
    DAR   = log(P[0.5-4]/P[8-13]);    TAR   = log(P[4-7]/P[8-13])
    """
    raise NotImplementedError("Phase 2")
