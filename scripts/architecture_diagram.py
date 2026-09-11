"""Figure S1 — the pipeline architecture schematic.

One deviation-from-normal field is the shared substrate for BOTH detection (two report-trained heads) and
description (a claims-table-governed read-off). Self-contained: reads no data.

Layout note. The previous version centred each label at its box's midpoint and asked matplotlib to `wrap`.
matplotlib wraps to the FIGURE width, not to the artist's width, so every long label ran straight through
its own box and overprinted its neighbours -- the figure was unreadable in five places. Text is now wrapped
to the box width here, in this file, and each box GROWS to fit its wrapped text, so a label can never
overflow again no matter how it is edited.

Run: MPLBACKEND=Agg python3 scripts/architecture_diagram.py  ->  figures/story/architecture.png
"""
from __future__ import annotations
import textwrap
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (applies shared Tufte publication style)
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = Path("figures/story")

# Fills are pale and carry NO information -- they group rows for the eye only, and every box is also named.
# That keeps the figure readable in greyscale and under any colour-vision deficiency.
C_IN, C_HUB, C_DET, C_DESC, C_VAL = "#e8eef4", "#f2eee6", "#e3efe0", "#e9e4f2", "#f0f0f0"
EDGE, HUB_EDGE = "#5a6b7a", "#4a4a4a"   # not orange: that is LENS's colour in six figures

W_IN, H_IN = 7.1, 6.4                      # canvas inches
XMAX, YMAX = 12.0, 12.0                    # data units
X_PER_IN, Y_PER_IN = XMAX / W_IN, YMAX / H_IN


def _wrap(text, w_units, fs):
    """Wrap to the box width. Chars-per-unit from the actual canvas scale, not guessed."""
    chars = max(8, int(w_units / X_PER_IN * 72.0 / (0.55 * fs) * 0.94))
    out = []
    for para in text.split("\n"):
        out += textwrap.wrap(para, chars) or [""]
    return out


def box(ax, x, y_top, w, text, fc, fs=8.0, bold=False, ec=EDGE, pad=0.30):
    """Draw a box whose HEIGHT is derived from the wrapped text. Returns (y_bottom, y_centre)."""
    lines = _wrap(text, w, fs)
    lh = fs * 1.32 / 72.0 * Y_PER_IN                       # one line, in data units
    h = len(lines) * lh + 2 * pad
    y = y_top - h
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.010,rounding_size=0.012",
                                linewidth=1.0, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h / 2, "\n".join(lines), ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.32, zorder=3)
    return y, y + h / 2


def arrow(ax, x0, y0, x1, y1, lw=1.2, color="#444"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11,
                                 lw=lw, color=color, shrinkA=2, shrinkB=2, zorder=1))


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(W_IN, H_IN))
    ax.set_xlim(0, XMAX); ax.set_ylim(0, YMAX); ax.axis("off")

    # ---- ingest ---------------------------------------------------------------------------------
    top = 11.30
    b1, _ = box(ax, 0.20, top, 3.55, "Clinical EEG\n25,536 recordings · 21,757 patients", C_IN, 7.6)
    b2, _ = box(ax, 4.15, top, 3.70, "Sleep staging (Morgoth)\nW / N1 / N2 / N3 / REM per 15-s segment", C_IN, 7.6)
    b3, _ = box(ax, 8.25, top, 3.55, "Segment features\nband powers and ratios per region", C_IN, 7.6)
    ymid = (top + min(b1, b2, b3)) / 2
    arrow(ax, 3.75, ymid, 4.15, ymid); arrow(ax, 7.85, ymid, 8.25, ymid)

    # ---- the hub --------------------------------------------------------------------------------
    top2 = min(b1, b2, b3) - 0.75
    c_b, c_c = box(ax, 0.20, top2, 5.30,
                   "Lifespan × sleep-stage normative curves (GAMLSS)\nmedian and spread per age × stage × region × feature",
                   C_HUB, 7.8, bold=True)
    f_b, f_c = box(ax, 6.20, top2, 5.60,
                   "DEVIATION-FROM-NORMAL FIELD\nz per 15-s segment × region × feature — the shared substrate",
                   C_HUB, 7.8, bold=True, ec=HUB_EDGE)
    arrow(ax, 10.0, min(b1, b2, b3), 10.0, top2)
    arrow(ax, 5.50, c_c, 6.20, f_c)
    ax.text(5.85, c_c + 0.26, "score", fontsize=6.8, color="#666", ha="center")

    # ---- two consumers --------------------------------------------------------------------------
    top3 = min(c_b, f_b) - 0.75
    d_b, _ = box(ax, 0.20, top3, 5.30, "DETECTION — two heads, trained only on report labels", C_DET, 8.0, bold=True)
    s_b, _ = box(ax, 6.20, top3, 5.60, "DESCRIPTION — read off the field, governed by the claims table",
                 C_DESC, 8.0, bold=True)
    arrow(ax, 7.20, f_b, 2.85, top3)
    arrow(ax, 9.00, f_b, 9.00, top3)

    top4 = min(d_b, s_b) - 0.42
    g_b, _ = box(ax, 0.20, top4, 2.55, "Generalized head\ntop-k pooled whole-head amount z", C_DET, 7.2)
    fo_b, _ = box(ax, 2.95, top4, 2.55, "Focal head\npeak-region z, focality, L–R asymmetry, spatial stability",
                  C_DET, 7.2)
    de_b, _ = box(ax, 6.20, top4, 5.60,
                  "Structured descriptors: amount (SD / centile) · side · lobe · electrode · band "
                  "(low-confidence) · prevalence · persistence · sleep stage, with abstain rules enforced",
                  C_DESC, 7.2)
    arrow(ax, 1.47, top4 + 0.42, 1.47, top4); arrow(ax, 4.22, top4 + 0.42, 4.22, top4)
    arrow(ax, 9.00, top4 + 0.42, 9.00, top4)

    top5 = min(g_b, fo_b, de_b) - 0.42
    r_b, _ = box(ax, 0.20, top5, 5.30, "Recording focal + generalized slowing scores", C_DET, 7.8, bold=True)
    p_b, _ = box(ax, 6.20, top5, 5.60, "Generated finding line + report paragraph", C_DESC, 7.8, bold=True)
    arrow(ax, 1.47, top5 + 0.42, 2.30, top5); arrow(ax, 4.22, top5 + 0.42, 3.40, top5)
    arrow(ax, 9.00, top5 + 0.42, 9.00, top5)

    # ---- validation -----------------------------------------------------------------------------
    top6 = min(r_b, p_b) - 0.75
    v1_b, _ = box(ax, 0.20, top6,
                  5.30, "VALIDATION, held out\n• ON-100: 18 experts\n• the foundation-model gate\n"
                        "• the published qEEG indices\n• SAI-100: second site, SCORE-AI", C_VAL, 7.2)
    v2_b, _ = box(ax, 6.20, top6,
                  5.60, "VALIDATION, against clinical reports\n• dose-response contrasts\n"
                        "• component concordance (side, region, band)\n• sleep under-reporting, spindle-verified",
                  C_VAL, 7.2)
    arrow(ax, 2.85, top6 + 0.75, 2.85, top6); arrow(ax, 9.00, top6 + 0.75, 9.00, top6)

    ax.text(6, min(v1_b, v2_b) - 0.55,
            "One interpretable normative field → detection (report-trained, expert-validated)\n"
            "+ structured, claims-governed description.",
            ha="center", va="top", fontsize=8.0, style="italic", color="#333")

    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    fig.savefig(FIG / "architecture.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote figures/story/architecture.png")


if __name__ == "__main__":
    main()
