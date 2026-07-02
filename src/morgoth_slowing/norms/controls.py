"""Define and audit the lifespan control cohort (PLAN.md §3, the 'normal' population).

A control = clinically-normal EEG, technically adequate, enough usable staged segments per state,
no strongly EEG-altering meds where known. This module does NOT assume a curated list exists;
it builds one and reports lifespan coverage so gaps (peds, very old, REM) are explicit.
"""
from __future__ import annotations
import pandas as pd


def select_controls(metadata: pd.DataFrame, *, min_usable_segments: int = 20) -> pd.DataFrame:
    """Filter subjects to clinically-normal, technically-adequate controls.

    Requires a normal/abnormal label (structured field or report NLP — see data_sources.md).
    Returns one row per control subject with age, sex, usable-segments-per-state.
    """
    raise NotImplementedError("Phase 1")


def coverage_matrix(controls: pd.DataFrame, age_bands, sexes, states) -> pd.DataFrame:
    """age_band x sex x state -> (n_subjects, total_usable_minutes). Flags thin cells.

    This is the deliverable that answers 'do we have good lifespan representation?'.
    """
    raise NotImplementedError("Phase 1")
