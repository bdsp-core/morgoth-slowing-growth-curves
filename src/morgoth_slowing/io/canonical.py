"""Canonical data access — the ONE way analysis reads the clean-room output (SAP §5), keyed on eeg_id.

Repointing target for the analysis scripts: instead of each script reading a legacy bdsp_id-keyed table
(`segment_features`, `gate_probs`, …), they load through here. Everything is eeg_id-keyed and comes from
`segment_master` + the sidecars produced by scripts/31.
"""
from __future__ import annotations
import glob
from pathlib import Path
import pandas as pd

DERIVED = Path("data/derived")
SM_DIR = DERIVED / "segment_master"

# the canonical segment_master schema (scripts/31) — analysis code should assert against this
SM_ID = ["eeg_id", "patient_id", "eeg_datetime", "segment", "t_start_s", "region", "stage",
         "artifact_flag", "artifact_reason"]
SM_FEATURES = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
               "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
SM_VANPUTTEN = ["DTABR", "ADR", "SEF95", "median_freq", "peak_freq"]          # per region
SM_WHOLEHEAD = ["Q_SLOWING", "Q_APG", "r_sBSI", "pdBSI", "Q_ASYM"]            # whole_head only
SM_GATE = ["p_slowing", "p_focal", "p_generalized"]
REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal", "midline"]


def load_segment_master(eeg_ids=None, columns=None) -> pd.DataFrame:
    """Load segment_master (all partitions, or the given eeg_ids)."""
    if eeg_ids is not None:
        parts = [SM_DIR / f"eeg_id={e}" / "part.parquet" for e in eeg_ids]
        parts = [p for p in parts if p.exists()]
    else:
        parts = glob.glob(str(SM_DIR / "eeg_id=*" / "part.parquet"))
    if not parts:
        raise FileNotFoundError(f"no segment_master partitions under {SM_DIR} — run scripts/31 first")
    return pd.concat([pd.read_parquet(p, columns=columns) for p in parts], ignore_index=True)


def usable(sm: pd.DataFrame, region="whole_head") -> pd.DataFrame:
    """Usable (non-artifact) segments for a region."""
    return sm[(sm.region == region) & (~sm.artifact_flag)]


def load_recording_meta() -> pd.DataFrame:
    return pd.read_parquet(DERIVED / "recording_meta.parquet")


def load_recording_labels() -> pd.DataFrame:
    return pd.read_parquet(DERIVED / "recording_labels.parquet")


def validate_schema(sm: pd.DataFrame) -> None:
    """Assert the canonical invariants (used by analysis + the golden test)."""
    missing = [c for c in SM_ID + SM_FEATURES + SM_VANPUTTEN + SM_GATE if c not in sm.columns]
    assert not missing, f"segment_master missing columns: {missing}"
    assert set(sm.region.unique()) <= set(REGIONS), f"unexpected regions: {set(sm.region.unique())}"
    assert set(sm.stage.unique()) <= {"W", "N1", "N2", "N3", "REM", "Other"}, "unexpected stages"
    # every segment has all 6 regions
    per = sm.groupby(["eeg_id", "segment"]).region.nunique()
    assert (per <= len(REGIONS)).all(), "more region rows than regions per segment"
