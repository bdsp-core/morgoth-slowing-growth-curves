"""Assemble the SUBMISSION figure set into figures/manuscript/: multi-panel figures are composited into a
single file with (A)/(B)/... panel labels — the way the journal receives them — not left as separate panel
files. Single-panel figures are copied through. Names track docs/manuscript_draft.md §Figures exactly.

The output folder is WIPED and rebuilt each run, so a rename never leaves an orphan. Missing sources are
reported, not fatal. Part of the `results` reproduce tier (regenerate the panel sources first).

Run: MPLBACKEND=Agg python3 scripts/assemble_manuscript_figures.py
"""
from __future__ import annotations
import math
import re
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
    "Figure4_example_focal.png":      ([f"{STY}/s4_examples_eeg_focal.png"], 1, "62, 63"),
    "Figure5_example_generalized.png": ([f"{STY}/s4_examples_eeg_generalized.png"], 1, "62, 63"),
    "Figure6_description_contrast.png": ([f"{STY}/s4_d2.png", f"{STY}/s4_d5.png"], 1, "57"),
    "Figure7_sleep_underreporting.png": ([f"{G}/v4a_wake_sleep.png"], 1, "fig6_sleep_naming (95b stat)"),
    # ---- SUPPLEMENTARY ----
    "FigureS1_architecture.png":     ([f"{STY}/architecture.png"], 1, "architecture_diagram"),
    "FigureS6_deviation_field.png":  ([f"{STY}/s2_segment_deviation.png"], 1, "44"),
    "FigureS5_curvebank.png":        ([f"{SC}/rel_delta__whole_head.png", f"{SC}/TAR__whole_head.png", f"{SC}/DAR__whole_head.png"], 1, "111"),
    "FigureS8_description_panels.png": ([f"{STY}/s4_d1.png", f"{STY}/s4_d3.png", f"{STY}/s4_d4.png", f"{STY}/s4_d6.png"], 1, "57, 58"),
    "FigureS7_localized_focal.png":  ([f"{STY}/s0_occasion_ours_v4_focal.png"], 1, "49"),
    "FigureS9_severity_null.png":    ([f"{G}/severity_recalibrated.png"], 1, "109"),
    "FigureS3_vanputten.png":        (["figures/figs/vanputten_panel_s7.png"], 1, "vanputten_panel_s7"),
    "FigureS4_topoplot_TAR.png":     ([f"{G}/topo_TAR_by_age_stage.png"], 1, "77"),
    "FigureS2_centile_calibration.png": ([f"{STY}/s9_centile_calibration.png"], 1, "78"),
}
COLW = 7.0                                                       # inches per panel column
PAGE_W = 7.0         # the journal prints a figure at this width whatever the composite measures
SHRINK_WARN = 0.70   # a source authored wider than page-width/SHRINK_WARN has its text shrunk below legibility

# Clinical Neurophysiology print box. A figure is scaled to fit BOTH limits, so a figure that is too TALL
# gets printed narrower than the column -- and its type shrinks with it. That is the failure the width-only
# guard below could not see: Figure 1 passed it while its 5.6 pt tick labels printed at ~4 pt, which is what
# review comment C103 ("Figure 1 illegible") was actually about. page_fit() checks the height limit too.
PAGE_MM = (190.0, 240.0)
MIN_PT = 6.0         # nothing may print smaller than this
MIN_DPI = 300.0      # ...and nothing may print coarser than this, ON THE PAGE


