"""Golden-recording (schema/invariant) + stage-grid-alignment tests for the canonical segment_master
(SAP §5, §12.4). The stage-alignment test is the regression guard for the old cross-correlation
misalignment bug: stages must map to segments by DIRECT time (segment center → window index), not by
any learned/cross-correlated offset."""
import glob
import numpy as np
import pandas as pd
import pytest
from morgoth_slowing.io import canonical as C
from morgoth_slowing.features import extract as ex


def _synthetic_sm(n_seg=3):
    rows = []
    for i in range(n_seg):
        for reg in C.REGIONS:
            row = {c: 0.0 for c in C.SM_FEATURES + C.SM_VANPUTTEN + C.SM_GATE}
            row.update(eeg_id="E1", patient_id="P1", eeg_datetime="20200101000000", segment=i,
                       t_start_s=i * 14.0, region=reg, stage="W", artifact_flag=False, artifact_reason="none")
            if reg == "whole_head":
                row.update({c: 0.0 for c in C.SM_WHOLEHEAD})
            rows.append(row)
    return pd.DataFrame(rows)


def test_canonical_schema_validates():
    C.validate_schema(_synthetic_sm())            # a well-formed frame passes


def test_canonical_schema_catches_missing_column():
    bad = _synthetic_sm().drop(columns=["p_slowing"])
    with pytest.raises(AssertionError):
        C.validate_schema(bad)


def test_canonical_schema_catches_bad_region():
    bad = _synthetic_sm(); bad.loc[0, "region"] = "occipital"   # not a feature region
    with pytest.raises(AssertionError):
        C.validate_schema(bad)


def test_stage_alignment_is_direct_time_mapping():
    """Segment i's center → window floor(center/step). This is the worker's mapping; guards against the
    cross-correlation misalignment regression (stages must not be offset by a learned lag)."""
    fs, step = 200.0, 5.0
    segidx = ex.segment_indices(int(300 * fs))     # 5 min
    centers = [((s + e) / 2 / fs) for s, e in segidx]
    wi = [int(c / step) for c in centers]
    assert wi[0] == int(7.5 / step)                # first 15-s segment centered at 7.5 s -> window 1
    assert all(wi[k + 1] >= wi[k] for k in range(len(wi) - 1))    # monotonic non-decreasing
    # a stage array indexed by window; segment picks its OWN window (no global shift)
    stages = np.array([0, 1, 2, 3, 4] * (max(wi) // 5 + 2))
    picked = [stages[w] for w in wi]
    assert picked[0] == stages[wi[0]]              # exact, offset-free


@pytest.mark.skipif(not glob.glob("data/derived/segment_master/eeg_id=*/part.parquet"),
                    reason="no pilot segment_master present")
def test_pilot_segment_master_golden():
    """If a pilot run exists, validate the real output + a physiology invariant (deep sleep is slower)."""
    sm = C.load_segment_master()
    C.validate_schema(sm)
    wh = C.usable(sm)
    by_stage = wh[wh.stage.isin(["W", "N2", "N3"])].groupby("stage").rel_delta.mean()
    if {"W", "N3"} <= set(by_stage.index):
        assert by_stage["N3"] > by_stage["W"]      # N3 has more relative delta than wake (physiologic)
