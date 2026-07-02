"""Load 15-s staged EEG segments and per-subject metadata.

Shape of the returned data depends on what Growth_curves/ actually contains (Phase 0):
precomputed features vs. raw/BIDS EEG. Provide a common interface either way.
"""
from __future__ import annotations
import pandas as pd


def load_subject_segments(subject_id: str, config: dict) -> pd.DataFrame:
    """One row per (segment, channel/region, band) with: state, age, sex, feature values.

    If features are precomputed on S3, read them; if raw EEG, run features/spectra + bandpower.
    """
    raise NotImplementedError("Phase 0/2")


def load_metadata(config: dict) -> pd.DataFrame:
    """Subject-level table: subject, age, sex, normal/abnormal label, focal/generalized label,
    usable-segments-per-state. Backbone for control selection and discrimination analysis."""
    raise NotImplementedError("Phase 0")
