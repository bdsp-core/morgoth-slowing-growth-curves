"""P1 morphology features (docs/morphology_features.md): slow-band spectral shape.

The crude delta-vs-theta band call (threshold on band-power z) agreed with reports only ~0.74.
A faithful, continuous measure of WHERE the slow mass sits is the slow-band spectral centroid and
peak frequency (0.5-8 Hz). Low centroid -> delta-dominant; high -> theta-dominant; mid -> mixed.
Computed from the same multitaper PSD as features/extract.py.
"""
from __future__ import annotations
import numpy as np
from . import extract as ex

SLOW_LO, SLOW_HI = 0.5, 8.0


def slow_shape(freqs, psd):
    """Per-channel slow-band (0.5-8 Hz) centroid, peak freq, and bandwidth (spread).
    psd: (n_ch, n_freq). Returns dict of (n_ch,) arrays."""
    m = (freqs >= SLOW_LO) & (freqs < SLOW_HI)
    f = freqs[m]; p = psd[:, m]
    tot = np.trapz(p, f, axis=1) + 1e-12
    centroid = np.trapz(p * f, f, axis=1) / tot
    peak = f[np.argmax(p, axis=1)]
    spread = np.sqrt(np.trapz(p * (f[None, :] - centroid[:, None]) ** 2, f, axis=1) / tot)
    return {"slow_centroid": centroid, "slow_peak": peak, "slow_spread": spread}


def recording_morphology(data, ch_names, fs=ex.FS, agg=np.nanmedian):
    """Raw referential EEG -> per-region slow-shape features (median over segments).
    Returns list of dicts: {region, slow_centroid, slow_peak, slow_spread}."""
    data = ex.preprocess(data, fs)
    bip = ex.to_bipolar(data, ch_names)
    segs = ex.segment_indices(bip.shape[0])
    # per segment: (18,) centroid/peak/spread
    per_seg = {k: [] for k in ("slow_centroid", "slow_peak", "slow_spread")}
    for s, e in segs:
        f, psd = ex.multitaper_psd(bip[s:e].T, fs)
        sh = slow_shape(f, psd)
        for k in per_seg:
            per_seg[k].append(sh[k])
    arr = {k: np.stack(v) for k, v in per_seg.items()}          # (n_seg, 18)
    rows = []
    for reg, chans in ex_REGIONS().items():
        rows.append({"region": reg,
                     **{k: float(agg(arr[k][:, chans])) for k in arr}})
    return rows


def ex_REGIONS():
    from .recording import _AGG
    return _AGG
