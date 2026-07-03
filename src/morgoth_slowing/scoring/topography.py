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
             burden_thr: float = 2.0, dominance_thr: float = 1.8, asym_thr: float = 2.0) -> str:
    """Return one of: 'focal', 'lateralized', 'generalized', 'multifocal', 'none'.

    region_burdens: {region: patient-level z (burden proxy)}. Thresholds provisional
    (calibrate against expert labels, feature_spec §6).
    """
    vals = {r: v for r, v in region_burdens.items() if np.isfinite(v)}
    abn = {r: v for r, v in vals.items() if v >= burden_thr}
    if not abn:
        return "none"
    dom = dominance_ratio(vals)
    asym_abn = abs(hemisphere_asym_z) >= asym_thr
    if len(abn) >= 2 and dom < dominance_thr and not asym_abn:
        return "generalized"
    if dom >= dominance_thr and asym_abn:
        return "focal"
    if asym_abn:
        return "lateralized"
    if len(abn) >= 2:
        return "multifocal"
    return "focal"
