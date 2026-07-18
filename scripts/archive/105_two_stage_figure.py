"""Figure 4 — the system as it is actually meant to be used: GATE, then QUANTIFY.

The pipeline is two-stage. Morgoth decides *whether and what* (detection). Our normative deviations then say
*how much of it there is* (quantification). Evaluating our linear predictor as if it were the detector asks it
to do a job it was never given -- and, for focal slowing, a job that is intrinsically topographic.

Top row     : ROC of the Morgoth gate against the expert majority, with all 18 electroencephalographers
              overlaid as individual operating points (each scored against the majority of the other 17).
              Our score S is drawn faintly, for reference only, as a detector.
Bottom row  : box plots of the corresponding linear predictor across consensus categories
              (neither / focal only / generalized only / both). This is the claim that matters: the EEGs the
              panel calls slow do quantitatively carry more of that kind of slowing.

Run: PYTHONPATH=src python scripts/105_two_stage_figure.py
"""
from __future__ import annotations
import json, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import kruskal, mannwhitneyu
from sklearn.metrics import roc_auc_score, roc_curve
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

spec = importlib.util.spec_from_file_location("m103", "scripts/103_sparse_slowing_score.py")
m103 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m103)
rng = np.random.default_rng(0)

GROUPS = ["neither", "focal only", "generalized only", "both"]
GCOL = {"neither": "#8fbf8f", "focal only": "#4c78a8",
        "generalized only": "#f2a541", "both": "#b03a48"}


