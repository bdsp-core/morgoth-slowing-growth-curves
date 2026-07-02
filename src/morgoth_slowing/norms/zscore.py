"""Segment-level z-scores against the reference model (feature_spec §2)."""
from __future__ import annotations
import numpy as np


def segment_z(log_power, mu, sigma):
    """z = (log_power - mu) / sigma, elementwise."""
    return (log_power - mu) / sigma


def exceedance(z, tau: float):
    """max(z - tau, 0) — the building block of burden (deviations below tau don't cancel)."""
    return np.maximum(z - tau, 0.0)


def combined_slow_score(z_delta, z_theta, tau: float):
    """S_slow = sqrt(max(z_delta-tau,0)^2 + max(z_theta-tau,0)^2)  (feature_spec §2)."""
    return np.sqrt(exceedance(z_delta, tau) ** 2 + exceedance(z_theta, tau) ** 2)
