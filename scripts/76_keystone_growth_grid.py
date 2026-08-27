"""KEYSTONE FIGURE — normative growth curves of the most discriminating slowing features, per sleep stage.
Rows = sleep stages (W/N1/N2/N3/REM), columns = features (rel_delta, then the top normal-vs-abnormal
discriminators TAR & DAR). Every cell is a GAMLSS/LMS BCT percentile growth chart on central (C3/C4).

Built from the OVERNIGHT expansion only (one consistent extract.py pipeline) so all features/stages are
directly comparable — essential for a keystone (the routine .mat pipeline is not band-comparable for
ratio features; see memory: cohort/expansion harmonization). Sexes pooled (sex adds <=0.002 AUROC).

Run: PYTHONPATH=src python scripts/76_keystone_growth_grid.py [feat1,feat2,...]
"""
from __future__ import annotations
import os, sys, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (applies shared Tufte publication style)

FEATURES = (sys.argv[1].split(",") if len(sys.argv) > 1 else ["rel_delta", "TAR", "DAR"])
FEAT_LABEL = {"rel_delta": "Relative delta  (δ / total)", "TAR": "Theta/alpha ratio  (TAR)",
              "DAR": "Delta/alpha ratio  (DAR)", "log_delta": "log delta power", "low_freq_rel": "low-freq / total"}
FEAT_AUC = {"rel_delta": 0.72, "TAR": 0.82, "DAR": 0.79, "log_delta": 0.74, "low_freq_rel": 0.72}
TABLE = "data/derived/channel_stage_features.parquet"
# Review C100: the posterior dominant rhythm is read clinically from O1/O2 (at most P3/P4), not C3/C4, so
# the keystone is now built on the occipital derivations. REGION=central restores the original panel.
OCCIPITAL = ["P3-O1", "T5-O1", "P4-O2", "T6-O2"]
CENTRAL = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
REGION = os.environ.get("REGION", "occipital").lower()
CHANS = CENTRAL if REGION == "central" else OCCIPITAL
REGION_LABEL = "central (C3/C4)" if REGION == "central" else "occipital (O1/O2)"
STAGES = ["W", "N1", "N2", "N3", "REM"]
YODA = {"W": "#E8B800", "N1": "#5FB0D0", "N2": "#4488FF", "N3": "#00008B", "REM": "#A040A0"}
BANDS = [(3, 97), (10, 90), (25, 75)]
# Review C100: a single log10 age axis compresses all of adulthood into the last fifth of the panel, so the
# aging trend cannot be read. Each cell is therefore split: log-spaced development to SPLIT_AGE, then a
# LINEAR adult axis, drawn as two adjacent sub-axes sharing a y-scale.
SPLIT_AGE = 20.0
DEV_TICKS = [1/12, 6/12, 2, 5, 10, 20]
DEV_LABELS = ["1mo", "6mo", "2", "5", "10", "20"]
ADULT_TICKS = [30, 40, 50, 60, 70, 80, 90]
ADULT_LABELS = ["30", "40", "50", "60", "70", "80", "90"]
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
    """region-mean per-(recording,stage) for one feature -> GAMLSS curves per stage."""
    c = df[df.region.isin(CHANS)].groupby(["bdsp_id", "stage"]).agg(
        val=(feat, "mean"),
        # PUBLISHED artefact -> HIPAA Safe Harbor: ages >89 are binned to 90+ (the de-identified
        # OMOP does NOT do this for us; it returns ages up to 121). age_pub is the only age that
        # may appear in a figure. The normative FIT still uses the exact age.
        age=("age_pub", "first")).reset_index()
    c = c[c.age.between(0, 95) & np.isfinite(c.val)]
    lo, hi = c.val.quantile([0.002, 0.998])            # trim extreme ratio outliers (BCT needs positive)
    c = c[(c.val > max(lo, 1e-6)) & (c.val < hi)]
    c["t"] = A2T(c.age)
    # mu df: "smooth" (=5) was too stiff for the now-exact fractional ages, which resolve a sharp early-life
    # peak (1 mo-1 yr) that a 5-df spline over the whole log-age span cannot bend through. gamlss_fit.R takes
    # a numeric df; ~9 gives the infant region enough local flexibility while the log-age axis + lower-df
    # sigma keep the data-dense adult range stable. Override with KEYSTONE_MU_DF. Raised 9 -> 20 after the round-1 review: at df=9 the fitted median
    # undershot the model-free rolling median through the infant peak of the ratio features (worst cell DAR/W,
    # median gap 0.97 IQR over 2mo-1y); df=20 brings that to 0.24 IQR. See scripts/79.
    mu_df = os.environ.get("KEYSTONE_MU_DF", "20")
    with tempfile.TemporaryDirectory() as td:
        inp, outp = f"{td}/in.csv", f"{td}/out.csv"
        c[["stage", "t", "val"]].to_csv(inp, index=False)
        subprocess.run(["Rscript", "scripts/gamlss_fit.R", inp, outp, mu_df], capture_output=True, text=True)
        curves = pd.read_csv(outp)
    return c, curves


