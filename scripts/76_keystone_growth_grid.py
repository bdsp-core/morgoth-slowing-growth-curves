"""KEYSTONE FIGURE — normative growth curves of the most discriminating slowing features, per sleep stage.
Rows = sleep stages (W/N1/N2/N3/REM), columns = features (rel_delta, then the top normal-vs-abnormal
discriminators TAR & DAR). Every cell is a GAMLSS/LMS BCT percentile growth chart on central (C3/C4).

Built from the OVERNIGHT expansion only (one consistent extract.py pipeline) so all features/stages are
directly comparable — essential for a keystone (the routine .mat pipeline is not band-comparable for
ratio features; see memory: cohort/expansion harmonization). Sexes pooled (sex adds <=0.002 AUROC).

Run: PYTHONPATH=src python scripts/76_keystone_growth_grid.py [feat1,feat2,...]
"""
from __future__ import annotations
import sys, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATURES = (sys.argv[1].split(",") if len(sys.argv) > 1 else ["rel_delta", "TAR", "DAR"])
FEAT_LABEL = {"rel_delta": "Relative delta  (δ / total)", "TAR": "Theta/alpha ratio  (TAR)",
              "DAR": "Delta/alpha ratio  (DAR)", "log_delta": "log delta power", "low_freq_rel": "low-freq / total"}
FEAT_AUC = {"rel_delta": 0.72, "TAR": 0.82, "DAR": 0.79, "log_delta": 0.74, "low_freq_rel": 0.72}
TABLE = "data/derived/channel_stage_features.parquet"
CENTRAL = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
YODA = {"W": "#E8B800", "N1": "#5FB0D0", "N2": "#4488FF", "N3": "#00008B", "REM": "#A040A0"}
BANDS = [(3, 97), (10, 90), (25, 75)]
TICK_AGES = [0, 1/12, 3/12, 6/12, 1, 2, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80]
TICK_LABELS = ["0", "1mo", "3mo", "6mo", "1", "2", "5", "10", "15", "20", "30", "40", "50", "60", "70", "80"]
def A2T(age): return np.log10(np.asarray(age, float) + 1/12)


def rolling_pctile(t_data, v_data, t_grid, q=0.5, h=0.11):
    t_data, v_data = np.asarray(t_data), np.asarray(v_data)
    out = np.full(len(t_grid), np.nan)
    for i, t0 in enumerate(t_grid):
        w = np.exp(-0.5 * ((t_data - t0) / h) ** 2)
        if w.sum() < 8: continue
        idx = np.argsort(v_data); vs, ws = v_data[idx], w[idx]
        cw = (np.cumsum(ws) - 0.5 * ws) / ws.sum()
        out[i] = np.interp(q, cw, vs)
    return out


def fit_feature(df, feat):
    """central per-(recording,stage) for one feature, overnight only -> GAMLSS curves per stage."""
    c = df[df.region.isin(CENTRAL)].groupby(["bdsp_id", "stage"]).agg(
        val=(feat, "mean"), age=("age", "first")).reset_index()
    c = c[c.age.between(0, 95) & np.isfinite(c.val)]
    lo, hi = c.val.quantile([0.002, 0.998])            # trim extreme ratio outliers (BCT needs positive)
    c = c[(c.val > max(lo, 1e-6)) & (c.val < hi)]
    c["t"] = A2T(c.age)
    with tempfile.TemporaryDirectory() as td:
        inp, outp = f"{td}/in.csv", f"{td}/out.csv"
        c[["stage", "t", "val"]].to_csv(inp, index=False)
        subprocess.run(["Rscript", "scripts/gamlss_fit.R", inp, outp, "smooth"], capture_output=True, text=True)
        curves = pd.read_csv(outp)
    return c, curves


def main():
    df = pd.read_parquet(TABLE)
    # UNION of both report-normal cohorts. Valid once BOTH cohorts are on the identical extract.py+Morgoth
    # pipeline (the cohort recompute) — before that, use src=="expansion" only. The union is the broad,
    # conservative clinical-normal (scripts/79 showed it costs no detection power).
    df = df[df.clean_normal == True]
    nfig, nrow, ncol = len(FEATURES), len(STAGES), len(FEATURES)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 2.5 * nrow), squeeze=False)
    tg = A2T(np.logspace(np.log10(1/12), np.log10(90), 160))

    for cj, feat in enumerate(FEATURES):
        c, curves = fit_feature(df, feat)
        ylo, yhi = c.val.quantile([0.01, 0.99])                      # shared y across stages within a feature
        for ri, stage in enumerate(STAGES):
            ax = axes[ri][cj]; col = YODA[stage]
            sub = c[c.stage == stage]
            ax.scatter(sub.t, sub.val, s=3, alpha=0.12, color="#333", edgecolors="none", zorder=1)
            cv = curves[curves.group == stage].sort_values("t")
            if len(cv):
                for a, b in BANDS:
                    ax.fill_between(cv.t, cv[f"p{a}"], cv[f"p{b}"], color=col, alpha=0.20, lw=0, zorder=2)
                ax.plot(cv.t, cv.p50, color=col, lw=2.3, zorder=3)
                emp = rolling_pctile(sub.t.values, sub.val.values, cv.t.values, 0.5)
                ax.plot(cv.t, emp, color="k", lw=1.0, ls=(0, (4, 2)), alpha=0.7, zorder=4)
            ax.set_ylim(ylo, yhi); ax.grid(alpha=0.18)
            ax.set_xticks(A2T(TICK_AGES))
            ax.set_xticklabels(TICK_LABELS if ri == nrow - 1 else [], fontsize=6.5, rotation=45, ha="right")
            if cj == 0:
                ax.set_ylabel(stage, fontsize=13, fontweight="bold", rotation=0, ha="right", va="center", labelpad=14)
            ax.tick_params(labelsize=7)
            if ri == 0:
                ax.set_title(f"{FEAT_LABEL.get(feat, feat)}\nnormal-vs-abnormal AUROC ≈ {FEAT_AUC.get(feat,0):.2f}",
                             fontsize=11, fontweight="bold")
            if ri == nrow - 1:
                ax.set_xlabel("age (years, log-scaled)", fontsize=8)

    fig.suptitle("Normative EEG-slowing growth curves across the lifespan, by sleep stage & feature\n"
                 "central (C3/C4), overnight EEG, sexes pooled; GAMLSS/LMS BCT — solid median, dashed = "
                 "model-free rolling median, bands p3–p97/p10–p90/p25–p75  (n≈15k/stage)", fontsize=12)
    fig.tight_layout(rect=[0.01, 0, 1, 0.96])
    out = Path("figures/growth_v2/keystone_growth_grid.png"); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
