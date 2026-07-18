"""Supplementary Figure — model / pipeline architecture schematic.

One deviation-from-normal field is the shared substrate for BOTH detection (two report-trained heads) and
description (claims-table-governed read-out). Rendered as a block diagram; self-contained (no data reads).

Run: MPLBACKEND=Agg python3 scripts/architecture_diagram.py  ->  figures/story/architecture.png
"""
from __future__ import annotations
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = Path("figures/story")
C_IN, C_HUB, C_DET, C_DESC, C_VAL = "#dfe7ef", "#f6d9b8", "#d8e8d5", "#e2dcec", "#eeeeee"
EDGE = "#5a6b7a"


def box(ax, x, y, w, h, text, fc, fs=8.5, bold=False, ec=EDGE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.010,rounding_size=0.014",
                                linewidth=1.1, edgecolor=ec, facecolor=fc))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x0, y0, x1, y1, style="-|>", lw=1.4, color="#333", ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=13,
                                 lw=lw, color=color, linestyle=ls, shrinkA=1, shrinkB=1))


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.5, 9.2)); ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.axis("off")

    # ---- ingest (top) ----
    box(ax, 0.5, 11.0, 3.3, 0.8, "Clinical EEG (EDF)\n25,536 recordings · 21,757 patients", C_IN, 8)
    box(ax, 4.3, 11.0, 3.5, 0.8, "Morgoth sleep staging (ss_hm_1)\nW / N1 / N2 / N3 / REM per 15-s segment", C_IN, 8)
    box(ax, 8.3, 11.0, 3.2, 0.8, "Segment features\nper region × band (δ/θ/α power, DAR, TAR, rel-power)", C_IN, 7.6)
    arrow(ax, 3.8, 11.4, 4.3, 11.4); arrow(ax, 7.8, 11.4, 8.3, 11.4)

    # ---- normative curves + deviation field (hub) ----
    box(ax, 1.2, 9.3, 4.6, 1.0, "Lifespan × sleep-stage normative growth curves (GAMLSS)\nμ, σ per (age × stage × region × feature)", C_HUB, 8.5, bold=True)
    box(ax, 6.4, 9.3, 4.4, 1.0, "DEVIATION-FROM-NORMAL FIELD\nz per 15-s segment × region × feature\n(the shared substrate)", C_HUB, 8.5, bold=True, ec="#b06a1a")
    arrow(ax, 9.9, 11.0, 8.6, 10.3)                      # features -> curves/field
    arrow(ax, 5.8, 9.8, 6.4, 9.8)                        # curves -> field
    ax.text(6.1, 9.95, "score", fontsize=7, color="#666", ha="center")

    # ---- two branches ----
    box(ax, 0.5, 7.4, 5.2, 0.55, "DETECTION  —  two heads, trained ONLY on report labels", C_DET, 9, bold=True)
    box(ax, 6.6, 7.4, 5.0, 0.55, "DESCRIPTION  —  read-off, governed by the claims table", C_DESC, 9, bold=True)
    arrow(ax, 7.6, 9.3, 3.1, 8.0)                        # field -> detection
    arrow(ax, 9.4, 9.3, 9.1, 8.0)                        # field -> description

    # detection heads
    box(ax, 0.5, 6.1, 2.5, 1.1, "Generalized head\ntop-5 pooled whole-head\namount z (diffuse)", C_DET, 7.8)
    box(ax, 3.2, 6.1, 2.5, 1.1, "Focal head\nrecording-level: peak-region z,\nfocality, L–R asymmetry,\nspatial stability · de-confounded", C_DET, 7.0)
    arrow(ax, 1.7, 7.4, 1.7, 7.2); arrow(ax, 4.4, 7.4, 4.4, 7.2)
    box(ax, 1.0, 5.0, 4.2, 0.7, "Recording focal + generalized slowing scores", C_DET, 8.2, bold=True)
    arrow(ax, 1.7, 6.1, 2.6, 5.7); arrow(ax, 4.4, 6.1, 3.6, 5.7)

    # description read-out
    box(ax, 6.6, 5.7, 5.0, 1.5,
        "Structured descriptors →\n• amount (SD / centile)   • side · lobe\n• electrode (L–R asymmetry)   • band (calibrated z_θ−z_δ)\n"
        "• prevalence · persistence   • sleep stage\n(low-confidence / abstain rules enforced)", C_DESC, 7.4)
    arrow(ax, 9.1, 7.4, 9.1, 7.2)
    box(ax, 7.0, 5.0, 4.2, 0.6, "Generated finding line + report paragraph", C_DESC, 8.2, bold=True)
    arrow(ax, 9.1, 5.7, 9.1, 5.6)

    # ---- validation (bottom) ----
    box(ax, 0.6, 3.0, 5.1, 1.4,
        "VALIDATION (held out)\n• 18-expert OccasionNoise panel — % experts under ROC\n• Morgoth foundation-model gate\n"
        "• van Putten qEEG indices\n• external Sandor_100 (second site, SCORE-AI)", C_VAL, 7.6, bold=False)
    box(ax, 6.6, 3.0, 5.0, 1.4,
        "VALIDATION (vs clinical reports)\n• dose-response contrasts (D1–D5)\n• component concordance (side, region, band)\n"
        "• band at expert-vs-expert floor (κ≈0.09)\n• sleep-slowing under-reporting (spindle-verified)", C_VAL, 7.6)
    arrow(ax, 3.1, 5.0, 3.1, 4.4); arrow(ax, 9.1, 5.0, 9.1, 4.4)

    ax.text(6, 1.9, "One interpretable normative field → detection (report-trained, expert-validated) + "
                    "structured, claims-governed description.", ha="center", fontsize=8.5, style="italic", color="#333")
    ax.text(6, 11.9, "Pipeline architecture — lifespan/sleep-stage deviation-from-normal EEG slowing",
            ha="center", fontsize=11.5, fontweight="bold")

    fig.tight_layout(); fig.savefig(FIG / "architecture.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote figures/story/architecture.png")


if __name__ == "__main__":
    main()
