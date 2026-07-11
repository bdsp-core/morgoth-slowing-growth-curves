"""Canonical data access — the ONE way analysis reads the clean-room output (SAP §5), keyed on eeg_id.

Grain decided 2026-07-11: segment_master is PER (eeg_id, segment, channel) — 18 bipolar channels — so the
raw feature store keeps channel-level detail; the 6 clinical regions are DERIVED downstream (`to_regions`),
not stored. Three tables (all eeg_id-keyed, produced by scripts/31 + assembled by scripts/33):
  segment_master   — one row per (eeg_id, segment, channel): per-channel features + van Putten.
  segment_summary  — one row per (eeg_id, segment): stage, artifact, per-segment p_slowing, whole-head vP.
  recording_meta   — one row per eeg_id: the run ledger (provenance, hash, stats, EEG-level gate, labels).
Repointing target for analysis scripts: load through here instead of legacy bdsp_id-keyed tables.
"""
from __future__ import annotations
import glob
from pathlib import Path
import pandas as pd
from morgoth_slowing.features.recording import CH_NAMES, _AGG

DERIVED = Path("data/derived")
SM_DIR = DERIVED / "segment_master"
SS_DIR = DERIVED / "segment_summary"

# --- segment_master (per channel) ---
SM_ID = ["eeg_id", "segment", "t_start_s", "channel", "stage", "artifact_flag", "artifact_reason"]
SM_FEATURES = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
               "rel_delta", "rel_theta", "rel_alpha", "log_DAR", "log_TAR", "log_DTR", "low_freq_rel"]
SM_VANPUTTEN = ["DTABR", "ADR", "SEF95", "median_freq", "peak_freq"]      # per channel
CHANNELS = list(CH_NAMES)                                                  # the 18 bipolar derivations
# --- segment_summary (per segment) ---
SS_ID = ["eeg_id", "patient_id", "eeg_datetime", "segment", "t_start_s", "stage",
         "artifact_flag", "artifact_reason"]
SS_GATE = ["p_slowing"]
SS_WHOLEHEAD = ["Q_SLOWING", "Q_APG", "r_sBSI", "pdBSI", "Q_ASYM"]
# --- the 6 clinical regions, DERIVED from channels (whole_head = all 18) ---
REGIONS = list(_AGG)                                                       # whole_head, L/R_temporal, ...
CHAN_REGION = {CH_NAMES[i]: reg for reg, chans in _AGG.items() if reg != "whole_head" for i in chans}
STAGES = {"W", "N1", "N2", "N3", "REM", "Other"}


def _load_parts(root, eeg_ids=None, columns=None) -> pd.DataFrame:
    if eeg_ids is not None:
        parts = [root / f"eeg_id={e}" / "part.parquet" for e in eeg_ids]
        parts = [p for p in parts if p.exists()]
    else:
        parts = glob.glob(str(root / "eeg_id=*" / "part.parquet"))
    if not parts:
        raise FileNotFoundError(f"no partitions under {root} — run scripts/31 first")
    return pd.concat([pd.read_parquet(p, columns=columns) for p in parts], ignore_index=True)


def load_segment_master(eeg_ids=None, columns=None) -> pd.DataFrame:
    """Per-(eeg_id, segment, channel) feature rows (all partitions, or the given eeg_ids)."""
    return _load_parts(SM_DIR, eeg_ids, columns)


def load_segment_summary(eeg_ids=None, columns=None) -> pd.DataFrame:
    """Per-(eeg_id, segment) rows: stage, artifact, p_slowing, whole-head van Putten."""
    return _load_parts(SS_DIR, eeg_ids, columns)


def usable(sm: pd.DataFrame) -> pd.DataFrame:
    """Non-artifact rows (artifact_flag is per-segment, denormalized onto every channel row)."""
    return sm[~sm.artifact_flag]


def to_regions(sm: pd.DataFrame, value_cols=None, agg="mean") -> pd.DataFrame:
    """Aggregate per-channel rows into the 6 clinical regions (SAP §5). Returns rows keyed
    (eeg_id, segment, region). whole_head averages all 18 channels; the five disjoint regions average
    their member channels. Feature/vP columns are averaged (default); this is the region view the
    downstream analyses consume, computed on the fly rather than stored."""
    value_cols = value_cols or [c for c in SM_FEATURES + SM_VANPUTTEN if c in sm.columns]
    keys = [c for c in ["eeg_id", "segment", "t_start_s", "stage", "artifact_flag"] if c in sm.columns]
    dis = sm.copy()
    dis["region"] = dis.channel.map(CHAN_REGION)
    dis = dis.dropna(subset=["region"])
    whole = sm.assign(region="whole_head")
    both = pd.concat([dis, whole], ignore_index=True)
    return both.groupby(keys + ["region"], observed=True)[value_cols].agg(agg).reset_index()


def load_recording_meta() -> pd.DataFrame:
    """The run ledger — one row per eeg_id (scripts/33)."""
    return pd.read_parquet(DERIVED / "recording_meta.parquet")


def load_recording_labels() -> pd.DataFrame:
    return pd.read_parquet(DERIVED / "recording_labels.parquet")


def validate_schema(sm: pd.DataFrame) -> None:
    """Assert the canonical segment_master invariants (used by analysis + the golden test)."""
    missing = [c for c in SM_ID + SM_FEATURES + SM_VANPUTTEN if c not in sm.columns]
    assert not missing, f"segment_master missing columns: {missing}"
    assert set(sm.channel.unique()) <= set(CH_NAMES), f"unexpected channels: {set(sm.channel.unique()) - set(CH_NAMES)}"
    assert set(sm.stage.unique()) <= STAGES, f"unexpected stages: {set(sm.stage.unique()) - STAGES}"
    per = sm.groupby(["eeg_id", "segment"]).channel.nunique()
    assert (per <= len(CH_NAMES)).all(), "more channel rows than channels per segment"


def validate_summary(ss: pd.DataFrame) -> None:
    missing = [c for c in SS_ID + SS_GATE + SS_WHOLEHEAD if c not in ss.columns]
    assert not missing, f"segment_summary missing columns: {missing}"
    assert not ss.duplicated(["eeg_id", "segment"]).any(), "segment_summary must be one row per (eeg_id, segment)"
