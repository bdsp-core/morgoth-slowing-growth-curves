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
    out = ["# External test of the sparse score S against the 18-expert panel\n",
           "Coefficients were frozen on the in-cohort data (`scripts/103`). Nothing about these 100 EEGs "
           "informed the normal reference, the correlation clusters, the penalty, the L1 selection, or the "
           "weights. This script only applies them.\n",
           "The focal detector is evaluated on the same three questions as in-cohort, using the expert "
           "majority on each axis (FN = focal non-epileptiform, GN = generalized non-epileptiform).\n"]

    pairs = [("generalized", "GN"), ("focal", "FN")]
    pairs = [p for p in pairs if p[0] in frozen]
    fig, axes = plt.subplots(1, len(pairs), figsize=(6 * len(pairs), 5))
    axes = np.atleast_1d(axes)
    scores = {}
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
        scores[nm] = pd.Series(S.values, index=S.index)

        ax.scatter(s[ok], p[ok], c=["#e45756" if t else "#8fbf8f" for t in y[ok]], s=26, alpha=.85,
                   edgecolors="k", linewidths=.3)
        ax.set_xlabel(f"S ({nm}) — linear predictor, {len(cols)} features")
        ax.set_ylabel("fraction of 18 experts marking slowing")
        ax.set_title(f"{nm}: AUROC {a:.3f}, ρ={rho:.3f} vs consensus proportion")
    # ---- the focal detector on three questions, using expert-majority labels
    V = {ax: votes.pivot_table(index="fid", columns="rater", values=f"r1.{ax}") for ax in ["FS", "FN", "GS", "GN"]}
    maj = {ax: (v.mean(1) >= 0.5).astype(int) for ax, v in V.items()}
    M = pd.DataFrame(maj); M.index = M.index.astype(str)
    Sf = scores["focal"]
    common = [i for i in Sf.index if i in M.index]
    M = M.loc[common]; Sf = Sf.loc[common]
    no_abn = (M[["FS", "FN", "GS", "GN"]].sum(1) == 0)

    def auc_of(pos, neg):
        p_, n_ = Sf[pos], Sf[neg]
        if len(p_) < 5 or len(n_) < 5: return None
        y = np.r_[np.ones(len(p_)), np.zeros(len(n_))]
        return auc_ci(y, np.r_[p_.values, n_.values])

    out.append("\n## The focal detector, evaluated on three different questions (expert majority)\n")
    out.append("**Note on the positives:** an expert calling focal slowing does not exclude generalized "
               "slowing. The second block restricts positives to EEGs the panel called focal and NOT "
               "generalized.\n")
    out.append("| positives | comparison group | AUROC [95% CI] | n |")
    out.append("|---|---|---|---|")
    for plabel, pos in [("all focal (FN)", M.FN == 1),
                        ("exclusively focal (FN, not GN)", (M.FN == 1) & (M.GN == 0))]:
        for clabel, neg in [("no abnormality (all four axes 0)", no_abn),
                            ("everything else", (M.FN == 0)),
                            ("generalized, not focal (GN, not FN)", (M.GN == 1) & (M.FN == 0))]:
            r = auc_of(pos, neg)
            if r is None:
                out.append(f"| {plabel} | {clabel} | n/a (too few) | — |"); continue
            a, lo, hi = r
            out.append(f"| {plabel} | {clabel} | **{a:.3f}** [{lo:.3f}, {hi:.3f}] | "
                       f"{int(pos.sum())} vs {int(neg.sum())} |")

    fig.suptitle("Sparse score S, coefficients frozen in-cohort, applied to 100 expert-read EEGs\n"
                 "red = expert majority called slowing", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig("figures/growth_v2/sparse_score_external.png", dpi=140); plt.close(fig)

    Path("results/sparse_score_external.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
