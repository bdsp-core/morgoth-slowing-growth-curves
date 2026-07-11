"""Normative growth curves — CENTRAL (C3/C4), per sleep stage, SEXES POOLED — fit with GAMLSS/LMS (the
clinical growth-chart method: scripts/gamlss_fit.R fits BCCG with smooth mu/sigma). Sex was shown to add
nothing to detection (dAUC <=0.002, scripts/74), so one curve per stage over all recordings.

- Region = mean of the 4 chains touching C3/C4; sleep-yoda stage colors; OMOP fractional age, log axis.
- Panels: one per stage (points + p3-97/p10-90/p25-75 bands + median) plus an all-stage median overlay.
Run: PYTHONPATH=src python scripts/67_central_stage_growth.py [feature] [method]
"""
from __future__ import annotations
import sys, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATURE = sys.argv[1] if len(sys.argv) > 1 else "rel_delta"
METHOD = sys.argv[2] if len(sys.argv) > 2 else "smooth"
SOURCE = sys.argv[3] if len(sys.argv) > 3 else "auto"   # auto | pooled | cohort | expansion
TABLE = "data/derived/channel_stage_features.parquet"
CENTRAL = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
# Source policy per stage (harmonization): routine cohort EEG is the reference for WAKE (alert wake), but
# its sleep segments are rare/mis-staged, so overnight expansion is the reference for real sleep stages.
# "auto" applies this; "pooled" uses both (shows the bimodality); cohort/expansion force one source.
STAGE_SRC = {"W": "cohort", "N1": "cohort", "N2": "expansion", "N3": "expansion", "REM": "expansion"}
YODA = {"W": "#FFD700", "N1": "#ADD8E6", "N2": "#4488FF", "N3": "#00008B", "REM": "#A040A0"}
BANDS = [(3, 97), (10, 90), (25, 75)]
TICK_AGES = [0, 1/12, 3/12, 6/12, 1, 2, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80]
TICK_LABELS = ["0", "1mo", "3mo", "6mo", "1", "2", "5", "10", "15", "20", "30", "40", "50", "60", "70", "80"]
def A2T(age): return np.log10(np.asarray(age, float) + 1/12)


def rolling_pctile(t_data, v_data, t_grid, q, h=0.11):
    """Empirical q-quantile in a SLIDING window that widens with age: a Gaussian kernel of half-width h
    in log10-age space (so a fixed ~±h in log-age = a geometrically wider window in linear years for
    older ages). Returns the weighted quantile at each grid point — the model-free reference the fitted
    LMS curve should track."""
    t_data, v_data = np.asarray(t_data), np.asarray(v_data)
    out = np.full(len(t_grid), np.nan)
    for i, t0 in enumerate(t_grid):
        w = np.exp(-0.5 * ((t_data - t0) / h) ** 2)
        if w.sum() < 5:
            continue
        idx = np.argsort(v_data); vs, ws = v_data[idx], w[idx]
        cw = (np.cumsum(ws) - 0.5 * ws) / ws.sum()
        out[i] = np.interp(q, cw, vs)
    return out


