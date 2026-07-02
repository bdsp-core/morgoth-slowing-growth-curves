"""Normative (growth-curve) models: feature ~ smooth(age) x sex, per state/region/band.

Produces the age x sex percentile curves (feature_spec §1, PLAN.md §5.1). Continuous age,
robust to non-Gaussian distributions. Method selectable: gamlss-style / quantile regression /
robust median-MAD z. Subject is the unit; supports leave-one-subject-out refitting.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


class ReferenceModel:
    def __init__(self, method: str = "gamlss", percentiles=(3, 10, 25, 50, 75, 90, 97)):
        self.method = method
        self.percentiles = percentiles

    def fit(self, df: pd.DataFrame, feature: str, by=("state", "region", "band")):
        """Fit smooth(age) x sex per group. df has columns: subject, age, sex, <group cols>, feature."""
        raise NotImplementedError("Phase 3")

    def location_scale(self, age, sex, state, region, band):
        """Return (mu, sigma) for a query point -> segment z-scoring."""
        raise NotImplementedError("Phase 3")

    def percentile_curves(self, sex, state, region, band, ages=None) -> pd.DataFrame:
        """Return the growth-curve percentile lines for plotting/QC."""
        raise NotImplementedError("Phase 3")

    def fit_loso(self, df, feature, subject_col="subject", **kw):
        """Yield (held_out_subject, model) refit excluding each subject (feature_spec §4)."""
        raise NotImplementedError("Phase 3")
