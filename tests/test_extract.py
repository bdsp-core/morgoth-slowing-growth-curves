"""Band power vs a known integral, and the MAX_ANALYZE_HOURS=24 coverage cap (SAP §4.2/§4.3, §12.3)."""
import numpy as np
from morgoth_slowing.features import extract as ex


def test_band_power_flat_psd_equals_height_times_width():
    freqs = np.arange(0, 50, 0.05)
    psd = np.full((1, freqs.size), 2.0)              # flat PSD, height 2
    bp = ex.band_powers(freqs, psd)
    # trapz over a [lo,hi) grid spans one step short of the full width -> compare with rtol
    assert np.isclose(bp["delta"][0], 2.0 * 3, rtol=0.03)   # 1-4 Hz -> width 3
    assert np.isclose(bp["theta"][0], 2.0 * 4, rtol=0.03)   # 4-8 Hz -> width 4 (theta is 4-8, not 4-7)
    assert np.isclose(bp["alpha"][0], 2.0 * 5, rtol=0.03)   # 8-13 Hz -> width 5


def test_theta_edge_is_4_to_8():
    assert ex.BANDS["theta"] == (4.0, 8.0)
    assert ex.BANDS["alpha"][0] == 8.0             # contiguous, no 7-8 Hz hole


def test_cap_to_hours_truncates_long_recording():
    fs = 200.0
    x = np.zeros((int(30 * 3600 * fs), 2), dtype=np.float32)   # 30 h
    assert ex.cap_to_hours(x, fs).shape[0] == int(24 * 3600 * fs)
    short = np.zeros((1000, 2))
    assert ex.cap_to_hours(short, fs).shape[0] == 1000          # <= cap: unchanged


def test_segment_indices_capped_at_24h():
    n = int(30 * 3600 * 200)                        # 30 h of samples
    segs = ex.segment_indices(n)
    assert segs[-1][1] <= int(ex.MAX_ANALYZE_HOURS * 3600 * 200)
    uncapped = ex.segment_indices(n, max_hours=None)
    assert uncapped[-1][1] > int(24 * 3600 * 200)   # cap is opt-out-able for tests