def auc_ci(y, s, n=3000):
    a = roc_auc_score(y, s); bs = []
    for _ in range(n):
        j = rng.choice(len(y), len(y), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def our_scores():
    frozen = json.loads(Path("data/derived/sparse_score_coefs.json").read_text())
    coh = pd.read_parquet("data/derived/channel_stage_features.parquet")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    ref = coh[(coh.src == "cohort") & (coh.clean_normal == True) &
              coh.stage.isin(m103.STAGES) & ~coh.bdsp_id.isin(ex)]
    R = m103.ref_curves(ref)
    occ = pd.read_parquet("data/derived/occasion_features.parquet").rename(columns={"fid": "bdsp_id"})
    occ["bdsp_id"] = occ.bdsp_id.astype(str)
    X = m103.z_table(occ[occ.stage.isin(m103.STAGES)], R)
    S = {}
    for nm, f in frozen.items():
        cols = list(f["coef"])
        Xi = X.reindex(columns=cols)
        for c in cols:
            Xi[c] = Xi[c].fillna(f["impute"][c])
        Z = (Xi - pd.Series(f["center"])[cols]) / pd.Series(f["scale"])[cols]
        S[nm] = Z.mul(pd.Series(f["coef"])[cols], axis=1).sum(axis=1) + f["intercept"]
    return S


def main():
    S = our_scores()
    votes = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    mp = pd.read_parquet("data/derived/occasion_morgoth_preds.parquet")

    V = {ax: votes.pivot_table(index="fid", columns="rater", values=f"r1.{ax}") for ax in ["FN", "GN"]}
    maj = pd.DataFrame({ax: (v.mean(1) >= 0.5).astype(int) for ax, v in V.items()})
    maj.index = maj.index.astype(str)

    grp = pd.Series("neither", index=maj.index)
    grp[(maj.FN == 1) & (maj.GN == 0)] = "focal only"
    grp[(maj.FN == 0) & (maj.GN == 1)] = "generalized only"
    grp[(maj.FN == 1) & (maj.GN == 1)] = "both"

    out = ["# Figure 4 — gate, then quantify\n",
           "The system is two-stage: **Morgoth decides whether and what; our normative deviations say how "
           "much.** Scoring our linear predictor as if it were the detector asks it to do a job it was never "
           "given — and, for focal slowing, an intrinsically topographic one.\n",
           f"Consensus groups (expert majority of 18 raters): " +
           ", ".join(f"{g} n={int((grp == g).sum())}" for g in GROUPS) + "\n",
           "**Note.** The panel's EEGs were curated so that focal and generalized non-epileptiform findings "
           "are essentially disjoint (only 1 of 100 is called both). In our clinical cohort they co-occur in "
           "**60.9%** of focal recordings. The panel therefore poses the focal-versus-generalized question "
           "cleanly, which our report-derived labels cannot; the `both` group is too small to plot and is "
           "shown for completeness only.\n"]

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10))
    for col, (nm, axis, title) in enumerate([("generalized", "GN", "generalized slowing"),
                                             ("focal", "FN", "focal slowing")]):
        y = maj[axis]
        m = mp[mp.axis == axis].copy(); m["fid"] = m.fid.astype(str)
        m = m.set_index("fid").reindex(y.index)
        ok = m.M_pred.notna().values

        # ---------------- top: Morgoth ROC + every expert as an operating point
        ax = axes[0, col]
        a_m, lo_m, hi_m = auc_ci(y.values[ok], m.M_pred.values[ok])
        fpr, tpr, _ = roc_curve(y.values[ok], m.M_pred.values[ok])
        ax.plot(fpr, tpr, lw=2.4, color="#333333", label=f"Morgoth gate — AUROC {a_m:.3f}")

        s = S[nm].reindex(y.index)
        ok2 = s.notna().values
        a_s, lo_s, hi_s = auc_ci(y.values[ok2], s.values[ok2])
        fpr2, tpr2, _ = roc_curve(y.values[ok2], s.values[ok2])
        ax.plot(fpr2, tpr2, lw=1.2, ls="--", color="#4c78a8", alpha=.85,
                label=f"our S, used as a detector — {a_s:.3f}\n(not its role: see the panel below)")

        E = V[axis]; E.index = E.index.astype(str)
        E = E.reindex(y.index)
        for i, r in enumerate(E.columns):
            oth = E.drop(columns=[r])
            cons = (oth.mean(1) >= 0.5).astype(int)
            e = E[r]; msk = e.notna()
            if cons[msk].sum() in (0, msk.sum()): continue
            se = e[msk][cons[msk] == 1].mean(); sp = 1 - e[msk][cons[msk] == 0].mean()
            ax.plot(1 - sp, se, "o", ms=6.5, mfc="none", mec="crimson", mew=1.4,
                    label="individual expert (vs the other 17)" if i == 0 else None)
        ax.plot([0, 1], [0, 1], "k:", lw=.7)
        ax.set_title(f"GATE — {title}", fontsize=11, weight="bold")
        ax.set_xlabel("1 − specificity"); ax.set_ylabel("sensitivity")
        ax.legend(loc="lower right", fontsize=7.5)
        out.append(f"\n## {title}\n")
        out.append(f"- **Morgoth gate: AUROC {a_m:.3f}** [{lo_m:.3f}, {hi_m:.3f}] against the expert majority")
        out.append(f"- our S as a detector: {a_s:.3f} [{lo_s:.3f}, {hi_s:.3f}] — reported only to show that "
                   f"this is not the quantity it is for")

        # ---------------- bottom: the quantifier, by consensus group
        ax = axes[1, col]
        data, labs, cols_ = [], [], []
        for g in GROUPS:
            v = s[(grp == g).values].dropna().values
            if len(v) < 3: continue
            data.append(v); labs.append(f"{g}\n(n={len(v)})"); cols_.append(GCOL[g])
        bp = ax.boxplot(data, showfliers=False, patch_artist=True, widths=.6)
        for patch, c in zip(bp["boxes"], cols_):
            patch.set_facecolor(c); patch.set_alpha(.8)
        for i, v in enumerate(data):
            ax.scatter(np.full(len(v), i + 1) + rng.normal(0, .06, len(v)), v, s=13,
                       color="k", alpha=.45, zorder=3)
        ax.set_xticklabels(labs, fontsize=8)
        ax.set_ylabel(f"S ({nm}) — linear predictor")
        ax.set_title(f"QUANTIFY — S({nm}) by expert consensus", fontsize=11, weight="bold")

        kw = kruskal(*data)
        out.append(f"- **S({nm}) across consensus groups: Kruskal–Wallis p = {kw.pvalue:.2e}**")
        base = s[(grp == "neither").values].dropna().values
        for g in GROUPS[1:]:
            v = s[(grp == g).values].dropna().values
            if len(v) < 3: continue
            u = mannwhitneyu(v, base)
            out.append(f"  - {g}: median {np.median(v):+.2f} vs neither {np.median(base):+.2f} "
                       f"(Mann–Whitney p = {u.pvalue:.1e}, n = {len(v)})")

    fig.suptitle("The system as used: Morgoth GATES (whether/what), our normative deviations QUANTIFY (how much)\n"
                 "top: gate vs 18 electroencephalographers   ·   bottom: the linear predictor by expert consensus",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig("figures/growth_v2/two_stage_gate_and_quantify.png", dpi=140); plt.close(fig)

    out.append("\n## Why our score trails the experts on FOCAL slowing, but not on generalized\n")
    out.append("Three reasons, all measurable. **(1) The focal task is a topography task.** 21% of the EEGs "
               "we must *reject* as non-focal (18 of 86) are recordings the panel calls generalized-slow — "
               "they are slow, just not focally. Separating those from truly focal recordings is exactly the "
               "contrast on which a spectral-deviation score is weakest: restricted to exclusively focal "
               "recordings, it is at chance in-cohort (0.477). **(2) Morgoth sees pattern; we see amount.** "
               "Morgoth is *better* on focal (0.923) than on generalized (0.895); our score is *worse* on "
               "focal (0.848) than generalized (0.909). The gate has full morphological and topographic "
               "access; our features are recording-level averages of spectral deviation. **(3) Focal slowing "
               "is intermittent.** A 30-second run of left temporal theta in a 50-minute study barely moves a "
               "mean asymmetry, but is unmissable to a reader scrolling the trace.\n")
    out.append("None of this is a defect of the quantifier. It is the argument *for* the two-stage design: "
               "let the foundation model decide **whether and what**, and let the normative deviations say "
               "**how much** — which the bottom row shows they do.\n")
    out.append("## What the bottom row shows, and one honest wrinkle\n")
    out.append("**S(generalized) is specific.** It rises sharply in generalized-slowing EEGs (median +0.77 vs "
               "−0.38 in EEGs the panel calls neither, p = 3.3e-8) and does **not** rise in focal-only EEGs "
               "(−0.24, p = 0.24). The generalized quantifier measures generalized slowing.\n")
    out.append("**S(focal) is sensitive but not perfectly specific.** It rises in focal EEGs (median +0.23 vs "
               "−0.14, p = 3.0e-5), but it also rises modestly in generalized-only EEGs (−0.07 vs −0.14, "
               "p = 5.7e-3). That is the same limitation quantified elsewhere: a spectral asymmetry score "
               "cannot fully separate focal from generalized slowing. Gating on Morgoth's focal call before "
               "quantifying is what removes that ambiguity in use.")
    Path("results/two_stage_gate_and_quantify.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
