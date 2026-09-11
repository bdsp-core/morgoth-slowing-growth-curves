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
# Type is sized for the PRINTED page. Figure 1 stacks this grid under the growth-curve grid (scripts/76), the pair
# is scaled to a 7.0-in column, and the journal fits it inside 190 x 240 mm, where Elsevier requires normal
# lettering >= 7 pt at finished size. The old 5.5-6.8 pt labels printed at 4.6-5.6 pt there. Both producers now keep
# the composite short enough to be width-limited (page scale ~1.0), so 7.5 pt prints at ~7.5 pt and still clears
# 7 pt if the scale slips to 0.93.
TXT = 7.5
STAGE_PT = 9


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
    nrow, ncol = len(STAGES), len(AGE_BINS)
    # Layout in inches, authored at the 7.0-in column it is printed in: anything wider is scaled down, and the type
    # with it. Left band: the stage letter over its n range, both horizontal -- rotated, "n=24--2425" at 7.5 pt is
    # 0.64 in long, longer than a row, so neighbouring rows' ranges would run into each other. Right band: the
    # colourbar, its tick labels and its rotated label.
    FIG_W, LABEL_W, CBAR_W = 7.0, 0.72, 0.66
    CELL_W = (FIG_W - LABEL_W - CBAR_W) / ncol            # ~0.47 in per age bin; "6-12mo" at 7.5 pt needs 0.40
    GAP = 0.05                                            # clear space between neighbouring heads, both directions
    # mne draws the head (nose and ears included) with equal aspect in a box 1.07x taller than wide, so a slot of
    # that shape holds a round, unclipped map with no dead space. That -- not the old 1.7-in-per-column rule --
    # sets the row height: the old rows were ~40% empty, and height is what pushed Figure 1 past the page limit.
    HEAD_W = CELL_W - GAP
    ROW_H = 1.07 * HEAD_W + GAP
    TOP, BOTTOM = 0.17, 0.31                              # one line of age-bin titles; the two-line source note
    FIG_H = TOP + nrow * ROW_H + BOTTOM
    fig = plt.figure(figsize=(FIG_W, FIG_H))

    def inches(x, y, w, h):                               # [left, bottom, width, height] in figure fractions
        return [x / FIG_W, y / FIG_H, w / FIG_W, h / FIG_H]

    def row_y(ri):                                        # bottom edge of row ri's slot (row 0 at the top)
        return FIG_H - TOP - (ri + 1) * ROW_H

    axes = np.array([[fig.add_axes(inches(LABEL_W + ci * CELL_W + GAP / 2, row_y(ri) + GAP / 2,
                                          HEAD_W, ROW_H - GAP)) for ci in range(ncol)] for ri in range(nrow)])
    # ONE colour scale for the whole grid. This was computed per stage, so each row was normalised on its
    # own range (rel_delta: W 0.2-0.4 but N3 0.5-0.6) and carried its own colourbar. The figure invites a
    # vertical comparison -- its title says "by age & sleep stage" -- but under per-row scaling the same red
    # meant ~0.3 more rel_delta in N3 than in W, so the comparison the layout encourages was misleading.
    grid = {}
    for stage in STAGES:
        for (lo, hi) in AGE_BINS:
            sub = tab[(tab.stage == stage) & (tab.age >= lo) & (tab.age < hi)]
            grid[(stage, lo, hi)] = to_electrodes(sub.groupby("region")[feature].median())
    _all = np.concatenate([v[~np.isnan(v)] for v in grid.values()]) if grid else np.array([0, 1])
    vmin, vmax = np.nanpercentile(_all, 5), np.nanpercentile(_all, 95)

    im = None
    for ri, stage in enumerate(STAGES):
        vals_by_bin = [grid[(stage, lo, hi)] for (lo, hi) in AGE_BINS]
        row_n = []
        for ci, ((lo, hi), vals) in enumerate(zip(AGE_BINS, vals_by_bin)):
            ax = axes[ri, ci]
            nrec = tab[(tab.stage == stage) & (tab.age >= lo) & (tab.age < hi)].bdsp_id.nunique()
            if np.isfinite(vals).sum() >= 6:
                im, _ = mne.viz.plot_topomap(np.nan_to_num(vals, nan=np.nanmean(vals)), info, axes=ax,
                                             show=False, cmap="RdYlBu_r", vlim=(vmin, vmax),
                                             contours=4, sensors=True, image_interp="cubic",
                                             extrapolate="head", res=128)
            # age labels on the TOP ROW ONLY. Titling every subplot repeated the band labels five times and
            # collided them with the topoplots above; the per-row n moves beside the stage label instead.
            if ri == 0:
                ax.set_title(BIN_LABELS[ci], fontsize=TXT, pad=3)
            row_n.append(nrec)
        # Stage letter above its n range, right-aligned against the first head, both centred on the row.
        yc = (row_y(ri) + ROW_H / 2) / FIG_H
        xr = (LABEL_W - 0.03) / FIG_W
        fig.text(xr, yc + 0.01 / FIG_H, stage, fontsize=STAGE_PT, fontweight="bold", ha="right", va="bottom")
        if row_n:
            fig.text(xr, yc - 0.01 / FIG_H, f"n={min(row_n)}\u2013{max(row_n)}", fontsize=TXT, ha="right",
                     va="top", color="#555")
    # No in-figure title: Clinical Neurophysiology wants the descriptive title in the caption, and a suptitle
    # here overprinted the top row's labels. What it said -- median per 10-20 electrode over patients, mean of
    # incident bipolar chains, clean-normal EEGs, the recording count -- is in the Figure 1 caption.
    if im is not None:
        # An explicit colourbar axes, not colorbar(ax=[...]): that carves its space out of the maps' slots and
        # would undo the geometry above. Centred on the middle three rows, ~0.09 in clear of the last head.
        cax = fig.add_axes(inches(LABEL_W + ncol * CELL_W + 0.06, row_y(3), 0.085, 3 * ROW_H))
        cb = fig.colorbar(im, cax=cax)
        cb.set_label(palette.flabel(feature), fontsize=TXT); cb.ax.tick_params(labelsize=TXT)
    # A reviewer reads the image before the caption. The n are much smaller than a pooled whole-head count for
    # the same cohort because wake comes from routine studies and sleep from overnight studies, never pooled
    # (ratio features are not comparable across acquisition types) -- so the image says so. No figure number
    # in this string: numbering moves when the text is cut, and a stale cross-reference inside a PNG is
    # invisible to every text check. Two lines: at a printable 7.5 pt one line would be ~7.9 in, wider than the
    # column, and would widen the saved image (shrinking everything else when it is scaled back to 7 in).
    fig.text(0.5, 0.0, "Source-appropriate: wake from routine studies, sleep from overnight studies,\nnever "
                       "pooled \u2014 so sleep-row n are far below pooled whole-head counts.",
             ha="center", va="bottom", fontsize=TXT, color="#555", linespacing=1.2)
    out = Path(f"figures/growth_v2/topo_{feature}_by_age_stage.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    # pad_inches=0.04, not the default 0.1: the saved image is scaled to a 7.0-in column, so every 0.1 in of
    # white border shrinks the type by ~1.4% and adds printed height to Figure 1.
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.04); plt.close(fig)

    # The per-cell coverage the caption quotes. Emitted as a results artifact rather than left only in the
    # figure, so scripts/certify_reproducibility.py check C can find every number the manuscript states.
    res = Path("results/story"); res.mkdir(parents=True, exist_ok=True)
    md = [f"# Topography coverage — {feature} by age x sleep stage (Figure 1B / Figure S3)", "",
          f"Median per 10-20 electrode over patients (mean of the incident bipolar chains), in clean-normal "
          f"recordings from cohort + expansion. Total contributing recordings: **{tab.bdsp_id.nunique():,}**. "
          f"One colour scale spans the whole grid, so rows are directly comparable (N3 is redder than W at "
          f"every age).", "",
          "| stage | " + " | ".join(BIN_LABELS) + " |", "|---|" + "---|" * len(BIN_LABELS)]
    for stage in STAGES:
        ns = [tab[(tab.stage == stage) & (tab.age >= lo) & (tab.age < hi)].bdsp_id.nunique()
              for (lo, hi) in AGE_BINS]
        md.append(f"| {stage} | " + " | ".join(str(n) for n in ns) + " |")
    (res / f"topo_coverage_{feature}.md").write_text("\n".join(md) + "\n")
    print("wrote", out, f"+ results/story/topo_coverage_{feature}.md")


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
