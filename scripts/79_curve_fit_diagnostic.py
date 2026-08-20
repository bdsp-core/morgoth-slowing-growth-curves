#!/usr/bin/env python3
"""Does the fitted GAMLSS median actually track the data? Sweep the mu spline's degrees of freedom.

The manuscript claimed the fitted median "tracks closely across the lifespan" against a model-free rolling
median. Rebuilding Figure 1 at legible size showed that is false through the infant peak for the ratio
features. This measures the discrepancy instead of eyeballing it, and sweeps KEYSTONE_MU_DF to find the
smoothness that fixes infancy without destabilising the data-dense adult range.

Metric: |fitted p50 - rolling p50|, expressed as a fraction of that cell's own p25-p75 width, so features on
different scales are comparable. Reported over three age bands, since the whole point is that the fit can be
good in one and bad in another.

Writes results/story/curve_fit_diagnostic.md + figures/story/s10_curve_fit_diagnostic.png
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/79_curve_fit_diagnostic.py [--df 5,9,14,20]
"""
from __future__ import annotations
import argparse
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# scripts/76 reads sys.argv[1] as its feature list at import time, so hide our own flags from it.
_argv = sys.argv[:]
sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("m76", "scripts/76_keystone_growth_grid.py")
m76 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m76)
sys.argv = _argv

FIG = Path("figures/story")
RES = Path("results/story")
MIN_LOCAL = 50   # recordings within +-0.1 log-age required before a grid point counts
BANDS = [("infant (2mo-1y)", 2 / 12, 1.0), ("child (1-20y)", 1.0, 20.0), ("adult (>20y)", 20.0, 95.0)]


def discrepancy(c: pd.DataFrame, curves: pd.DataFrame, stage: str) -> dict[str, float]:
    """Median |fitted - rolling| / IQR within each age band, for one stage.

    MEDIAN, not max, and only at grid points with real data behind them. A spline evaluated past the edge of
    its data can take any value, and a max over the raw grid reports that edge artefact rather than the fit
    quality anyone can see in the figure.
    """
    sub = c[c.stage == stage]
    cv = curves[curves.group == stage].sort_values("t")
    if not len(cv) or not len(sub):
        return {}
    roll = m76.rolling_pctile(sub.t.values, sub.val.values, cv.t.values, 0.5)
    iqr = float(np.nanmedian(cv.p75.values - cv.p25.values)) or np.nan
    age = 10 ** cv.t.values - 1 / 12
    dense = np.array([(np.abs(sub.t.values - t0) < 0.1).sum() >= MIN_LOCAL for t0 in cv.t.values])
    out = {}
    for name, lo, hi in BANDS:
        m = (age >= lo) & (age < hi) & np.isfinite(roll) & dense
        out[name] = float(np.median(np.abs(cv.p50.values[m] - roll[m])) / iqr) if m.sum() else np.nan
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--df", default="5,9,14,20", help="comma-separated mu degrees of freedom to try")
    a = ap.parse_args()
    dfs = [d.strip() for d in a.df.split(",")]
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)

    df_all = pd.read_parquet(m76.TABLE)
    df_all = df_all[df_all.clean_normal == True]                                        # noqa: E712

    rows, fits = [], {}
    for mu_df in dfs:
        os.environ["KEYSTONE_MU_DF"] = mu_df
        for feat in m76.FEATURES:
            c, curves = m76.fit_feature(df_all, feat)
            fits[(mu_df, feat)] = (c, curves)
            for stage in m76.STAGES:
                d = discrepancy(c, curves, stage)
                if d:
                    rows.append(dict(mu_df=mu_df, feature=feat, stage=stage, **d))
        print(f"  mu_df={mu_df} done", flush=True)

    t = pd.DataFrame(rows)
    t.to_csv(RES / "curve_fit_diagnostic.csv", index=False)

    band_cols = [b[0] for b in BANDS]
    summ = t.groupby("mu_df")[band_cols].max().reindex(dfs)
    lines = ["# Does the fitted median track the data? (mu spline df sweep)", "",
             "Median |fitted median − rolling median| as a fraction of that cell's own p25–p75 width, "
             "over all feature × stage cells. Lower is better; >0.25 means the fitted median is off by more "
             "than a quarter of the interquartile range, which is visible in the figure.", "",
             "| mu df | " + " | ".join(band_cols) + " |", "|---|" + "---|" * len(band_cols)]
    for mu_df, r in summ.iterrows():
        lines.append(f"| {mu_df} | " + " | ".join(f"{r[b]:.2f}" for b in band_cols) + " |")
    lines += ["", "## Worst cells per mu df (infant band)", "",
              "| mu df | feature | stage | infant | child | adult |", "|---|---|---|---|---|---|"]
    for mu_df in dfs:
        w = t[t.mu_df == mu_df].nlargest(3, "infant (2mo-1y)")
        for _, r in w.iterrows():
            lines.append(f"| {mu_df} | {r.feature} | {r.stage} | {r['infant (2mo-1y)']:.2f} | "
                         f"{r['child (1-20y)']:.2f} | {r['adult (>20y)']:.2f} |")
    (RES / "curve_fit_diagnostic.md").write_text("\n".join(lines) + "\n")

    # --- figure: the worst cell at each mu df, fitted vs rolling ---
    worst = t.loc[t["infant (2mo-1y)"].idxmax()]
    feat, stage = worst.feature, worst.stage
    fig, axes = plt.subplots(1, len(dfs), figsize=(1.85 * len(dfs) + 0.6, 2.5), sharey=True, squeeze=False)
    for k, mu_df in enumerate(dfs):
        ax = axes[0][k]
        c, curves = fits[(mu_df, feat)]
        sub = c[c.stage == stage]
        cv = curves[curves.group == stage].sort_values("t")
        roll = m76.rolling_pctile(sub.t.values, sub.val.values, cv.t.values, 0.5)
        m = (10 ** cv.t.values - 1 / 12) <= 20
        ax.scatter(sub.t, sub.val, s=1.6, alpha=0.10, color="#333", edgecolors="none")
        ax.plot(cv.t.values[m], cv.p50.values[m], color=m76.YODA[stage], lw=1.9, label="GAMLSS median")
        ax.plot(cv.t.values[m], roll[m], color="k", lw=1.0, ls=(0, (3, 2)), label="rolling median")
        e = t[(t.mu_df == mu_df) & (t.feature == feat) & (t.stage == stage)]["infant (2mo-1y)"].iloc[0]
        ax.set_title(f"mu df = {mu_df}\ninfant gap {e:.2f} IQR", fontsize=7.5)
        ax.set_xlim(m76.A2T(1 / 12), m76.A2T(20))
        ax.set_xticks(m76.A2T(m76.DEV_TICKS))
        ax.set_xticklabels(m76.DEV_LABELS, rotation=45, ha="right", fontsize=6)
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.16, lw=0.4)
        ax.set_ylim(*np.nanpercentile(sub.val, [1, 99]))
        if k == 0:
            ax.set_ylabel(f"{feat} ({stage})", fontsize=7.5)
            ax.legend(fontsize=6, frameon=False, loc="upper right")
        ax.set_xlabel("age", fontsize=6.5)
    fig.suptitle(f"Infant-range fit of the mu spline — worst cell ({feat}, {stage})", fontsize=8.5)
    fig.tight_layout()
    out = FIG / "s10_curve_fit_diagnostic.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nworst cell overall: {feat} / {stage}")
    print(summ.to_string())
    print(f"wrote {out} and {RES/'curve_fit_diagnostic.md'}")


if __name__ == "__main__":
    main()
