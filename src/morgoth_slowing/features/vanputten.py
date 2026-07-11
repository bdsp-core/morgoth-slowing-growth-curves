"""van Putten-lineage qEEG slowing / asymmetry metrics (SAP §8.7; definitions in references/README.md).

All operate on a multitaper PSD `psd` of shape (18, n_freq) in the fixed BIPOLAR channel order
(see features/extract.py BIPOLAR) with matching `freqs`. Band power is the trapezoid integral of the PSD
over the band, per channel. Whole-head scalars average power over the selected channels then take the
ratio (matching how DAR / Q_SLOWING are reported). `idx` selects a channel subset (default: all 18).

Metrics:
  dar, adr, dtabr, q_slowing              -- global slowing ratios (Finnigan & van Putten 2013; Lodder 2013)
  sef, median_freq, peak_freq             -- spectral-edge / dominant-frequency summaries
  q_apg                                   -- anterior/posterior alpha gradient (Lodder & van Putten 2013)
  r_sbsi, pdbsi                           -- revised (power-based) BSI + our signed extension (van Putten 2007)
  q_asym                                  -- per-homologous-pair normalized spectral difference (Lodder 2013)
"""
from __future__ import annotations
import numpy as np

EPS = 1e-12
# BIPOLAR order 0..17: L/R hemispheres, homologous pairs, anterior/posterior (see extract.BIPOLAR)
LEFT = [0, 1, 2, 3, 8, 9, 10, 11]
RIGHT = [4, 5, 6, 7, 12, 13, 14, 15]
HOMOLOG_PAIRS = [(0, 4), (1, 5), (2, 6), (3, 7), (8, 12), (9, 13), (10, 14), (11, 15)]
ANTERIOR = [0, 1, 4, 5, 8, 9, 12, 13, 16]     # frontal/anterior-temporal chains + Fz-Cz
POSTERIOR = [2, 3, 6, 7, 10, 11, 14, 15, 17]  # posterior-temporal/parieto-occipital chains + Cz-Pz


def _bandpow(freqs, psd, lo, hi, idx=None):
    """Mean over selected channels of the trapezoid band power [lo, hi)."""
    m = (freqs >= lo) & (freqs < hi)
    p = psd[:, m] if idx is None else psd[np.asarray(idx)][:, m]
    return float(np.mean(np.trapz(p, freqs[m], axis=1)))


# ---- global slowing ratios ----------------------------------------------------------------------
def dar(freqs, psd, idx=None):      # delta / alpha (higher = slower)
    return _bandpow(freqs, psd, 1, 4, idx) / (_bandpow(freqs, psd, 8, 13, idx) + EPS)


def adr(freqs, psd, idx=None):      # alpha / delta = 1 / DAR
    return _bandpow(freqs, psd, 8, 13, idx) / (_bandpow(freqs, psd, 1, 4, idx) + EPS)


def dtabr(freqs, psd, idx=None):    # (delta + theta) / (alpha + beta)
    lo = _bandpow(freqs, psd, 1, 4, idx) + _bandpow(freqs, psd, 4, 8, idx)
    hi = _bandpow(freqs, psd, 8, 13, idx) + _bandpow(freqs, psd, 13, 30, idx)
    return lo / (hi + EPS)


def q_slowing(freqs, psd, idx=None):    # P[2-8] / P[2-25]  (Lodder & van Putten 2013; abnormal > 0.6)
    return _bandpow(freqs, psd, 2, 8, idx) / (_bandpow(freqs, psd, 2, 25, idx) + EPS)


# ---- spectral-edge / dominant-frequency ---------------------------------------------------------
def sef(freqs, psd, frac=0.95, idx=None, band=(0.5, 45.0)):
    """Spectral edge: frequency below which `frac` of the band's power lies (mean PSD over channels)."""
    m = (freqs >= band[0]) & (freqs <= band[1])
    p = psd[:, m] if idx is None else psd[np.asarray(idx)][:, m]
    mp = p.mean(axis=0)
    c = np.cumsum(mp)
    c = c / (c[-1] + EPS)
    i = int(np.searchsorted(c, frac))
    fb = freqs[m]
    return float(fb[min(i, len(fb) - 1)])


def median_freq(freqs, psd, idx=None, band=(0.5, 45.0)):
    return sef(freqs, psd, frac=0.5, idx=idx, band=band)


def peak_freq(freqs, psd, idx=None, band=(1.0, 45.0)):
    """Dominant frequency: argmax of the mean PSD over `band`."""
    m = (freqs >= band[0]) & (freqs <= band[1])
    p = psd[:, m] if idx is None else psd[np.asarray(idx)][:, m]
    mp = p.mean(axis=0)
    return float(freqs[m][int(np.argmax(mp))])


# ---- spatial (asymmetry / gradient) -------------------------------------------------------------
def q_apg(freqs, psd):      # anterior alpha / (anterior + posterior) alpha; > 0.6 = anterior shift
    a = _bandpow(freqs, psd, 8, 13, ANTERIOR)
    p = _bandpow(freqs, psd, 8, 13, POSTERIOR)
    return a / (a + p + EPS)


def _hemi_power(freqs, psd, band=(0.5, 25.0)):
    m = (freqs >= band[0]) & (freqs < band[1])
    R = psd[RIGHT][:, m].mean(axis=0)   # mean power over right-hemisphere channels, per frequency bin
    L = psd[LEFT][:, m].mean(axis=0)
    return R, L


def r_sbsi(freqs, psd):     # revised (power-based) spatial BSI, 0.5-25 Hz (van Putten 2007); 0 = symmetric
    R, L = _hemi_power(freqs, psd)
    return float(np.mean(np.abs(R - L) / (R + L + EPS)))


def pdbsi(freqs, psd):      # our SIGNED extension: + => right > left (lateralization)
    R, L = _hemi_power(freqs, psd)
    return float(np.mean((R - L) / (R + L + EPS)))


def q_asym(freqs, psd, band=(0.5, 25.0), reduce="max"):
    """Normalized spectral difference per homologous pair (mean over freq of |R-L|/(R+L)).
    reduce='max' -> the largest pair asymmetry (Lodder's 'any pair > 0.5'); reduce='dict' -> per pair."""
    m = (freqs >= band[0]) & (freqs < band[1])
    vals = {}
    for l, r in HOMOLOG_PAIRS:
        Rp, Lp = psd[r, m], psd[l, m]
        vals[(l, r)] = float(np.mean(np.abs(Rp - Lp) / (Rp + Lp + EPS)))
    if reduce == "dict":
        return vals
    return max(vals.values())
