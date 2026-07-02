"""Patient-level 'SD above normal' via the LOSO null burden distribution (feature_spec §4).

The key step: don't call abnormal just because segments exceed z>2. Build a null by scoring every
normal control as if a patient (against a model excluding them), then map patient burden to z.
"""
from __future__ import annotations
import numpy as np
from scipy import stats


def null_burden_distribution(controls_burden):
    """Return the array of per-control burdens (already computed LOSO). Used as the null."""
    return np.asarray(controls_burden, float)


def patient_z_gaussian(patient_burden, null_burden):
    null = np.asarray(null_burden, float)
    return (patient_burden - null.mean()) / null.std(ddof=1)


def patient_z_empirical(patient_burden, null_burden):
    """Z_eq = Phi^-1( F_norm(burden) ) — robust to non-Gaussian burden (feature_spec §4)."""
    null = np.sort(np.asarray(null_burden, float))
    # empirical CDF with continuity correction, clipped away from 0/1
    f = np.searchsorted(null, patient_burden, side="right") / (null.size + 1)
    f = min(max(f, 1.0 / (null.size + 1)), null.size / (null.size + 1))
    return float(stats.norm.ppf(f))
