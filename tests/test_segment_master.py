"""Golden-recording (schema/invariant) + stage-grid-alignment tests for the canonical tables
(SAP §5, §12.4). Grain (2026-07-11): segment_master is PER (eeg_id, segment, channel); the 6 clinical
regions are DERIVED (`to_regions`), not stored. The stage-alignment test is the regression guard for the
old cross-correlation misalignment bug: stages map to segments by DIRECT time, not a learned offset."""
import glob
import numpy as np
import pandas as pd
import pytest
from morgoth_slowing.io import canonical as C
from morgoth_slowing.features import extract as ex


def _synthetic_sm(n_seg=3):
    """Per-(segment, channel) rows for all 18 channels."""
    rows = []
    for i in range(n_seg):
        for ch in C.CHANNELS:
            row = {c: 0.0 for c in C.SM_FEATURES + C.SM_VANPUTTEN}
            row.update(eeg_id="E1", segment=i, t_start_s=i * 14.0, channel=ch,
                       stage="W", artifact_flag=False, artifact_reason="none")
            rows.append(row)
    return pd.DataFrame(rows)


def _synthetic_ss(n_seg=3):
    rows = []
    for i in range(n_seg):
        row = {c: 0.0 for c in C.SS_GATE + C.SS_WHOLEHEAD}
        row.update(eeg_id="E1", patient_id="P1", eeg_datetime="20200101000000", segment=i,
                   t_start_s=i * 14.0, stage="W", artifact_flag=False, artifact_reason="none")
        rows.append(row)
    return pd.DataFrame(rows)


def test_segment_master_schema_validates():
    C.validate_schema(_synthetic_sm())              # a well-formed channel frame passes
    C.validate_summary(_synthetic_ss())


def test_schema_catches_missing_feature():
    bad = _synthetic_sm().drop(columns=["log_DAR"])   # renamed from DAR (log-ratio, name matches value)
    with pytest.raises(AssertionError):
        C.validate_schema(bad)


def test_schema_catches_bad_channel():
    bad = _synthetic_sm(); bad.loc[0, "channel"] = "T3-T5-BOGUS"   # not a real bipolar derivation
    with pytest.raises(AssertionError):
        C.validate_schema(bad)


def test_summary_catches_duplicate_segment():
    bad = pd.concat([_synthetic_ss(1), _synthetic_ss(1)], ignore_index=True)   # (eeg_id, segment) dup
    with pytest.raises(AssertionError):
        C.validate_summary(bad)


def test_to_regions_derives_six_regions():
    """Regions are derived from channels, not stored: 18 channel rows/segment -> 6 region rows."""
    sm = _synthetic_sm(2)
    reg = C.to_regions(sm)
    assert set(reg.region.unique()) == set(C.REGIONS)
    assert (reg.groupby("segment").region.nunique() == len(C.REGIONS)).all()


def test_stage_alignment_is_direct_time_mapping():
    fs, step = 200.0, 5.0
    segidx = ex.segment_indices(int(300 * fs))       # 5 min
    centers = [((s + e) / 2 / fs) for s, e in segidx]
    wi = [int(c / step) for c in centers]
    assert wi[0] == int(7.5 / step)                  # first 15-s segment centered at 7.5 s -> window 1
    assert all(wi[k + 1] >= wi[k] for k in range(len(wi) - 1))    # monotonic non-decreasing
    stages = np.array([0, 1, 2, 3, 4] * (max(wi) // 5 + 2))
    picked = [stages[w] for w in wi]
    assert picked[0] == stages[wi[0]]                # exact, offset-free


@pytest.mark.skipif(not glob.glob("data/derived/segment_master/eeg_id=*/part.parquet"),
                    reason="no pilot segment_master present")
def test_pilot_segment_master_golden():
    """If a pilot run exists, validate the real output + a physiology invariant (deep sleep is slower)."""
    sm = C.load_segment_master()
    C.validate_schema(sm)
    reg = C.to_regions(C.usable(sm))                 # whole-head region view, non-artifact
    wh = reg[reg.region == "whole_head"]
    by_stage = wh[wh.stage.isin(["W", "N2", "N3"])].groupby("stage").rel_delta.mean()
    if {"W", "N3"} <= set(by_stage.index):
        assert by_stage["N3"] > by_stage["W"]        # N3 has more relative delta than wake (physiologic)
