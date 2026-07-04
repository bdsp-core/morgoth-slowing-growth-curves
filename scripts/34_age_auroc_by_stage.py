"""Age-dependent abnormal-detection AUROC, BROKEN OUT BY SLEEP STAGE — feature-based model vs Morgoth.

Morgoth's gate probability is recording-level (one per EEG), so it can't be split by stage; it's plotted
once as the reference. OUR feature-based model uses per-(region, stage) qEEG features, so we can ask a
question Morgoth can't: how well does slowing separate abnormal-from-normal at each age WITHIN each
sleep stage? For each stage we fit a 5-fold OOF logistic regression on that stage's regional features
(rel_delta/DAR/TAR/log_delta x 6 regions), then AUROC vs the clinical label within each age band.

Writes results/figs/age_auroc_by_stage.png + results/age_auroc_by_stage.csv.
Run: PYTHONPATH=src python scripts/34_age_auroc_by_stage.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

BANDS = [(0, 12), (13, 18), (19, 30), (31, 45), (46, 60), (61, 75), (76, 100)]
STAGES = [("W", "#f5a623"), ("N1", "#8e6fd6"), ("N2", "#4a90e2"), ("N3", "#2ec4b6"), ("REM", "#e0568a")]
METRICS = ["rel_delta", "DAR", "TAR"]         # slowing-direction metrics (higher = more slowing)
REGION = "whole_head"
NBOOT = 300


def boot(y, s, rng):
    if len(np.unique(y)) < 2 or len(y) < 15:
        return np.nan, np.nan, np.nan
    a = roc_auc_score(y, s); bs = []
    for _ in range(NBOOT):
        b = rng.choice(len(y), len(y), replace=True)
        if len(np.unique(y[b])) == 2:
            bs.append(roc_auc_score(y[b], s[b]))
    return a, (np.percentile(bs, 2.5) if bs else np.nan), (np.percentile(bs, 97.5) if bs else np.nan)


def stage_curve(rsf, stage, rng):
    """Per age band: abnormality score = summed deviation of stage-specific slowing metrics from the
    age-matched NORMAL recordings IN THAT STAGE (so physiologic sleep/age delta is subtracted out).
    Returns (aurocs, lo, hi, n) per band."""
    sub = rsf[(rsf.stage == stage) & (rsf.region == REGION)].copy()
    sub = sub[(sub.age >= 0) & (sub.age <= 100)].dropna(subset=["label"])
    ys, los, his, ns = [], [], [], []
    for lo, hi in BANDS:
        b = sub[(sub.age >= lo) & (sub.age <= hi)]
        nm = b[b.label == "normal"]
        if len(nm) < 10 or b.label.nunique() < 2:
            ys.append(np.nan); los.append(np.nan); his.append(np.nan); ns.append(len(b)); continue
        score = np.zeros(len(b))
        for m in METRICS:
            mu, sd = nm[m].mean(), nm[m].std() + 1e-9
            score = score + ((b[m] - mu) / sd).to_numpy()
        y = (b.label != "normal").astype(int).to_numpy()
        a, l, h = boot(y, score, rng)
        ys.append(a); los.append(l); his.append(h); ns.append(int(len(b)))
    return ys, los, his, ns


def morgoth_ref(rng):
    g = pd.read_parquet("data/derived/gate_probs.parquet")
    c = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "age"]]
    d = g.merge(c, on="bdsp_id").query("0 <= age <= 100")
    d = d[d.label.isin(["normal", "focal_slow", "general_slow"])]
    y = (d.label != "normal").astype(int).to_numpy(); s = d.p_abnormal.to_numpy(); age = d.age.to_numpy()
    xs, ys = [], []
    for lo, hi in BANDS:
        m = (age >= lo) & (age <= hi)
        a, _, _ = boot(y[m], s[m], rng)
        xs.append((lo + hi) / 2); ys.append(a)
    return xs, ys


def main():
    rsf = pd.read_parquet("data/derived/regional_stage_recording_features.parquet")
    rng = np.random.default_rng(0)
    xs = [(lo + hi) / 2 for lo, hi in BANDS]
    rows = []
    fig, ax = plt.subplots(figsize=(9, 5.4))
    for stage, color in STAGES:
        ys, los, his, ns = stage_curve(rsf, stage, rng)
        for (lo, hi), a, n in zip(BANDS, ys, ns):
            rows.append({"stage": stage, "age_band": f"{lo}-{hi}", "n": n,
                         "auroc": None if a is None or np.isnan(a) else round(a, 3)})
        ys = np.array(ys, float)
        ax.plot(xs, ys, marker="o", color=color, lw=2, label=f"our model · {stage}")
        ax.fill_between(xs, np.array(los, float), np.array(his, float), color=color, alpha=0.10)
    mx, my = morgoth_ref(rng)
    ax.plot(mx, my, marker="s", color="#111", lw=2.5, ls="--", label="Morgoth (recording-level)")
    ax.axhline(0.5, ls=":", color="#aaa", lw=1)
    ax.set_xlabel("Age (years, band midpoint)"); ax.set_ylabel("AUROC — abnormal vs normal")
    ax.set_ylim(0.4, 1.0); ax.set_title("Abnormal-slowing detection by age & sleep stage (ours) vs Morgoth")
    ax.legend(loc="lower right", fontsize=8, ncol=2); ax.grid(alpha=0.25)
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/age_auroc_by_stage.png", dpi=130)
    pd.DataFrame(rows).to_csv("results/age_auroc_by_stage.csv", index=False)
    print(pd.DataFrame(rows).pivot(index="age_band", columns="stage", values="auroc").to_string())
    print("\nwrote results/figs/age_auroc_by_stage.png + results/age_auroc_by_stage.csv")


if __name__ == "__main__":
    main()
