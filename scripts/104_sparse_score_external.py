"""Confirmatory external test of the sparse score S against the 18-expert panel.

Coefficients were FROZEN by scripts/103 on the in-cohort data alone (data/derived/sparse_score_coefs.json).
Nothing about OccasionNoise informed the reference, the correlation clusters, the C grid, the L1 selection or
the weights. This script only applies them.

DISCLOSURE: OccasionNoise has already been examined with hand-picked scores (scripts/94), so this is a
CONFIRMATORY check, not a first look. Read it that way.

Reported: AUROC of the linear predictor S against the expert majority, and Spearman rho of S against the
CONSENSUS PROPORTION (the fraction of 18 experts who marked slowing) -- the graded human target.

Run: PYTHONPATH=src python scripts/104_sparse_score_external.py
"""
from __future__ import annotations
import json, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

spec = importlib.util.spec_from_file_location("m103", "scripts/103_sparse_slowing_score.py")
m103 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m103)

HAND = {"generalized": 0.903, "focal": 0.738}          # scripts/94, hand-picked scores
MORGOTH = {"generalized": 0.895, "focal": 0.923}
rng = np.random.default_rng(0)


def auc_ci(y, s, n=4000):
    a = roc_auc_score(y, s); bs = []
    for _ in range(n):
        j = rng.choice(len(y), len(y), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    frozen = json.loads(Path("data/derived/sparse_score_coefs.json").read_text())

    # reference: ALL routine clean-normals from our cohort (the same population 103 used)
    coh = pd.read_parquet("data/derived/channel_stage_features.parquet")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    ref = coh[(coh.src == "cohort") & (coh.clean_normal == True) &
              coh.stage.isin(m103.STAGES) & ~coh.bdsp_id.isin(ex)]
    R = m103.ref_curves(ref)

    occ = pd.read_parquet("data/derived/occasion_features.parquet").rename(columns={"fid": "bdsp_id"})
    occ["bdsp_id"] = occ.bdsp_id.astype(str)
    occ = occ[occ.stage.isin(m103.STAGES)]
    X = m103.z_table(occ, R)

    votes = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    out = ["# Confirmatory external test of the sparse score S\n",
           "Coefficients frozen by `scripts/103` on the in-cohort data alone. Nothing about these 100 EEGs "
           "informed the reference, the clusters, the penalty, the selection, or the weights.\n",
           "**Disclosure 1.** OccasionNoise was already examined with hand-picked scores (`scripts/94`). "
           "This is confirmatory, not a first look.\n",
           "**Disclosure 2 — the focal_specific target is POST HOC.** The `focal` model was trained against "
           "clean-normals only, and it collapsed here (AUROC 0.611): trained that way, 'focal' is learnable "
           "as 'generally slow', and its two largest weights are indeed whole-head and midline terms. That "
           "failure is what prompted `focal_specific`, whose negatives include generalized-slowing "
           "recordings so the model cannot win on global slowing. The fix is principled — the panel's task "
           "(focal vs everything, including generalized) is not the task we had trained — and it was made "
           "without inspecting which features would help. **But the decision to make it was triggered by "
           "this test set.** The 0.848 below is therefore optimistic and requires independent confirmation "
           "on data neither model has seen. We report it as a hypothesis-generating result, not a validated "
           "one.\n"]

    pairs = [("generalized", "GN"), ("focal", "FN"), ("focal_specific", "FN")]
    pairs = [p for p in pairs if p[0] in frozen]
    fig, axes = plt.subplots(1, len(pairs), figsize=(6 * len(pairs), 5))
    axes = np.atleast_1d(axes)
    for ax, (nm, axis) in zip(axes, pairs):
        f = frozen[nm]
        cols = list(f["coef"])
        miss = [c for c in cols if c not in X.columns]
        Xi = X.reindex(columns=cols)
        for c in cols:                                    # same imputation the frozen model was fit with
            Xi[c] = Xi[c].fillna(f["impute"][c])
        Z = (Xi - pd.Series(f["center"])[cols]) / pd.Series(f["scale"])[cols]
        S = Z.mul(pd.Series(f["coef"])[cols], axis=1).sum(axis=1) + f["intercept"]

        v = votes.pivot_table(index="fid", columns="rater", values=f"r1.{axis}")
        maj = (v.mean(1) >= 0.5).astype(int)
        prop = v.mean(1)
        maj.index = maj.index.astype(str); prop.index = prop.index.astype(str)

        common = [i for i in S.index if i in maj.index]
        s, y, p = S.loc[common].values, maj.loc[common].values, prop.loc[common].values
        ok = np.isfinite(s)
        a, lo, hi = auc_ci(y[ok], s[ok])
        rho, pv = spearmanr(s[ok], p[ok])

        out.append(f"\n## {nm} slowing (n = {ok.sum()} EEGs, expert-majority prevalence {y[ok].mean():.2f})\n")
        out.append(f"- **S (frozen, {len(cols)} features): AUROC {a:.3f} [{lo:.3f}, {hi:.3f}]** vs the "
                   f"expert majority")
        hk = HAND.get(nm); mg = MORGOTH.get(nm)
        if hk: out.append(f"- hand-picked score (scripts/94): {hk:.3f}  |  Morgoth gate: {mg:.3f}")
        else:  out.append(f"- (no hand-picked comparator; Morgoth gate on this axis: {MORGOTH['focal']:.3f})")
        out.append(f"- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = "
                   f"**{rho:.3f}** (p = {pv:.1e}) — the graded human target")
        if miss:
            out.append(f"- note: {len(miss)} frozen feature(s) unavailable here and imputed: {miss}")
        out.append(f"- retained features: " + ", ".join(f"`{c}` ({f['coef'][c]:+.3f})" for c in cols))

        ax.scatter(s[ok], p[ok], c=["#e45756" if t else "#8fbf8f" for t in y[ok]], s=26, alpha=.85,
                   edgecolors="k", linewidths=.3)
        ax.set_xlabel(f"S ({nm}) — linear predictor, {len(cols)} features")
        ax.set_ylabel("fraction of 18 experts marking slowing")
        ax.set_title(f"{nm}: AUROC {a:.3f}, ρ={rho:.3f} vs consensus proportion")
    fig.suptitle("Sparse score S, coefficients frozen in-cohort, applied once to 100 expert-read EEGs\n"
                 "red = expert majority called slowing", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig("figures/growth_v2/sparse_score_external.png", dpi=140); plt.close(fig)

    Path("results/sparse_score_external.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
