"""Aggregate a recording's raw feature tensor into region-level slowing features.

Input: the `res` array from a Growth_curves .mat -> per-segment (18 ch x 31 feat).
We use the 6 base band powers (indices 0-5) and recompute ratios FROM region-mean band powers
(correct; avoids averaging ratios). Powers are log-transformed. See docs/data_dictionary.md.
"""
from __future__ import annotations
import numpy as np

# band power column indices in the 31-feature axis
BAND_IDX = {"delta": 0, "theta": 1, "alpha": 2, "beta": 3, "gamma": 4, "total": 5}

# channel indices (order per docs/data_dictionary.md / config/channels_regions.yaml)
CH_NAMES = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",
            "Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2",
            "Fz-Cz", "Cz-Pz"]
_AGG = {
    "L_temporal": [0, 1, 2, 3], "R_temporal": [4, 5, 6, 7],
    "L_parasagittal": [8, 9, 10, 11], "R_parasagittal": [12, 13, 14, 15],
    "midline": [16, 17], "whole_head": list(range(18)),
}
AGG_REGIONS = list(_AGG)                                   # the 6 clinical regions (for segment table)
# full region set = 6 aggregated + 18 individual channels (for recording-level localization)
REGIONS = {**_AGG, **{ch: [i] for i, ch in enumerate(CH_NAMES)}}
# homologous L/R pairs: 2 region-level + 8 individual bipolar-channel pairs (for asymmetry/localization)
_HOMOLOG_CH = [(0, 4), (1, 5), (2, 6), (3, 7), (8, 12), (9, 13), (10, 14), (11, 15)]
ASYM_PAIRS = {"temporal": ("L_temporal", "R_temporal"),
              "parasagittal": ("L_parasagittal", "R_parasagittal"),
              **{f"ch_{CH_NAMES[l]}": (CH_NAMES[l], CH_NAMES[r]) for l, r in _HOMOLOG_CH}}
EPS = 1e-12


def _res_to_tensor(res) -> np.ndarray:
    """res (n_seg x 4 object) -> float tensor (n_seg, 18, 31)."""
    return np.stack([np.asarray(row[3], float) for row in res])


def region_band_powers(tensor: np.ndarray) -> dict:
    """{region: (n_seg, 6) mean linear band power over its channels}.

    The data uses a sentinel (~-156.5) for bad/empty channel-segments; treat any non-positive
    band power as missing (NaN) so it doesn't poison means/logs."""
    bp = tensor[:, :, :6]                                   # (n_seg, 18, 6)
    # a channel-segment is valid only if ALL 6 bands are positive; else drop the whole channel
    # (so region-mean delta and total use the SAME channels -> ratios stay coherent, rel_delta<=1)
    valid = np.all(bp > 0, axis=2, keepdims=True)           # (n_seg, 18, 1)
    clean = np.where(valid, bp, np.nan)
    out = {}
    for reg, chans in REGIONS.items():
        out[reg] = np.nanmean(clean[:, chans, :], axis=1)   # (n_seg, 6 bands), nan-safe
    return out


def _derived(bp: np.ndarray) -> dict:
    """Per-segment derived features from a region's (n_seg, 6) band powers."""
    d, th, a, b, g, tot = [bp[:, i] for i in range(6)]
    return {
        "log_delta": np.log(d + EPS), "log_theta": np.log(th + EPS),
        "log_alpha": np.log(a + EPS), "log_beta": np.log(b + EPS),
        "log_gamma": np.log(g + EPS), "log_total": np.log(tot + EPS),
        "rel_delta": d / (tot + EPS), "rel_theta": th / (tot + EPS), "rel_alpha": a / (tot + EPS),
        "DAR": np.log((d + EPS) / (a + EPS)),   # delta/alpha (slowing high)
        "TAR": np.log((th + EPS) / (a + EPS)),  # theta/alpha
        "DTR": np.log((d + EPS) / (th + EPS)),  # delta/theta
        "low_freq_rel": (d + th) / (tot + EPS),
    }


def recording_features_tensor(tensor, agg=np.nanmedian):
    """Same as recording_features but takes a (n_seg, 18, 31) feature tensor directly
    (e.g. from features.extract.extract on raw EEG) instead of a `res` object array."""
    res = [(5, 0, 0, tensor[i]) for i in range(tensor.shape[0])]   # stage/start/end unused here
    return recording_features(res, agg=agg)


def recording_features(res, agg=np.nanmedian):
    """Return (rows, seg_rows):
      rows: list of dicts, one per region, aggregated over segments (for curves).
      seg_rows: list of dicts, one per (segment, region) (for z-scores/burden/scoring).
    """
    tensor = _res_to_tensor(res)
    rbp = region_band_powers(tensor)
    rows, seg_rows = [], []
    for reg, bp in rbp.items():
        feats = _derived(bp)
        rows.append({"region": reg, "n_segments": bp.shape[0],
                     **{k: float(agg(v)) for k, v in feats.items()}})
        for s in range(bp.shape[0]):
            seg_rows.append({"region": reg, "segment": s, **{k: float(v[s]) for k, v in feats.items()}})
    # asymmetry: log(L/R) of band power, per band, aggregated over segments
    asym = {}
    for name, (lreg, rreg) in ASYM_PAIRS.items():
        for band, bi in BAND_IDX.items():
            if band == "total":
                continue
            ratio = np.log((rbp[lreg][:, bi] + EPS) / (rbp[rreg][:, bi] + EPS))
            asym[f"asym_{name}_{band}"] = float(agg(ratio))
    return rows, seg_rows, asym
