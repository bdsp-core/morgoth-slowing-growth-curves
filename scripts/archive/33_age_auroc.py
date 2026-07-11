"""Age-dependent AUROC of the Morgoth gate — does the detector work equally well across ages?

For each age band, AUROC of the gate probability vs the report label (each contrast against NORMAL):
  - abnormal (any slowing) : p_abnormal,     focal|gen  vs  normal
  - focal slowing          : p_focal,        focal      vs  normal
  - generalized slowing    : p_generalized,  gen        vs  normal
with 95% bootstrap CIs. Uses the original 12,379-recording cohort (gate probs + ages + labels); the
newly-ingested recordings fold in once enough have accumulated. Writes results/figs/age_auroc.png
+ results/age_auroc.csv.

Run: PYTHONPATH=src python scripts/33_age_auroc.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

BANDS = [(0, 12), (13, 18), (19, 30), (31, 45), (46, 60), (61, 75), (76, 100)]
CONTRASTS = [("abnormal", "p_abnormal", ("focal_slow", "general_slow"), "#4a7fe0"),
             ("focal", "p_focal", ("focal_slow",), "#f5a623"),
             ("generalized", "p_generalized", ("general_slow",), "#e0568a")]
NBOOT = 300


def boot_auc(y, s, rng):
    if len(np.unique(y)) < 2 or len(y) < 12:
        return (np.nan, np.nan, np.nan)
    a = roc_auc_score(y, s)
    bs = []
    idx = np.arange(len(y))
    for _ in range(NBOOT):
        b = rng.choice(idx, len(idx), replace=True)
        if len(np.unique(y[b])) == 2:
            bs.append(roc_auc_score(y[b], s[b]))
    lo, hi = (np.nanpercentile(bs, [2.5, 97.5]) if bs else (np.nan, np.nan))
    return (a, lo, hi)


def load():
    g = pd.read_parquet("data/derived/gate_probs.parquet")
    c = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "age"]]
    df = g.merge(c, on="bdsp_id", how="inner")
    # fold in expansion gate probs if present
    exp = Path("results/expansion_gate_probs.csv"); prov = Path("results/expansion_provenance.csv")
    if exp.exists() and prov.exists():
        e = pd.read_csv(exp).rename(columns={"normal_head_prob": "p_abnormal"})
        pv = pd.read_csv(prov)[["bdsp_id", "label", "age"]]
        e = e.merge(pv, on="bdsp_id", how="left")
        keep = ["bdsp_id", "p_abnormal", "p_focal", "p_generalized", "label", "age"]
        df = pd.concat([df[keep], e[[k for k in keep if k in e]]], ignore_index=True)
    return df[(df.age >= 0) & (df.age <= 100)].copy()


def main():
    df = load()
    rng = np.random.default_rng(0)
    rows = []
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    xs = [(lo + hi) / 2 for lo, hi in BANDS]
    for name, score, pos_labels, color in CONTRASTS:
        ys, los, his, ns = [], [], [], []
        for lo, hi in BANDS:
            sub = df[(df.age >= lo) & (df.age <= hi)]
            sub = sub[sub.label.isin(list(pos_labels) + ["normal"])]
            y = sub.label.isin(pos_labels).astype(int).to_numpy()
            s = pd.to_numeric(sub[score], errors="coerce").to_numpy()
            ok = ~np.isnan(s)
            a, l, h = boot_auc(y[ok], s[ok], rng)
            ys.append(a); los.append(l); his.append(h); ns.append(int(ok.sum()))
            rows.append({"contrast": name, "age_band": f"{lo}-{hi}", "n": int(ok.sum()),
                         "auroc": None if np.isnan(a) else round(a, 3),
                         "ci_lo": None if np.isnan(l) else round(l, 3),
                         "ci_hi": None if np.isnan(h) else round(h, 3)})
        ys = np.array(ys, float)
        yerr = np.abs(np.vstack([ys - np.array(los, float), np.array(his, float) - ys]))
        ax.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, color=color, lw=2, label=name)
    ax.axhline(0.5, ls="--", color="#999", lw=1)
    ax.set_xlabel("Age (years, band midpoint)"); ax.set_ylabel("AUROC vs. normal")
    ax.set_ylim(0.4, 1.0); ax.set_title("Age-dependent gate discrimination (Morgoth vs. report labels)")
    ax.legend(title="contrast", loc="lower right"); ax.grid(alpha=0.25)
    # annotate n at the bottom for the abnormal contrast
    for x, r in zip(xs, [row for row in rows if row["contrast"] == "abnormal"]):
        ax.annotate(f"n={r['n']}", (x, 0.42), ha="center", fontsize=8, color="#666")
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/age_auroc.png", dpi=130)
    pd.DataFrame(rows).to_csv("results/age_auroc.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nwrote results/figs/age_auroc.png + results/age_auroc.csv")


if __name__ == "__main__":
    main()
