"""Coverage PLOTS demonstrating that every domain of interest has an acceptable sample (report labels),
for the manifest freeze review (docs/analysis_plan.md §3.7). Companion to scripts/122 (tables).

Domains: age × class; focal side × band; focal region × band; focal region × side; generalized
topography × band; age × focal-side; age × generalized-topography. Cells are annotated with counts and
colored by adequacy (green ≥ ADEQUATE, amber ≥ THIN, red < THIN). Uses the CLEAN usable set.

Writes figures/coverage/coverage_overview.png (+ per-panel PNGs). PHI-free (counts only).
Run: PYTHONPATH=src python scripts/123_coverage_plots.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

MANIFEST = "data/manifest/report_manifest_v1.parquet"
OUT = Path("figures/coverage"); OUT.mkdir(parents=True, exist_ok=True)
AGE_BINS = [0, 1, 6, 13, 18, 45, 60, 75, 200]
AGE_LAB = ["0-1", "1-5", "6-12", "13-17", "18-44", "45-59", "60-74", "75+"]
THIN, ADEQUATE = 50, 200            # <THIN red, THIN-ADEQUATE amber, >=ADEQUATE green
CMAP = ListedColormap(["#d43d51", "#e6a23c", "#4caf7d"])
NORM = BoundaryNorm([0, THIN, ADEQUATE, 1e9], CMAP.N)


def heat(ax, t, title):
    """Adequacy heatmap: color by count band, annotate raw counts."""
    M = t.values.astype(float)
    ax.imshow(M, cmap=CMAP, norm=NORM, aspect="auto")
    ax.set_xticks(range(t.shape[1])); ax.set_xticklabels(t.columns, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(t.shape[0])); ax.set_yticklabels(t.index, fontsize=8)
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = int(M[i, j])
            ax.text(j, i, v, ha="center", va="center", fontsize=8,
                    color="white" if v < THIN else "#222", fontweight="bold" if v < THIN else "normal")
    ax.set_title(title, fontsize=10, fontweight="bold")


def bars(ax, s, title, thin=THIN):
    colors = ["#d43d51" if v < thin else "#e6a23c" if v < ADEQUATE else "#4caf7d" for v in s.values]
    ax.bar(range(len(s)), s.values, color=colors)
    ax.set_xticks(range(len(s))); ax.set_xticklabels(s.index, rotation=30, ha="right", fontsize=8)
    for i, v in enumerate(s.values):
        ax.text(i, v, int(v), ha="center", va="bottom", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold"); ax.margins(y=0.15)


def main():
    m = pd.read_parquet(MANIFEST)
    c = m[(m.clean_pair == True) & (~m.same_date_ambiguous)].copy()
    c["age_bin"] = pd.cut(pd.to_numeric(c.age, errors="coerce"), bins=AGE_BINS, labels=AGE_LAB, right=False)
    foc, gen = c[c.has_focal_slow == 1], c[c.has_gen_slow == 1]

    fig, ax = plt.subplots(3, 3, figsize=(16, 13))
    fig.suptitle(f"Report-label coverage across domains of interest  —  clean usable set n={len(c):,}  "
                 f"(green ≥{ADEQUATE}, amber ≥{THIN}, red <{THIN})", fontsize=13, fontweight="bold")

    # age × class
    acl = pd.DataFrame({"clean-normal": c[c.clean_normal == 1].groupby("age_bin", observed=False).size(),
                        "abnormal": c[c.is_abnormal == 1].groupby("age_bin", observed=False).size(),
                        "focal": foc.groupby("age_bin", observed=False).size(),
                        "generalized": gen.groupby("age_bin", observed=False).size()}).fillna(0)
    heat(ax[0, 0], acl, "Age × class")
    bars(ax[0, 1], c.groupby("age_bin", observed=False).size(), "Age distribution (all EEGs)")
    bars(ax[0, 2], pd.Series({"focal": len(foc), "generalized": len(gen),
                              "clean-normal": int((c.clean_normal == 1).sum()),
                              "abnormal": int((c.is_abnormal == 1).sum())}), "Class totals")

    heat(ax[1, 0], pd.crosstab(foc.focal_side, foc.focal_band), "FOCAL: side × band")
    heat(ax[1, 1], pd.crosstab(foc.focal_region, foc.focal_band), "FOCAL: region × band")
    heat(ax[1, 2], pd.crosstab(foc.focal_region, foc.focal_side), "FOCAL: region × side")

    heat(ax[2, 0], pd.crosstab(gen.gen_topography, gen.gen_band), "GENERALIZED: topography × band")
    heat(ax[2, 1], pd.crosstab(foc.age_bin, foc.focal_side), "FOCAL: age × side")
    heat(ax[2, 2], pd.crosstab(gen.age_bin, gen.gen_topography), "GENERALIZED: age × topography")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    p = OUT / "coverage_overview.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    print(f"wrote {p}")

    # a compact adequacy summary: how many cells are adequate / thin / empty per crosstab
    summary = []
    for name, t in [("focal side×band", pd.crosstab(foc.focal_side, foc.focal_band)),
                    ("focal region×band", pd.crosstab(foc.focal_region, foc.focal_band)),
                    ("focal region×side", pd.crosstab(foc.focal_region, foc.focal_side)),
                    ("gen topo×band", pd.crosstab(gen.gen_topography, gen.gen_band))]:
        v = t.values.flatten()
        summary.append({"crosstab": name, "cells": v.size, "≥%d" % ADEQUATE: int((v >= ADEQUATE).sum()),
                        "%d-%d" % (THIN, ADEQUATE): int(((v >= THIN) & (v < ADEQUATE)).sum()),
                        "<%d" % THIN: int((v < THIN).sum())})
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
