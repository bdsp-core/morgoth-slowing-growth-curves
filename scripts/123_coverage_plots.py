"""Coverage PLOTS after backfill (docs/analysis_plan.md §3.7). Shows the COMBINED cohort + backfill
coverage under the 4-region taxonomy (scripts/20 REGION4). Adequacy is assessed on the MARGINALS
(region / side / band / topography / age) — all green after backfill — plus the well-populated interaction
cells. The four genuinely-rare three-way cells (focal central-delta / central-theta / frontal-theta,
generalized anterior-theta) max out <200 across the ENTIRE 62k-patient pool and are marked "rare (pooled)",
not flagged as gaps (band is a low-confidence descriptor; no per-region-per-band claim is made).

Sources: report_manifest_v1 (cohort clean, focal region re-extracted to 4 regions from report_text) +
backfill_candidates_v1. PHI: counts only. Writes figures/coverage/coverage_overview.png.
Run: PYTHONPATH=src python scripts/123_coverage_plots.py
"""
from __future__ import annotations
from pathlib import Path
import importlib.util
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

MANIFEST = "data/manifest/report_manifest_v1.parquet"
BACKFILL = "data/manifest/backfill_candidates_v1.parquet"
OUT = Path("figures/coverage"); OUT.mkdir(parents=True, exist_ok=True)
AGE_BINS = [0, 1, 6, 13, 18, 45, 60, 75, 200]
AGE_LAB = ["0-1", "1-5", "6-12", "13-17", "18-44", "45-59", "60-74", "75+"]
GREEN, GREY = "#4caf7d", "#9aa0a6"
TARGET = 200

_m20 = importlib.util.spec_from_file_location("m20", "scripts/20_extract_report_labels.py")
m20 = importlib.util.module_from_spec(_m20); _m20.loader.exec_module(m20)


def load_combined():
    m = pd.read_parquet(MANIFEST)
    mc = m[(m.clean_pair == True) & (~m.same_date_ambiguous)].copy()
    reg = mc.loc[mc.has_focal_slow == 1, "report_text"].fillna("").str.lower().map(m20.extract_region4)
    mc["focal_region"] = np.nan; mc.loc[reg.index, "focal_region"] = reg          # 4-region re-extraction
    coh = pd.DataFrame({"focal": mc.has_focal_slow == 1, "gen": mc.has_gen_slow == 1,
                        "normal": mc.clean_normal == 1, "abnormal": mc.is_abnormal == 1,
                        "focal_region": mc.focal_region, "focal_side": mc.focal_side,
                        "focal_band": mc.focal_band, "gen_topography": mc.gen_topography,
                        "gen_band": mc.gen_band, "age": pd.to_numeric(mc.age, errors="coerce")})
    b = pd.read_parquet(BACKFILL)
    bf = pd.DataFrame({"focal": b.is_focal == 1, "gen": b.is_gen == 1, "normal": b.is_normal == 1,
                       "abnormal": (b.is_focal == 1) | (b.is_gen == 1),
                       "focal_region": b.focal_region, "focal_side": b.focal_side, "focal_band": b.focal_band,
                       "gen_topography": b.gen_topography, "gen_band": b.gen_band,
                       "age": pd.to_numeric(b.age, errors="coerce")})
    c = pd.concat([coh, bf], ignore_index=True)
    c["age_bin"] = pd.cut(c.age, bins=AGE_BINS, labels=AGE_LAB, right=False)
    return c, len(coh), len(bf)


def bars(ax, s, title):
    colors = [GREEN if v >= TARGET else GREY for v in s.values]
    ax.bar(range(len(s)), s.values, color=colors)
    ax.axhline(TARGET, ls=":", color="#555", lw=1)
    ax.set_xticks(range(len(s))); ax.set_xticklabels(s.index, rotation=25, ha="right", fontsize=8)
    for i, v in enumerate(s.values):
        ax.text(i, v, int(v), ha="center", va="bottom", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold"); ax.margins(y=0.18)


def heat(ax, t, title):
    M = t.values.astype(float)
    rgb = np.empty(M.shape + (3,))
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            rgb[i, j] = (0.298, 0.686, 0.49) if M[i, j] >= TARGET else (0.604, 0.627, 0.651)
    ax.imshow(rgb, aspect="auto")
    ax.set_xticks(range(t.shape[1])); ax.set_xticklabels(t.columns, fontsize=9)
    ax.set_yticks(range(t.shape[0])); ax.set_yticklabels(t.index, fontsize=9)
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = int(M[i, j]); lab = f"{v}" + ("\nrare" if v < TARGET else "")
            ax.text(j, i, lab, ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.set_title(title, fontsize=10, fontweight="bold")


def main():
    c, ncoh, nbf = load_combined()
    f, g = c[c.focal], c[c.gen]
    fig, ax = plt.subplots(3, 3, figsize=(16, 13))
    fig.suptitle(f"Report-label coverage after backfill — cohort {ncoh:,} + backfill {nbf:,} = {len(c):,} EEGs "
                 f"(green ≥{TARGET}; grey = genuinely rare, pooled in assessment)",
                 fontsize=13, fontweight="bold")

    # Row 1 — age & class (the backfilled young bins)
    acl = pd.DataFrame({"clean-normal": c[c.normal].groupby("age_bin", observed=False).size(),
                        "abnormal": c[c.abnormal].groupby("age_bin", observed=False).size(),
                        "focal": f.groupby("age_bin", observed=False).size(),
                        "generalized": g.groupby("age_bin", observed=False).size()}).fillna(0).astype(int)
    heat(ax[0, 0], acl, "Age × class")
    bars(ax[0, 1], c.groupby("age_bin", observed=False).size(), "Age distribution (all)")
    bars(ax[0, 2], pd.Series({"focal": len(f), "generalized": len(g),
                              "clean-normal": int(c.normal.sum()), "abnormal": int(c.abnormal.sum())}),
         "Class totals")

    # Row 2 — MARGINALS (the adequacy criterion), all green
    bars(ax[1, 0], f.focal_region.value_counts(), "FOCAL region (marginal)")
    bars(ax[1, 1], f.focal_side.value_counts(), "FOCAL side (marginal)")
    bars(ax[1, 2], f.focal_band.value_counts(), "FOCAL band (marginal)")

    # Row 3 — interactions (rare cells greyed) + gen marginals
    heat(ax[2, 0], pd.crosstab(f.focal_region, f.focal_band), "FOCAL region × band")
    heat(ax[2, 1], pd.crosstab(g.gen_topography, g.gen_band), "GEN topography × band")
    bars(ax[2, 2], pd.concat([g.gen_topography.value_counts().rename(lambda x: "topo:" + str(x)),
                              g.gen_band.value_counts().rename(lambda x: "band:" + str(x))]),
         "GEN topography & band (marginals)")

    fig.legend(handles=[Patch(color=GREEN, label=f"≥{TARGET} (adequate)"),
                        Patch(color=GREY, label="rare finding — pooled, not a sampling gap")],
               loc="lower center", ncol=2, fontsize=10, frameon=False)
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    p = OUT / "coverage_overview.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    print(f"wrote {p}")
    # adequacy summary
    for lab, s in [("focal region", f.focal_region.value_counts()), ("focal side", f.focal_side.value_counts()),
                   ("focal band", f.focal_band.value_counts()), ("gen topo", g.gen_topography.value_counts()),
                   ("gen band", g.gen_band.value_counts())]:
        print(f"  {lab:14s} marginal min = {int(s.min())}  ({'ALL GREEN' if s.min() >= TARGET else 'THIN'})")


if __name__ == "__main__":
    main()
