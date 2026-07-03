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


def persistence(is_abnormal, segment_seconds=15, step_seconds=14):
    """Run-length stats of an ordered boolean abnormality series (feature_spec §3).

    Returns longest_run_min, n_episodes, median_episode_min. An "episode" is a maximal run of
    consecutive abnormal segments; duration = segment_seconds + (run_len-1)*step_seconds converted
    to minutes (segments overlap/step by step_seconds)."""
    a = np.asarray(is_abnormal, bool)
    runs = []
    i = 0
    while i < len(a):
        if a[i]:
            j = i
            while j < len(a) and a[j]:
                j += 1
            runs.append(j - i)
            i = j
        else:
            i += 1
    if not runs:
        return {"longest_run_min": 0.0, "n_episodes": 0, "median_episode_min": 0.0}
    dur = lambda n: (segment_seconds + (n - 1) * step_seconds) / 60.0
    durations = [dur(n) for n in runs]
    return {"longest_run_min": max(durations), "n_episodes": len(runs),
            "median_episode_min": float(np.median(durations))}