def main():
    df = pd.read_parquet(TABLE)
    # Restrict to CLEAN NORMAL recordings only. The uniform table's `label` column is a placeholder
    # ('normal' for all); the authoritative re-derived labels live in labels_unified. Cohort recordings
    # that are not clean_normal (abnormal / focal-or-pathologic-generalized slowing) must be excluded so
    # the norm is not contaminated. Expansion recordings have no report label (NaN) and were selected as
    # normal overnight EEGs by the fleet manifest, so they are kept.
    if "clean_normal" not in df.columns:      # older table without labels attached -> join them
        lu = pd.read_parquet("data/derived/labels_unified.parquet")[["bdsp_id", "clean_normal"]]
        df = df.merge(lu, on="bdsp_id", how="left")
        df["clean_normal"] = df.clean_normal.fillna(True)
    keep = df[df.clean_normal == True]
    c = keep[keep.region.isin(CENTRAL)].groupby(["bdsp_id", "stage"]).agg(
        val=(FEATURE, "mean"), age=("age", "first"), src=("src", "first")).reset_index()
    hi = 1.0 if FEATURE.startswith("rel") else 1e9
    c = c[c.age.between(0, 100) & c.val.between(0, hi)]
    # apply the source policy so mis-calibrated sources are not pooled within a stage
    if SOURCE == "cohort": c = c[c.src == "cohort"]
    elif SOURCE == "expansion": c = c[c.src == "expansion"]
    elif SOURCE == "auto": c = c[c.apply(lambda r: r.src == STAGE_SRC.get(r.stage, "expansion"), axis=1)]
    c["t"] = A2T(c.age)
    print(f"central per-(recording,stage): {len(c)} rows, {c.bdsp_id.nunique()} clean-normal recordings "
          f"[source={SOURCE}], sexes pooled | by src: {c.groupby('src').bdsp_id.nunique().to_dict()}")

    # --- GAMLSS/LMS fit in R (one curve per stage) ---
    with tempfile.TemporaryDirectory() as td:
        inp, outp = f"{td}/in.csv", f"{td}/out.csv"
        c[["stage", "t", "val"]].to_csv(inp, index=False)
        r = subprocess.run(["Rscript", "scripts/gamlss_fit.R", inp, outp, METHOD], capture_output=True, text=True)
        print(r.stdout[-600:]); print(r.stderr[-400:] if r.returncode else "")
        curves = pd.read_csv(outp)

    fig, axes = plt.subplots(3, 2, figsize=(12, 13))
    axes = axes.ravel()
    for ai, stage in enumerate(STAGES):
        ax = axes[ai]; col = YODA[stage]
        sub = c[c.stage == stage]
        ax.scatter(sub.t, sub.val, s=4, alpha=0.20, color="#333333", edgecolors="none", zorder=1)
        cv = curves[curves.group == stage].sort_values("t")
        if len(cv):
            for lo, hi_ in BANDS:
                ax.fill_between(cv.t, cv[f"p{lo}"], cv[f"p{hi_}"], color=col, alpha=0.22, lw=0, zorder=2)
            ax.plot(cv.t, cv.p50, color=col, lw=2.4, zorder=3)
            # QC overlay: model-free rolling median (sliding age-widening window) — the LMS median (solid)
            # should track this dashed line. Divergence = a fit problem, not noise.
            emp50 = rolling_pctile(sub.t.values, sub.val.values, cv.t.values, 0.50)
            ax.plot(cv.t, emp50, color="k", lw=1.1, ls=(0, (4, 2)), zorder=4, alpha=0.7)
        ax.set_title(f"{stage}  (n={sub.bdsp_id.nunique()} recordings)", fontsize=11, fontweight="bold")
        ax.grid(alpha=0.2)
        ax.set_xticks(A2T(TICK_AGES)); ax.set_xticklabels(TICK_LABELS, fontsize=7, rotation=45, ha="right")
        ax.set_ylabel(FEATURE)
        p2 = np.nanpercentile(sub.val, [0.5, 99.5]); ax.set_ylim(p2[0], p2[1])
        if ai >= 3: ax.set_xlabel("age (years, log-scaled)")

    # 6th panel: all-stage median overlay (+ light p25-75)
    axo = axes[5]
    for stage in STAGES:
        cv = curves[curves.group == stage].sort_values("t")
        if not len(cv): continue
        axo.fill_between(cv.t, cv.p25, cv.p75, color=YODA[stage], alpha=0.12, lw=0)
        axo.plot(cv.t, cv.p50, color=YODA[stage], lw=2.2, label=stage)
    axo.set_title("All stages — median (band = p25–p75)", fontsize=11, fontweight="bold")
    axo.grid(alpha=0.2); axo.legend(fontsize=9, ncol=5, loc="upper right", frameon=False)
    axo.set_xticks(A2T(TICK_AGES)); axo.set_xticklabels(TICK_LABELS, fontsize=7, rotation=45, ha="right")
    axo.set_xlabel("age (years, log-scaled)"); axo.set_ylabel(FEATURE)

    srcnote = {"auto": "wake=routine, sleep=overnight", "pooled": "cohort+expansion POOLED",
               "cohort": "routine EEG only", "expansion": "overnight EEG only"}.get(SOURCE, SOURCE)
    fig.suptitle(f"Normative growth curves — {FEATURE}, central (C3/C4), by sleep stage (sexes pooled)\n"
                 f"GAMLSS/LMS BCT fit [{METHOD}]; source: {srcnote}; bands p3-p97/p10-p90/p25-p75; "
                 f"dashed = model-free rolling median; n={c.bdsp_id.nunique()} clean-normal EEGs", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    tag = "" if SOURCE == "auto" else f"_{SOURCE}"
    out = Path(f"figures/growth_v2/central_{FEATURE}_{METHOD}{tag}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
