"""Refreshed discrimination on the RECOMPUTED UNION data (both cohorts, identical extract.py pipeline).
Recording-level whole-head features (n_seg-weighted mean over stages), age-adjusted normal-referenced z
(kernel over the union clean-normals), AUROC for normal-vs-abnormal / focal / generalized-pathologic.
Everything is now pipeline-comparable, so TAR/DAR are valid here (unlike before the recompute).

Run: PYTHONPATH=src python scripts/83_union_discrimination.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATURES = ["TAR", "DAR", "log_delta", "log_theta", "rel_delta"]
REGION = "whole_head"
rng = np.random.default_rng(0)


def normal_z(vals, ages, ref_vals, ref_ages, bw=5.0):
    z = np.full(len(vals), np.nan); ra, rv = np.asarray(ref_ages), np.asarray(ref_vals)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    for i in range(len(vals)):
        if not (np.isfinite(vals[i]) and np.isfinite(ages[i])): continue
        w = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = w.sum()
        if sw < 5: continue
        mu = (w * rv).sum() / sw; sd = np.sqrt(max((w * (rv - mu) ** 2).sum() / sw, 1e-9))
        z[i] = (vals[i] - mu) / sd
    return z


def auc_ci(y, s, n=400):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    a = roc_auc_score(y, s); idx = np.arange(len(y)); bs = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


STAGES = ["W", "N1", "N2", "N3", "REM"]


def main():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "has_focal_slow", "has_gen_slow", "gen_class"]].drop_duplicates("bdsp_id")
    w = d[(d.region == REGION) & d.age.between(0, 100)].merge(lu, on="bdsp_id", how="left")
    # PER-STAGE detection: slowing is stage-specific (strong W/N1/REM, collapses N2/N3), so averaging
    # over stages dilutes it. One row per (recording, stage); z vs that stage's union clean-normals.
    targets = {"abnormal": w.is_abnormal == True, "focal": w.has_focal_slow == True,
               "gen_pathologic": w.gen_class == "pathologic"}
    w = w.assign(**{f"_t_{k}": v for k, v in targets.items()})
    rows = []
    for st in STAGES:
        s = w[w.stage == st]
        norm = s[s.clean_normal == True]
        for feat in FEATURES:
            z = normal_z(s[feat].values, s.age.values, norm[feat].values, norm.age.values)
            for tname in targets:
                pos = s[f"_t_{tname}"].values
                mask = pos | (s.clean_normal == True).values
                y = pos[mask].astype(int); sc = z[mask]
                if y.sum() < 15: continue
                a, lo, hi = auc_ci(y, sc)
                rows.append({"stage": st, "feature": feat, "target": tname,
                             "auc": a, "lo": lo, "hi": hi, "n_pos": int(y.sum())})
    res = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True); res.to_csv("results/union_discrimination.csv", index=False)
    print("=== AUROC by STAGE (age-adjusted whole-head z, union clean-normal reference) ===")
    for tname in targets:
        print(f"\nnormal vs {tname}:")
        piv = res[res.target == tname].pivot(index="feature", columns="stage", values="auc").reindex(FEATURES)[STAGES]
        print(piv.round(3).to_string())

    # figure: for each target, AUROC of the best feature (TAR) across stages + the top features in W
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, tname in zip(axes, targets):
        sub = res[res.target == tname]
        x = np.arange(len(STAGES)); wd = 0.16
        for i, feat in enumerate(FEATURES):
            fs = sub[sub.feature == feat].set_index("stage").reindex(STAGES)
            ax.bar(x + (i - 2) * wd, fs.auc, wd, label=feat)
        ax.axhline(0.5, color="k", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(STAGES)
        ax.set_ylim(0.4, 0.85); ax.set_title(f"normal vs {tname}"); ax.set_ylabel("AUROC")
    axes[0].legend(fontsize=8, ncol=2)
    fig.suptitle("Stage-stratified discrimination on recomputed union data (whole-head, age-adjusted) — "
                 "slowing is detectable in W/N1/REM, collapses in N2/N3", fontsize=12)
    fig.tight_layout(); fig.savefig("figures/growth_v2/union_discrimination.png", dpi=130); plt.close(fig)
    print("\nwrote results/union_discrimination.csv + figures/growth_v2/union_discrimination.png")


if __name__ == "__main__":
    main()
