"""Prevalence, severity, burden, persistence per state/region/band (feature_spec §3)."""
from __future__ import annotations
import numpy as np


def prevalence(z, tau, weights=None):
    """Fraction of usable (weighted) time with z > tau."""
    z = np.asarray(z)
    w = np.ones_like(z, float) if weights is None else np.asarray(weights, float)
    return float((w * (z > tau)).sum() / w.sum())


def severity(z, tau):
    """Median z among abnormal segments (conditional severity)."""
    z = np.asarray(z)
    abn = z[z > tau]
    return float(np.median(abn)) if abn.size else 0.0


def burden(z, tau, weights=None):
    """Best single number: weighted mean of max(z - tau, 0)."""
    z = np.asarray(z)
    w = np.ones_like(z, float) if weights is None else np.asarray(weights, float)
    return float((w * np.maximum(z - tau, 0.0)).sum() / w.sum())


def persistence(is_abnormal, segment_seconds=15):
    """Return dict: longest_run_min, n_episodes, median_episode_min (feature_spec §3)."""
    raise NotImplementedError("Phase 4: run-length encode the boolean abnormality series.")
