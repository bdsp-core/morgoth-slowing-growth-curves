"""Multitaper power spectral density per 15-s segment (feature_spec §1).

Parameters MUST match morgoth-viewer preprocessing so patient and reference features
are computed identically. See config.spectral.
"""
from __future__ import annotations
import numpy as np


def multitaper_psd(segment: np.ndarray, fs: float, nw: float = 4.0, n_tapers: int = 7,
                   fmin: float = 0.5, fmax: float = 30.0):
    """PSD for one (n_channels, n_samples) segment via DPSS tapers.

    Returns (freqs, psd) with psd shape (n_channels, n_freqs). Restricted to [fmin, fmax].
    Implement with scipy.signal.windows.dpss + rfft, averaging over tapers.
    """
    raise NotImplementedError("Phase 2: implement DPSS multitaper matching morgoth-viewer.")
