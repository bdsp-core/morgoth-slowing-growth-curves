"""Reproducible Python feature extraction from RAW EEG -> the Growth_curves 18x31 representation.

The original Growth_curves features were precomputed (MATLAB, code unavailable). This module
recomputes them from raw referential EEG so new recordings (e.g. from the BDSP repository) can be
featurized identically, in Python, reproducibly. Validated against JJ's features (see
scripts/12_validate_extractor.py): tune BANDS / multitaper params until per-channel band powers match.

Pipeline: referential -> 18 bipolar (double-banana) -> 15-s segments (3000 samp @200Hz, step 2800)
-> multitaper PSD per segment/channel -> 31 features (5 band powers + total + rel + ratios).
"""
from __future__ import annotations
import numpy as np
from scipy.signal.windows import dpss

# 18 bipolar derivations as (anode, cathode) referential channel names (double banana)
BIPOLAR = [
    ("Fp1", "F7"), ("F7", "T3"), ("T3", "T5"), ("T5", "O1"),
    ("Fp2", "F8"), ("F8", "T4"), ("T4", "T6"), ("T6", "O2"),
    ("Fp1", "F3"), ("F3", "C3"), ("C3", "P3"), ("P3", "O1"),
    ("Fp2", "F4"), ("F4", "C4"), ("C4", "P4"), ("P4", "O2"),
    ("Fz", "Cz"), ("Cz", "Pz"),
]
# band edges (Hz). delta low-edge = 1.0 (not 0.5): the 0.5-1 Hz range is dominated by sub-delta
# drift/1-f and artifact and inflated relative-delta ~0.5 vs the ~0.30 reference; delta 1-4 is a
# standard clinical convention and calibrates rel_delta to JJ's precomputed features (median 0.33 vs
# 0.30). See docs/feature_extraction.md.
BANDS = {"delta": (1.0, 4.0), "theta": (4.0, 7.0), "alpha": (8.0, 13.0),
         "beta": (13.0, 30.0), "gamma": (30.0, 45.0), "total": (0.5, 45.0)}
SEG_SAMPLES = 3000     # 15 s @ 200 Hz
SEG_STEP = 2800        # 14 s (1 s overlap) — matches Growth_curves res
FS = 200.0
NW = 4.0               # time-bandwidth product
N_TAPERS = 7


def preprocess(data, fs=FS, hp=0.5, notch=60.0):
    """High-pass (remove drift that inflates delta) + notch (line noise). data (n_samp, n_ch).

    Filters ONE channel at a time into a preallocated output, so peak memory is ~2x `data` instead of
    the ~4x transient of a whole-array filtfilt (which OOMs 16 GB on multi-hour recordings).
    Per-channel filtfilt is numerically identical to the axis-wise version.
    """
    from scipy.signal import butter, filtfilt, iirnotch
    b, a = butter(4, hp / (fs / 2), btype="high")
    notches = [iirnotch(f0, 30, fs) for f0 in (60.0, 50.0) if f0 < fs / 2]  # US + intl line noise
    out = np.empty_like(data)
    for c in range(data.shape[1]):
        y = filtfilt(b, a, data[:, c])
        for bn, an in notches:
            y = filtfilt(bn, an, y)
        out[:, c] = y
    return out


def to_bipolar(data, ch_names):
    """data (n_samples, n_ch) referential -> (n_samples, 18) bipolar in BIPOLAR order.

    Subtracts directly into a preallocated array (no list of 18 full-length temporaries)."""
    idx = {c: i for i, c in enumerate(ch_names)}
    out = np.empty((data.shape[0], len(BIPOLAR)), dtype=data.dtype)
    for k, (a, b) in enumerate(BIPOLAR):
        np.subtract(data[:, idx[a]], data[:, idx[b]], out=out[:, k])
    return out


def segment_indices(n_samples, seg=SEG_SAMPLES, step=SEG_STEP):
    starts = list(range(0, n_samples - seg + 1, step))
    return [(s, s + seg) for s in starts]


def multitaper_psd(x, fs=FS, nw=NW, k=N_TAPERS):
    """x (n_ch, n_samp) -> (freqs, psd (n_ch, n_freq)) one-sided, averaged over k DPSS tapers."""
    from scipy.signal import detrend
    x = detrend(x, axis=-1, type="linear")            # remove DC/linear drift per channel
    n = x.shape[-1]
    tapers = dpss(n, nw, Kmax=k)                      # (k, n)
    freqs = np.fft.rfftfreq(n, d=1 / fs)
    xt = x[:, None, :] * tapers[None, :, :]           # (n_ch, k, n)
    S = np.abs(np.fft.rfft(xt, axis=-1)) ** 2         # (n_ch, k, n_freq)
    psd = S.mean(axis=1) / fs                         # average tapers
    return freqs, psd


def band_powers(freqs, psd, bands=BANDS):
    """Return dict band -> (n_ch,) integrated power (trapezoid)."""
    out = {}
    for b, (lo, hi) in bands.items():
        m = (freqs >= lo) & (freqs < hi)
        out[b] = np.trapz(psd[:, m], freqs[m], axis=1)
    return out


def features_31(bp):
    """31 features per channel in FEATURE_NAMES order, from band powers dict (n_ch each)."""
    d, th, a, be, g, tot = (bp["delta"], bp["theta"], bp["alpha"], bp["beta"], bp["gamma"], bp["total"])
    eps = 1e-12
    def r(x, y): return x / (y + eps)
    cols = [d, th, a, be, g, tot,
            r(d, tot), r(th, tot), r(a, tot), r(be, tot), r(g, tot),
            r(d, th), r(d, a), r(d, be), r(d, g),
            r(th, d), r(th, a), r(th, be), r(th, g),
            r(a, d), r(a, th), r(a, be), r(a, g),
            r(be, d), r(be, th), r(be, a), r(be, g),
            r(g, d), r(g, th), r(g, a), r(g, be)]
    return np.stack(cols, axis=1)   # (n_ch, 31)


def extract(data, ch_names, fs=FS):
    """Raw referential EEG (n_samples, n_ch) -> feature tensor (n_segments, 18, 31), matching
    the Growth_curves `res` col-4 layout. Also returns segment (start,end) sample indices."""
    data = preprocess(data, fs)                      # high-pass + notch
    bip = to_bipolar(data, ch_names)                 # (n_samp, 18)
    segs = segment_indices(bip.shape[0])
    out = []
    for s, e in segs:
        freqs, psd = multitaper_psd(bip[s:e].T, fs)  # (18, n_freq)
        out.append(features_31(band_powers(freqs, psd)))
    return np.stack(out), segs                        # (n_seg, 18, 31)
