"""Topoplots of a slowing feature across the head, by age and sleep stage — the SPATIAL view of the
normative growth curves. Each of the 18 bipolar channels is monopolarized onto the standard_1020 layout
(mne). Rows = sleep stages (W/N1/N2/N3/REM), cols = age bins (finer at young ages, coarser at old).
Clean-normal recordings only, source-appropriate (wake from routine cohort, sleep from overnight expansion).

Shows the developmental spatial story the whole-head growth curves compress: frontal-predominant delta,
highest in infancy across every stage, declining monotonically with age; deep sleep (N3) highest.

No CLI arg -> renders the story defaults (rel_delta, TAR). Pass a feature name to render just one.
Run: PYTHONPATH=src python scripts/77_topoplots_by_age.py [feature]
Writes figures/growth_v2/topo_<feature>_by_age_stage.png (promoted from scripts/archive/68_topoplots_by_age.py).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (applies shared Tufte publication style)
import mne

DEFAULT_FEATURES = ["rel_delta", "TAR"]
TABLE = "data/derived/channel_stage_features.parquet"
PAIRS = {
    "Fp1-F7": ("Fp1", "F7"), "F7-T3": ("F7", "T3"), "T3-T5": ("T3", "T5"), "T5-O1": ("T5", "O1"),
    "Fp2-F8": ("Fp2", "F8"), "F8-T4": ("F8", "T4"), "T4-T6": ("T4", "T6"), "T6-O2": ("T6", "O2"),
    "Fp1-F3": ("Fp1", "F3"), "F3-C3": ("F3", "C3"), "C3-P3": ("C3", "P3"), "P3-O1": ("P3", "O1"),
    "Fp2-F4": ("Fp2", "F4"), "F4-C4": ("F4", "C4"), "C4-P4": ("C4", "P4"), "P4-O2": ("P4", "O2"),
    "Fz-Cz": ("Fz", "Cz"), "Cz-Pz": ("Cz", "Pz"),
}
CHANS = list(PAIRS)
NAME_MAP = {"T3": "T7", "T4": "T8", "T5": "P7", "T6": "P8"}
ELECTRODES = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T3", "C3", "Cz", "C4", "T4",
              "T5", "P3", "Pz", "P4", "T6", "O1", "O2"]
INCIDENT = {e: [c for c, (a, b) in PAIRS.items() if e in (a, b)] for e in ELECTRODES}
STAGES = ["W", "N1", "N2", "N3", "REM"]
AGE_BINS = [(0, 1/12), (1/12, 3/12), (3/12, 6/12), (6/12, 1), (1, 2), (2, 5),
            (5, 10), (10, 20), (20, 40), (40, 60), (60, 80), (80, 120)]
BIN_LABELS = ["<1mo", "1-3mo", "3-6mo", "6-12mo", "1-2y", "2-5y", "5-10y",
              "10-20", "20-40", "40-60", "60-80", "80+"]


def montage_info():
    info = mne.create_info(ch_names=[NAME_MAP.get(e, e) for e in ELECTRODES], sfreq=200, ch_types="eeg")
    info.set_montage(mne.channels.make_standard_montage("standard_1020"))
    return info


def to_electrodes(chan_series):
    out = []
    for e in ELECTRODES:
        v = [chan_series.get(c) for c in INCIDENT[e]]
        v = [x for x in v if x is not None and np.isfinite(x)]
        out.append(np.mean(v) if v else np.nan)
    return np.array(out)


def render(tab, info, feature):
    fig, axes = plt.subplots(len(STAGES), len(AGE_BINS), figsize=(1.7 * len(AGE_BINS), 2.3 * len(STAGES)))
    for ri, stage in enumerate(STAGES):
        vals_by_bin = []
        for (lo, hi) in AGE_BINS:
            sub = tab[(tab.stage == stage) & (tab.age >= lo) & (tab.age < hi)]
            vals_by_bin.append(to_electrodes(sub.groupby("region")[feature].median()))
        allv = np.concatenate([v[~np.isnan(v)] for v in vals_by_bin]) if vals_by_bin else np.array([0, 1])
        vmin, vmax = np.nanpercentile(allv, 5), np.nanpercentile(allv, 95)
        im = None
        for ci, ((lo, hi), vals) in enumerate(zip(AGE_BINS, vals_by_bin)):
            ax = axes[ri, ci]
            nrec = tab[(tab.stage == stage) & (tab.age >= lo) & (tab.age < hi)].bdsp_id.nunique()
            if np.isfinite(vals).sum() >= 6:
                im, _ = mne.viz.plot_topomap(np.nan_to_num(vals, nan=np.nanmean(vals)), info, axes=ax,
                                             show=False, cmap="RdYlBu_r", vlim=(vmin, vmax),
                                             contours=4, sensors=True, image_interp="cubic",
                                             extrapolate="head", res=128)
            ax.set_title(f"{BIN_LABELS[ci]}\nn={nrec}", fontsize=8)
            if ci == 0:
                ax.text(-0.3, 0.5, stage, transform=ax.transAxes, fontsize=12, fontweight="bold",
                        rotation=90, va="center")
        if im is not None:
            fig.colorbar(im, ax=list(axes[ri]), fraction=0.015, pad=0.01).set_label(feature, fontsize=8)
    fig.suptitle(f"Regional {feature} across the head by age & sleep stage (normal EEGs, cohort+expansion)\n"
                 f"per 10-20 electrode (median over patients, mean of incident bipolar chains); "
                 f"n={tab.bdsp_id.nunique()} recordings", fontsize=12)
    out = Path(f"figures/growth_v2/topo_{feature}_by_age_stage.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=125, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


def main():
    features = [sys.argv[1]] if len(sys.argv) > 1 else DEFAULT_FEATURES
    info = montage_info()
    tab = pd.read_parquet(TABLE)
    if "clean_normal" not in tab.columns:
        lu = pd.read_parquet("data/derived/labels_unified.parquet")[["bdsp_id", "clean_normal"]]
        tab = tab.merge(lu, on="bdsp_id", how="left"); tab["clean_normal"] = tab.clean_normal.fillna(True)
    tab = tab[(tab.clean_normal == True) & tab.region.isin(CHANS) & tab.age.between(0, 95)]
    if "src" in tab.columns:
        SS = {"W": "cohort", "N1": "cohort", "N2": "expansion", "N3": "expansion", "REM": "expansion"}
        tab = tab[tab.apply(lambda r: r.src == SS.get(r.stage, "expansion"), axis=1)]
    print(f"channel table: {tab.bdsp_id.nunique()} recordings (clean-normal, source-appropriate)")
    for feat in features:
        render(tab, info, feat)


if __name__ == "__main__":
    main()
