"""Per-STAGE test of whether reported slowing is distinguishable from physiologic (sleep) slowing.

Brandon's question: pathological slowing must be told apart from the delta that normally appears in
sleep. The report flags are whole-recording + stage-agnostic, so we test it directly in the features:
within each sleep stage, how well does a qEEG feature separate clean-normal recordings from
focal-slowing / generalized-slowing recordings (one-vs-clean-normal AUROC, per stage)?

Hypotheses: (1) focal slowing is distinguishable across stages incl. sleep; (2) generalized slowing is
HARD to distinguish inside sleep (N2/N3) because physiologic delta dominates — separable mainly in W/REM
or when extreme.

Reads data/derived/stage_recording_features.parquet (per recording x region x stage, clean labels +
lab_focal/lab_gen/lab_clean_normal injected by scripts/53). Writes results/stage_pathology.md +
results/figs/stage_pathology.png.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

srf = pd.read_parquet("data/derived/stage_recording_features.parquet")
wh = srf[srf.region == "whole_head"].copy()
STAGES = ["W", "N1", "N2", "N3", "REM"]
FEATS = ["rel_delta", "DAR", "rel_theta", "TAR"]


def auroc(sub, feat, poscol):
    n = sub[sub.lab_clean_normal == 1]
    p = sub[(sub[poscol] == 1) & (sub.lab_clean_normal == 0)]
    if len(n) < 20 or len(p) < 20:
        return np.nan, len(p), len(n)
    y = np.r_[np.zeros(len(n)), np.ones(len(p))]
    x = np.r_[n[feat].values, p[feat].values]
    m = ~np.isnan(x)
    return roc_auc_score(y[m], x[m]), len(p), len(n)


rows = []
for st in STAGES:
    s = wh[wh.stage == st]
    for feat in FEATS:
        for grp, col in [("focal", "lab_focal"), ("gen", "lab_gen")]:
            a, npos, nneg = auroc(s, feat, col)
            rows.append(dict(stage=st, feat=feat, group=grp, auroc=a, n_pos=npos, n_normal=nneg))
res = pd.DataFrame(rows)

L = ["# Per-stage distinguishability of slowing vs clean-normal (whole-head)\n",
     "\nAUROC of each feature separating clean-normal from focal / generalized slowing, WITHIN each stage.\n",
     "Low AUROC inside sleep = that 'slowing' is not distinguishable from physiologic sleep delta.\n\n"]
for feat in FEATS:
    L.append(f"## {feat}\n\n| stage | focal AUROC (n) | gen AUROC (n) |\n|---|---|---|\n")
    for st in STAGES:
        f = res[(res.stage == st) & (res.feat == feat) & (res.group == "focal")].iloc[0]
        g = res[(res.stage == st) & (res.feat == feat) & (res.group == "gen")].iloc[0]
        L.append(f"| {st} | {f.auroc:.3f} (n={f.n_pos}) | {g.auroc:.3f} (n={g.n_pos}) |\n")
    L.append("\n")
Path("results/stage_pathology.md").write_text("".join(L))
print("".join(L))

# figure: AUROC vs stage, focal vs gen, for DAR (headline feature)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
for ax, feat in zip(axes, ["DAR", "rel_delta"]):
    for grp, color in [("focal", "#f5a623"), ("gen", "#e0568a")]:
        d = res[(res.feat == feat) & (res.group == grp)].set_index("stage").reindex(STAGES)
        ax.plot(STAGES, d.auroc, "-o", color=color, label=grp, lw=2)
    ax.axhline(0.5, ls="--", color="#888"); ax.set_title(f"{feat}: slowing vs clean-normal by stage")
    ax.set_xlabel("stage"); ax.set_ylabel("AUROC"); ax.set_ylim(0.45, 1.0); ax.legend(); ax.grid(alpha=.25)
fig.tight_layout(); Path("results/figs").mkdir(parents=True, exist_ok=True)
fig.savefig("results/figs/stage_pathology.png", dpi=110, bbox_inches="tight")
print("wrote results/figs/stage_pathology.png")
