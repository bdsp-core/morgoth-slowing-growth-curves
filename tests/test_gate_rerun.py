"""The gate re-run's geometry. Pure functions, so they are cheap to protect and expensive to get wrong."""
import importlib.util, sys
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("gw", "scripts/32_gate_rerun_worker.py")
gw = importlib.util.module_from_spec(spec)
sys.modules["gw"] = gw
spec.loader.exec_module(gw)


def test_step_is_one_second():
    """The 5 s step is the bug this whole re-run exists to fix. Morgoth's reference pipeline uses 1 s."""
    assert gw.GATE_STEP == 1


def test_thirty_row_floor_is_respected():
    """The EEG-level head's CNN reduces length 30x (MaxPool 10 then 3). Under 30 rows it yields ZERO
    transformer tokens and cannot run. We must return None rather than fabricate mean-padding."""
    assert gw.MIN_ROWS == 30
    for T in (10, 15, 29):
        assert gw.context_rows(center_s=7.5, ctx=30, n_rows=T) is None, f"{T} rows must be refused"
    assert gw.context_rows(center_s=15.0, ctx=30, n_rows=30) == (0, 30)


def test_window_is_shifted_to_fit_never_shrunk():
    """At the edges of a recording the window slides inward, keeping its FULL length — so the model always
    sees `ctx` rows of real data. It is never truncated (which would drop below the CNN floor) and never
    padded (which would fabricate input)."""
    T = 100
    for ctx in (30, 60):
        for center in (0.0, 5.0, 50.0, 99.0):
            lo, hi = gw.context_rows(center, ctx, T)
            assert hi - lo == ctx, "window must keep its full length"
            assert 0 <= lo and hi <= T, "window must lie inside the recording"


def test_guard_is_recorded_not_applied():
    """Morgoth zeroes a probability, with no forward pass, when the head's class column never exceeds 1/3.
    We must only RECORD that verdict — the caller stores the model's real output regardless."""
    W = np.full((30, 3), 1 / 3, dtype=np.float32)
    W[:, 1] = 0.05          # focal class never clears 1/3
    W[:, 2] = 0.90          # generalized class does
    assert gw.guard_would_fire(W, 0, 30, class_idx=1) is True
    assert gw.guard_would_fire(W, 0, 30, class_idx=2) is False


def test_contexts_are_multiples_of_the_cnn_factor():
    """30 / 60 / 120 give 1 / 2 / 4 clean transformer tokens with no padding."""
    for c in gw.CONTEXTS:
        assert c % 30 == 0, f"{c}s is not a whole number of CNN-reduced tokens"
        assert (c // 10) // 3 >= 1