def native_inches(path: str) -> float | None:
    """Width in inches the panel was authored at (px / its own stored dpi). None if undeterminable."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            dpi = (im.info.get("dpi") or (None,))[0]
            return im.size[0] / dpi if dpi else None
    except Exception:
        return None


def page_width_per_panel(ncols: int) -> float:
    """Inches of PAGE width each panel gets once the journal scales the composite to a 7in column.

    The composite is COLW*ncols inches wide, but it is printed at 7in regardless, so a two-up figure gives
    each panel 3.5in of page -- not 7. Comparing against COLW alone under-reports exactly the multi-panel
    figures (Figure 5, Figure S8) whose text is smallest on the page.
    """
    return PAGE_W / ncols


def legibility(panels: list[str], ncols: int) -> list[str]:
    """Warn when compositing shrinks a panel enough to make its axis text unreadable in print.

    The composite gives every panel COLW inches of width. A panel authored at W inches therefore has all of
    its text scaled by COLW/W; an 18-inch-wide panel with 6.5 pt ticks lands at ~2.5 pt on the page. This is
    the mechanism behind the round-1 review comment that axis labels were illegible even at high
    magnification, so it is checked rather than left to the eye.
    """
    out = []
    for p in panels:
        w = native_inches(p)
        if w is None:
            continue
        target = page_width_per_panel(ncols)
        scale = target / w
        if scale < SHRINK_WARN:
            out.append(f"{Path(p).name}: authored {w:.1f}in wide -> {target:.1f}in of page "
                       f"({scale:.0%}; text renders at {scale:.0%} of its authored pt size)")
    return out



def page_fit(out_path: Path) -> tuple[float, float, float]:
    """(printed width mm, printed height mm, type scale) for a finished composite at the journal's box.

    Type scale is what every point size in the file is multiplied by on the printed page: 1.0 means the
    figure prints at the size it was authored, 0.7 means a 9 pt label lands at 6.3 pt."""
    from PIL import Image
    with Image.open(out_path) as im:
        dpi = (im.info.get("dpi") or (300,))[0] or 300
        w_mm, h_mm = im.size[0] / dpi * 25.4, im.size[1] / dpi * 25.4
    s = min(PAGE_MM[0] / w_mm, PAGE_MM[1] / h_mm)
    return w_mm * s, h_mm * s, s


def print_dpi(out_path: Path) -> float:
    """Pixels per inch the figure actually has once it is scaled onto the page."""
    from PIL import Image
    with Image.open(out_path) as im:
        dpi = (im.info.get("dpi") or (300,))[0] or 300
        w_in = im.size[0] / dpi
    return im.size[0] / (page_fit(out_path)[0] / 25.4) if w_in else float("nan")


def smallest_pt(panels: list[str]) -> float | None:
    """The smallest font size any producing script sets for these panels, read from the source.

    Crude on purpose -- a regex over `fontsize=`/`labelsize=` in the scripts that write these panels. It
    only has to be right about the SMALLEST value, which is the one that decides legibility."""
    pts = []
    for src in sorted(Path("scripts").glob("*.py")):
        text = src.read_text(errors="ignore")
        if not any(Path(p).name in text for p in panels):
            continue
        pts += [float(m) for m in re.findall(r"(?:fontsize|labelsize)\s*=\s*([0-9.]+)", text)]
    return min(pts) if pts else None


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
    # hspace was 0.03, which put each panel letter on top of the previous panel's x-axis labels (the "B"
    # of Figure 2 and Figure 6 sat in among the tick labels of panel A). The letter needs a line of its own.
    gs = fig.add_gridspec(nrows, ncols, height_ratios=row_h, hspace=0.115, wspace=0.03)
    for i, im in enumerate(imgs):
        r, c = divmod(i, ncols)
        ax = fig.add_subplot(gs[r, c]); ax.imshow(im); ax.axis("off")
        if n > 1:
            ax.text(0.0, 1.01, chr(65 + i), transform=ax.transAxes, fontsize=17, fontweight="bold",
                    va="bottom", ha="left")
    # Save at whatever pixel density leaves the PRINTED figure at >= MIN_DPI.
    #
    # This is the DPI trap, and it is the exact twin of the type-size one. A figure saved at 300 dpi carries
    # "300 dpi" in its metadata and every checker reads it back and passes it -- but the journal scales the
    # figure to fill the column, and scaling UP spreads the same pixels over more paper. At the page scales
    # this set uses (1.13-1.44) every figure was landing between 209 and 266 dpi on the page while claiming
    # 300. Measured, not assumed: see the effective-DPI column in MANIFEST.md.
    #
    # So: render once to learn the natural size, compute the page scale, then re-render at 300 x that scale.
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    scale = page_fit(out_path)[2]
    if scale > 1.0:
        fig.savefig(out_path, dpi=int(math.ceil(MIN_DPI * scale)), bbox_inches="tight", facecolor="white")
    fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")   # vector; dpi n/a
    plt.close(fig)
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in [*OUT.glob("*.png"), *OUT.glob("*.pdf")]:
        old.unlink()
    lines = ["# Manuscript figures — composited submission set", "",
             "Built by `scripts/assemble_manuscript_figures.py`: multi-panel figures are composited into one "
             "file with (A)/(B) labels (as submitted); singles are passed through. Regenerate panel sources via "
             "the `results` reproduce tier, then re-run.", "",
             "Printed size is what the figure measures once it is scaled to fit Clinical Neurophysiology's "
             f"{PAGE_MM[0]:.0f} x {PAGE_MM[1]:.0f} mm box; type scale is what every point size in it is "
             "multiplied by on the page. A figure that is too tall prints narrower than the column and "
             "shrinks its own labels, so both are reported here.", "",
             "| submission figure | panels | producing script(s) | printed mm | type scale | printed DPI |",
             "|---|---|---|---|---|---|"]
    have = miss = 0
    warnings: dict[str, list[str]] = {}
    toosmall: dict[str, tuple] = {}
    lowdpi: dict[str, float] = {}
    fit: list[tuple] = []
    for name, (panels, ncols, scripts) in FIGS.items():
        w = legibility(panels, ncols)
        if w:
            warnings[name] = w
        if compose(OUT / name, panels, ncols):
            have += 1
            pw, ph, sc = page_fit(OUT / name)
            edpi = print_dpi(OUT / name)
            spt = smallest_pt(panels)
            fit.append((name, pw, ph, sc, spt, edpi))
            if spt is not None and spt * sc < MIN_PT:
                toosmall[name] = (spt, sc, spt * sc, pw, ph)
            if edpi < MIN_DPI - 1:
                lowdpi[name] = edpi
            lines.append(f"| `{name}` | {len(panels)} ({', '.join(Path(p).name for p in panels)}) | "
                         f"`scripts/{scripts}` | {pw:.0f} x {ph:.0f} | {sc:.2f} | {edpi:.0f} |")
        else:
            miss += 1
            missing = [p for p in panels if not Path(p).exists()]
            lines.append(f"| `{name}` | *(missing: {', '.join(missing)})* | `scripts/{scripts}` | — | — | — |")
    (OUT / "MANIFEST.md").write_text("\n".join(lines) + "\n")
    print(f"composited {have} submission figures into {OUT}/ ({miss} with a missing source) + MANIFEST.md")
    if miss:
        for name, (panels, _, _) in FIGS.items():
            missing = [p for p in panels if not Path(p).exists()]
            if missing:
                print(f"    {name} <- missing {missing}")
    worst = min((f[3] for f in fit), default=1.0)
    worst_dpi = min((f[5] for f in fit), default=300.0)
    print(f"    page fit: worst type scale {worst:.2f}; worst printed DPI {worst_dpi:.0f}"
          + (f"; {len(toosmall)} figure(s) print type below {MIN_PT:.0f} pt" if toosmall
             else f"; every figure prints its smallest type at >= {MIN_PT:.0f} pt"))
    if lowdpi:
        print(f"\n!! {len(lowdpi)} figure(s) print below {MIN_DPI:.0f} DPI ON THE PAGE. The dpi stamped in the\n"
              f"   file is not the dpi on paper: a figure scaled UP to fill the column spreads the same\n"
              f"   pixels over more paper. Raise the save dpi in compose():")
        for name, e in lowdpi.items():
            print(f"    {name} <- {e:.0f} DPI printed")
    if toosmall:
        print(f"\n!! {len(toosmall)} figure(s) would print text below the {MIN_PT:.0f} pt floor. A figure "
              f"taller than ~{PAGE_MM[0]/PAGE_MM[1]:.2f}x its width is scaled DOWN to fit the page height, "
              f"which shrinks its type:")
        for name, (spt, sc, eff, pw, ph) in toosmall.items():
            print(f"    {name} <- smallest authored type {spt:g} pt x page scale {sc:.2f} = {eff:.1f} pt "
                  f"(prints {pw:.0f} x {ph:.0f} mm)")
        print("   Fix in the PRODUCING script: shorter/wider panels, or larger fontsize — not here.")
    if warnings:
        print(f"\n!! {len(warnings)} figure(s) shrink below {SHRINK_WARN:.0%} of authored width — "
              f"axis text will be hard to read in print:")
        for name, ws in warnings.items():
            for w in ws:
                print(f"    {name} <- {w}")
        print("   Fix in the PRODUCING script (narrower figsize or larger fontsize), not here.")


if __name__ == "__main__":
    main()