def main():
    df = pd.read_parquet(TABLE)
    # UNION of both report-normal cohorts. Valid once BOTH cohorts are on the identical extract.py+Morgoth
    # pipeline (the cohort recompute) — the union is the broad, conservative clinical-normal.
    df = df[df.clean_normal == True]
    ncol = len(FEATURES); nrow = len(STAGES)

    # Sized for the page, not for the screen: the composite gives each figure 7in of width, so authoring
    # wider than that shrinks every label below legibility (review C103). Kept at 7.1in.
    # Height budget is set by the PAGE, not by the screen. Figure 1 is this grid stacked over the
    # topography panel, and a journal prints the composite inside 190 x 240 mm. A composite taller than
    # ~1.4x its width has to be scaled DOWN to fit the page height, which shrinks every label with it: at
    # the old 1.42 in/row plus a 4-line in-figure title the 5.6 pt ticks printed at ~4 pt, which is what
    # review comment C103 ("Figure 1 illegible") was actually about -- re-exporting at 300 dpi raised the
    # resolution but not the printed point size. Shorter rows + the title moved to the caption (where CN
    # wants it anyway) keep the composite under that limit, so nothing prints below 6 pt.
    fig = plt.figure(figsize=(7.1, 1.22 * nrow + 0.42))
    # two sub-columns per feature: log-age development | linear-age adulthood
    gs = fig.add_gridspec(nrow, 2 * ncol, width_ratios=[1.35, 1.0] * ncol,
                          hspace=0.16, wspace=0.06, left=0.135, right=0.995, top=0.935, bottom=0.115)
    tsplit = A2T(SPLIT_AGE)

    for cj, feat in enumerate(FEATURES):
        c, curves = fit_feature(df, feat)
        ylo, yhi = c.val.quantile([0.01, 0.99])                  # shared y across stages within a feature
        for ri, stage in enumerate(STAGES):
            col = YODA[stage]
            sub = c[c.stage == stage]
            cv = curves[curves.group == stage].sort_values("t")
            emp = rolling_pctile(sub.t.values, sub.val.values, cv.t.values, 0.5) if len(cv) else None
            axes_pair = []
            for k in (0, 1):                                     # 0 = development (log), 1 = adult (linear)
                ax = fig.add_subplot(gs[ri, 2 * cj + k])
                axes_pair.append(ax)
                dev = k == 0
                # x transform: log-age on the left panel, raw years on the right
                def X(t_arr):
                    a = 10 ** np.asarray(t_arr, float) - 1 / 12
                    return A2T(a) if dev else a
                m_s = (sub.age <= SPLIT_AGE) if dev else (sub.age > SPLIT_AGE)
                ax.scatter(X(sub.t[m_s]), sub.val[m_s], s=1.6, alpha=0.10, color="#333",
                           edgecolors="none", zorder=1)
                if len(cv):
                    age_c = 10 ** cv.t.values - 1 / 12
                    m_c = (age_c <= SPLIT_AGE) if dev else (age_c > SPLIT_AGE)
                    xc = X(cv.t.values)[m_c]
                    for a, b in BANDS:
                        ax.fill_between(xc, cv[f"p{a}"].values[m_c], cv[f"p{b}"].values[m_c],
                                        color=col, alpha=0.20, lw=0, zorder=2)
                    ax.plot(xc, cv.p50.values[m_c], color=col, lw=1.6, zorder=3)
                    if emp is not None:
                        ax.plot(xc, emp[m_c], color="k", lw=0.8, ls=(0, (3, 2)), alpha=0.7, zorder=4)
                ax.set_ylim(ylo, yhi)
                ax.grid(alpha=0.16, lw=0.4)
                ax.tick_params(labelsize=6.6, length=2, pad=1.5)
                if dev:
                    ax.set_xlim(A2T(1 / 12), tsplit)
                    ax.set_xticks(A2T(DEV_TICKS))
                    ax.set_xticklabels(DEV_LABELS if ri == nrow - 1 else [], rotation=45, ha="right")
                    ax.spines["right"].set_visible(False)
                else:
                    ax.set_xlim(SPLIT_AGE, 95)
                    ax.set_xticks(ADULT_TICKS)
                    ax.set_xticklabels(ADULT_LABELS if ri == nrow - 1 else [], rotation=45, ha="right")
                    ax.spines["left"].set_linestyle((0, (2, 2)))
                    ax.tick_params(labelleft=False)
                # y ticks on the LEFT panel of every feature: the three features are on different scales,
                # so hiding all but the first column leaves two thirds of the grid without a readable axis.
                if k == 0:
                    if cj == 0:
                        ax.set_ylabel(stage, fontsize=9, fontweight="bold", rotation=0,
                                      ha="right", va="center", labelpad=26)
                else:
                    ax.tick_params(labelleft=False)
            if ri == 0:
                axes_pair[0].set_title(f"{FEAT_LABEL.get(feat, feat)}\nAUROC ≈ {FEAT_AUC.get(feat, 0):.2f}",
                                       fontsize=8, fontweight="bold", loc="left", pad=4)
            if ri == nrow - 1:
                axes_pair[0].set_xlabel("age (log)", fontsize=7, labelpad=1)
                axes_pair[1].set_xlabel("age (linear)", fontsize=7, labelpad=1)

    # No in-figure title: what it used to say (region, sex pooling, BCT fit, the dashed model-free median,
    # the three percentile bands, the log/linear age split) now lives in the Figure 1 caption in
    # docs/manuscript_draft.md, which is where Clinical Neurophysiology wants it and where it costs no
    # printed height. Keep the two in sync when either changes.
    out = Path("figures/growth_v2/keystone_growth_grid.png"); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight"); plt.close(fig)
    print("wrote", out, f"[region={REGION}]")


if __name__ == "__main__":
    main()
