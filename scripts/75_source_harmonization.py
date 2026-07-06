"""SOURCE HARMONIZATION DIAGNOSTIC — the central data-quality check for the pooled growth curves.
Cohort (routine ~20-min EEG, JJ .mat pipeline) and expansion (overnight EEG, extract.py pipeline) are only
partly comparable: rel_delta was calibrated across pipelines but sleep-stage physiology + staging differ
(routine sleep is rare/mis-staged; overnight sleep is real). This overlays cohort-only vs expansion-only
rolling medians per stage so we can SEE where the two sources agree (poolable) vs diverge (use one source).

Run: PYTHONPATH=src python scripts/75_source_harmonization.py [feature]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATURE = sys.argv[1] if len(sys.argv) > 1 else "rel_delta"
TABLE = "data/derived/channel_stage_features.parquet"
CENTRAL = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
TICK_AGES = [0, 1/12, 6/12, 1, 2, 5, 10, 20, 40, 80]
TICK_LABELS = ["0", "1mo", "6mo", "1", "2", "5", "10", "20", "40", "80"]
def A2T(age): return np.log10(np.asarray(age, float) + 1/12)


def roll(t_data, v_data, t_grid, q=0.5, h=0.14):
    t_data, v_data = np.asarray(t_data), np.asarray(v_data)
    out = np.full(len(t_grid), np.nan)
    for i, t0 in enumerate(t_grid):
        w = np.exp(-0.5 * ((t_data - t0) / h) ** 2)
        if w.sum() < 8: continue
        idx = np.argsort(v_data); vs, ws = v_data[idx], w[idx]
        cw = (np.cumsum(ws) - 0.5 * ws) / ws.sum()
        out[i] = np.interp(q, cw, vs)
    return out


def main():
    df = pd.read_parquet(TABLE)
    c = df[df.region.isin(CENTRAL)].groupby(["bdsp_id", "stage", "src"]).agg(
        val=(FEATURE, "mean"), age=("age", "first"),
        clean=("clean_normal", "first")).reset_index()
    c = c[(c.clean == True) & c.age.between(0, 95)]
    hi = 1.0 if FEATURE.startswith("rel") else 1e9
    c = c[c.val.between(0, hi)]; c["t"] = A2T(c.age)
    tg = np.linspace(A2T(0), A2T(90), 160)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8)); axes = axes.ravel()
    rows = []
    for ai, stage in enumerate(STAGES):
        ax = axes[ai]
        for src, col in [("cohort", "#d1495b"), ("expansion", "#2e86ab")]:
            s = c[(c.stage == stage) & (c.src == src)]
            if len(s) < 30: continue
            ax.scatter(s.t, s.val, s=3, alpha=0.10, color=col, edgecolors="none")
            m = roll(s.t.values, s.val.values, tg)
            ax.plot(tg, m, color=col, lw=2.4, label=f"{src} (n={s.bdsp_id.nunique()})")
        ax.set_title(stage, fontsize=12, fontweight="bold"); ax.legend(fontsize=8); ax.grid(alpha=0.2)
        ax.set_xticks(A2T(TICK_AGES)); ax.set_xticklabels(TICK_LABELS, fontsize=7, rotation=45, ha="right")
        ax.set_ylabel(FEATURE)
        # quantify offset in pediatric (1-12) and adult (20-60) windows
        for lo, hi_, tag in [(1, 12, "peds"), (20, 60, "adult")]:
            co = c[(c.stage == stage) & (c.src == "cohort") & c.age.between(lo, hi_)].val
            ex = c[(c.stage == stage) & (c.src == "expansion") & c.age.between(lo, hi_)].val
            if len(co) > 15 and len(ex) > 15:
                rows.append({"stage": stage, "window": tag, "cohort_med": round(co.median(), 3),
                             "exp_med": round(ex.median(), 3), "offset": round(ex.median() - co.median(), 3),
                             "n_co": len(co), "n_ex": len(ex)})
    axes[5].axis("off")
    summ = pd.DataFrame(rows)
    txt = summ.to_string(index=False)
    axes[5].text(0.0, 0.95, f"{FEATURE}: cohort vs expansion offset\n\n{txt}", family="monospace",
                 fontsize=8, va="top", transform=axes[5].transAxes)
    fig.suptitle(f"Source harmonization — {FEATURE}, central: cohort (routine EEG) vs expansion (overnight)\n"
                 "rolling medians; where they diverge, pooling is invalid — use the source appropriate to the stage",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = Path(f"figures/growth_v2/source_harmonization_{FEATURE}.png"); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight"); plt.close(fig)
    print(summ.to_string(index=False)); print("wrote", out)


if __name__ == "__main__":
    main()
