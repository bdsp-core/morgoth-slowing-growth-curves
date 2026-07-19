"""Assemble the SUBMISSION figure set into figures/manuscript/: multi-panel figures are composited into a
single file with (A)/(B)/... panel labels — the way the journal receives them — not left as separate panel
files. Single-panel figures are copied through. Names track docs/manuscript_draft.md §Figures exactly.

The output folder is WIPED and rebuilt each run, so a rename never leaves an orphan. Missing sources are
reported, not fatal. Part of the `results` reproduce tier (regenerate the panel sources first).

Run: MPLBACKEND=Agg python3 scripts/assemble_manuscript_figures.py
"""
from __future__ import annotations
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("figures/manuscript")
STY = "figures/story"; G = "figures/growth_v2"; SC = "figures/stage_curves"; RF = "results/figs"

# submission figure -> (list of panel source paths, ncols, producing scripts). >1 panel => composited with letters.
FIGS = {
    # ---- MAIN (1 table + 6 figures) ----
    "Figure1_normative_model.png":   ([f"{G}/keystone_growth_grid.png", f"{G}/topo_rel_delta_by_age_stage.png"], 1, "76, 77"),
    "Figure2_detection.png":         ([f"{STY}/s0d_single_occasion_generalized.png", f"{STY}/s0e_occasion_focal.png"], 1, "54, 55, 66"),
    "Figure3_sandor_external.png":   ([f"{STY}/sandor100_slowing.png"], 1, "sandor100_external_validation"),
    "Figure4_example_eeg_reports.png": ([f"{STY}/s4_examples_eeg_panel.png"], 1, "62, 63"),
    "Figure5_description_contrast.png": ([f"{STY}/s4_d2.png", f"{STY}/s4_d5.png"], 2, "57"),
    "Figure6_sleep_underreporting.png": ([f"{G}/v4a_wake_sleep.png"], 1, "fig6_sleep_naming (95b stat)"),
    # ---- SUPPLEMENTARY ----
    "FigureS1_architecture.png":     ([f"{STY}/architecture.png"], 1, "architecture_diagram"),
    "FigureS2_deviation_field.png":  ([f"{STY}/s2_segment_deviation.png"], 1, "44"),
    "FigureS3_curvebank.png":        ([f"{SC}/rel_delta__whole_head.png", f"{SC}/TAR__whole_head.png", f"{SC}/DAR__whole_head.png"], 1, "111"),
    "FigureS4_description_panels.png": ([f"{STY}/s4_d1.png", f"{STY}/s4_d3.png", f"{STY}/s4_d4.png", f"{STY}/s4_d6.png"], 2, "57, 58"),
    "FigureS5_localized_focal.png":  ([f"{STY}/s0_occasion_ours_v4_focal.png"], 1, "49"),
    "FigureS6_severity_null.png":    ([f"{G}/severity_recalibrated.png"], 1, "109"),
    "FigureS7_vanputten.png":        (["figures/figs/vanputten_panel_s7.png"], 1, "vanputten_panel_s7"),
    "FigureS8_topoplot_TAR.png":     ([f"{G}/topo_TAR_by_age_stage.png"], 1, "77"),
}
COLW = 7.0                                                       # inches per panel column


def compose(out_path: Path, panels: list[str], ncols: int) -> bool:
    imgs = []
    for p in panels:
        if not Path(p).exists():
            return False
        imgs.append(plt.imread(p))
    n = len(imgs); nrows = (n + ncols - 1) // ncols
    cell_h = [COLW * im.shape[0] / im.shape[1] for im in imgs]   # height each panel needs at width COLW
    row_h = [max(cell_h[r * ncols:(r + 1) * ncols]) for r in range(nrows)]
    fig = plt.figure(figsize=(COLW * ncols, sum(row_h)))
    gs = fig.add_gridspec(nrows, ncols, height_ratios=row_h, hspace=0.03, wspace=0.03)
    for i, im in enumerate(imgs):
        r, c = divmod(i, ncols)
        ax = fig.add_subplot(gs[r, c]); ax.imshow(im); ax.axis("off")
        if n > 1:
            ax.text(0.0, 1.0, chr(65 + i), transform=ax.transAxes, fontsize=17, fontweight="bold",
                    va="bottom", ha="left")
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    lines = ["# Manuscript figures — composited submission set", "",
             "Built by `scripts/assemble_manuscript_figures.py`: multi-panel figures are composited into one "
             "file with (A)/(B) labels (as submitted); singles are passed through. Regenerate panel sources via "
             "the `results` reproduce tier, then re-run.", "",
             "| submission figure | panels | producing script(s) |", "|---|---|---|"]
    have = miss = 0
    for name, (panels, ncols, scripts) in FIGS.items():
        if compose(OUT / name, panels, ncols):
            have += 1
            lines.append(f"| `{name}` | {len(panels)} ({', '.join(Path(p).name for p in panels)}) | `scripts/{scripts}` |")
        else:
            miss += 1
            missing = [p for p in panels if not Path(p).exists()]
            lines.append(f"| `{name}` | *(missing: {', '.join(missing)})* | `scripts/{scripts}` |")
    (OUT / "MANIFEST.md").write_text("\n".join(lines) + "\n")
    print(f"composited {have} submission figures into {OUT}/ ({miss} with a missing source) + MANIFEST.md")
    if miss:
        for name, (panels, _, _) in FIGS.items():
            missing = [p for p in panels if not Path(p).exists()]
            if missing:
                print(f"    {name} <- missing {missing}")


if __name__ == "__main__":
    main()
