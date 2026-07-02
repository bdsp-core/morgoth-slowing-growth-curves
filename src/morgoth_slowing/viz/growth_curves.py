"""Plot normative growth curves with individual patients overlaid (PLAN.md §6).

The core sanity-check + discovery plot: percentile curves vs age (per sex/state/region/band),
with individual subjects colored by clinical label (normal / focal-slowing / generalized-slowing)
to reveal which features carry discriminative information.
"""
from __future__ import annotations
import pandas as pd


def plot_growth_curve(curves: pd.DataFrame, subjects: pd.DataFrame | None = None, *,
                      feature: str, state: str, region: str, band: str, sex: str, ax=None):
    """Draw percentile lines from `curves`; scatter `subjects` colored by clinical label.

    curves: output of ReferenceModel.percentile_curves (age, p3..p97).
    subjects: optional per-subject points with columns [age, value, label].
    """
    raise NotImplementedError("Phase 3/5")
