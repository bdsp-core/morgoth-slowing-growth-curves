"""usable_mask / segment_usable on flat, high-amplitude, and normal fixtures (SAP §4.3, §12.3).
Flat segments are the ones that must be caught (the std guard, FLAT_STD_UV=0.5) and FLAGGED not stripped."""
import numpy as np
from morgoth_slowing.features import artifact as af

FS = 200.0
N = 3000  # 15 s


def _seg(sig):
    return np.tile(np.asarray(sig)[:, None], (1, 18))   # (N, 18) same signal on every channel


def test_flat_segment_rejected():
    ok, reason = af.segment_usable(np.zeros((N, 18)), FS)
    assert not ok and reason == "flat"


def test_near_dc_segment_rejected_by_std_guard():
    # tiny std (< FLAT_STD_UV) but a single step so p2p is nonzero — the case the std guard exists for
    sig = np.zeros(N); sig[N // 2:] = 0.3
    ok, reason = af.segment_usable(_seg(sig), FS)
    assert not ok and reason == "flat"


def test_high_amplitude_rejected():
    t = np.arange(N) / FS
    sig = 300 * np.sin(2 * np.pi * 10 * t)              # p2p ~600 uV > HIAMP_UV 500
    ok, reason = af.segment_usable(_seg(sig), FS)
    assert not ok and reason == "high_amplitude"


def test_normal_low_frequency_segment_usable():
    rng = np.random.RandomState(0); t = np.arange(N) / FS
    sig = 30 * np.sin(2 * np.pi * 10 * t) + rng.randn(N) * 3   # ~30 uV alpha, low-freq dominated
    ok, reason = af.segment_usable(_seg(sig), FS)
    assert ok and reason == "ok"


def test_usable_mask_flags_not_strips():
    bip = np.zeros((6000, 18))                          # two flat segments
    mask, reasons = af.usable_mask(bip, [(0, 3000), (3000, 6000)], FS)
    assert mask.sum() == 0                              # both unusable...
    assert len(mask) == 2                               # ...but BOTH still present (flagged, not removed)
    assert reasons.get("flat") == 2
