"""van Putten-lineage metrics vs hand-computed values on synthetic PSDs (SAP §8.7, §12.3).
On a FLAT PSD every band power is height×width, so ratios reduce to width ratios — hand-checkable."""
import numpy as np
from morgoth_slowing.features import vanputten as vp


def _flat_psd(h=2.0):
    freqs = np.arange(0, 50, 0.05)
    return freqs, np.full((18, freqs.size), h)


def test_ratios_on_flat_psd_are_width_ratios():
    f, p = _flat_psd()
    assert np.isclose(vp.dar(f, p), 3 / 5, atol=0.02)         # delta(3) / alpha(5)
    assert np.isclose(vp.adr(f, p), 5 / 3, atol=0.05)         # alpha / delta = 1/DAR
    assert np.isclose(vp.dtabr(f, p), 7 / 22, atol=0.02)      # (3+4)/(5+17)
    assert np.isclose(vp.q_slowing(f, p), 6 / 23, atol=0.02)  # P[2-8]/P[2-25] = 6/23


def test_symmetric_psd_has_zero_asymmetry():
    f, p = _flat_psd()
    assert abs(vp.r_sbsi(f, p)) < 1e-6
    assert abs(vp.pdbsi(f, p)) < 1e-6
    assert vp.q_asym(f, p) < 1e-6
    assert np.isclose(vp.q_apg(f, p), 0.5, atol=1e-6)         # anterior == posterior


def test_right_hemisphere_hotter_gives_positive_signed_bsi():
    f, p = _flat_psd(); p = p.copy(); p[vp.RIGHT] *= 3        # right 3x power -> (3-1)/(3+1)=0.5
    assert np.isclose(vp.pdbsi(f, p), 0.5, atol=0.02)         # signed, positive = right>left
    assert np.isclose(vp.r_sbsi(f, p), 0.5, atol=0.02)        # unsigned magnitude
    assert np.isclose(vp.q_asym(f, p), 0.5, atol=0.02)


def test_median_freq_of_flat_psd_is_band_midpoint():
    f, p = _flat_psd()
    assert np.isclose(vp.median_freq(f, p), (0.5 + 45) / 2, atol=1.0)


def test_peak_freq_finds_the_bump():
    f = np.arange(0, 50, 0.1)
    p = np.full((18, f.size), 1.0) + 10 * np.exp(-((f - 10.0) ** 2) / 2)[None, :]  # 10 Hz peak
    assert abs(vp.peak_freq(f, p) - 10.0) < 1.0
