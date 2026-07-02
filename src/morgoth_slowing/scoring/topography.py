"""Classify slowing as focal / lateralized / generalized / multifocal (feature_spec §6)."""
from __future__ import annotations
import numpy as np

EPS = 1e-6


def dominance_ratio(region_burdens: dict) -> float:
    """max-region burden / (median of other regions + eps)."""
    vals = np.array(list(region_burdens.values()), float)
    if vals.size < 2:
        return float("inf")
    top = vals.max()
    others = np.delete(vals, vals.argmax())
    return float(top / (np.median(others) + EPS))


def classify(region_burdens: dict, hemisphere_asym_z: float,
             burden_thr: float, dominance_thr: float, asym_thr: float = 2.0) -> str:
    """Return one of: 'focal', 'lateralized', 'generalized', 'multifocal', 'none'.

    Rules (calibrate thresholds against expert labels, feature_spec §6):
      - none: no region above burden_thr
      - focal: single dominant region (dominance high) above threshold
      - lateralized: one hemisphere abnormal + abnormal hemisphere asymmetry
      - generalized: many regions abnormal, low dominance, asymmetry not abnormal
      - multifocal: >=2 noncontiguous abnormal regions, low dominance
    """
    raise NotImplementedError("Phase 4: implement decision rules + calibrate thresholds.")
