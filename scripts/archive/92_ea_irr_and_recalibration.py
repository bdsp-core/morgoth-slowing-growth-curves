"""Expert-algorithm IRR vs expert-expert IRR, and honest recalibration of the Morgoth gate.

Two corrections to an earlier, wrong claim ("we cannot plausibly beat expert-expert agreement"):

1. **ea-IRR can exceed ee-IRR.** If each expert is (latent truth + independent noise), two experts compound
   two error sources while an accurate algorithm carries only one. The classical-test-theory analogy: the
   correlation between two parallel noisy measures equals the reliability, whereas the correlation of a
   *perfect* measure with a noisy one equals sqrt(reliability). So an algorithm at the latent truth should
   score kappa_ae ~= sqrt(kappa_ee) -- e.g. 0.450 -> 0.671. We therefore benchmark kappa_ae against BOTH the
   observed kappa_ee distribution and sqrt(kappa_ee).
   Caveat: expert errors are NOT independent (shared training, shared blind spots such as under-calling sleep
   slowing). Correlated errors inflate kappa_ee, which makes sqrt(kappa_ee) a *conservative* target.

2. **Evaluate the system we can build, not the default settings.** Morgoth's shipped threshold yields
   near-perfect specificity and poor sensitivity. We recalibrate and report the achievable operating point,
   with the thresholds/Platt coefficients fitted **leave-one-out** so no EEG informs its own call.

Run: python scripts/92_ea_irr_and_recalibration.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score
from sklearn.linear_model import LogisticRegression

SC = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
      "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/occ/results")
FILES = [("FocalSlowingOutput_Morgoth_experts.xlsx", "focal slowing"),
         ("GenSlowingOutput_Morgoth_experts.xlsx", "generalized slowing")]
rng = np.random.default_rng(0)


def ee_kappas(E):
    ks = []
    for i in range(E.shape[1]):
        for j in range(i + 1, E.shape[1]):
            a, b = E[:, i], E[:, j]
            if len(set(a)) > 1 and len(set(b)) > 1:
                ks.append(cohen_kappa_score(a, b))
    return np.array(ks)


def ae_kappas(pred, E):
    return np.array([cohen_kappa_score(pred, E[:, i]) for i in range(E.shape[1])
                     if len(set(E[:, i])) > 1 and len(set(pred)) > 1])


def loo_calls(score, y):
    """Leave-one-out Platt(@0.5) and LOO Youden-threshold calls. No EEG informs its own call."""
    n = len(y)
    platt, youden = np.zeros(n, int), np.zeros(n, int)
    x = np.log(np.clip(score, 1e-6, 1 - 1e-6) / (1 - np.clip(score, 1e-6, 1 - 1e-6))).reshape(-1, 1)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        if y[m].sum() in (0, m.sum()):
            continue
        lr = LogisticRegression(max_iter=1000).fit(x[m], y[m])
        platt[i] = int(lr.predict_proba(x[i:i + 1])[0, 1] >= 0.5)
        # Youden J on the held-in fold
        ths = np.unique(score[m])
        best, bt = -1, 0.5
        for t in ths:
            p = (score[m] >= t).astype(int)
            se = p[y[m] == 1].mean(); sp = 1 - p[y[m] == 0].mean()
            if se + sp - 1 > best:
                best, bt = se + sp - 1, t
        youden[i] = int(score[i] >= bt)
    return platt, youden


def bal(pred, y):
    return 0.5 * (pred[y == 1].mean() + 1 - pred[y == 0].mean())


def main():
    out = ["# Expert-algorithm IRR vs expert-expert IRR, and recalibrating the gate\n",
           "An algorithm can agree with each expert *better than experts agree with each other*, because two ",
           "noisy raters compound two error sources while an accurate algorithm carries one. If experts were ",
           "(truth + independent noise), an algorithm at the truth would score **κ_ae ≈ √κ_ee**. Expert errors ",
           "are correlated (shared training, shared blind spots), which inflates κ_ee and makes √κ_ee a ",
           "**conservative** target.\n",
           "Thresholds and Platt coefficients are fitted **leave-one-out**; no EEG informs its own call. ",
           "Morgoth's AUROC is threshold-free and unchanged by recalibration — only the operating point moves.\n"]

    for f, name in FILES:
        d = pd.read_excel(f"{SC}/{f}")
        ex = [c for c in d.columns if c.startswith("expert_")]
        E = d[ex].values.astype(int)
        y = d["majority"].values.astype(int)
        s = d["M_pred"].values.astype(float)

        kee = ee_kappas(E)
        auc = roc_auc_score(y, s)
        shipped = d["M_pred_class"].values.astype(int)
        platt, youden = loo_calls(s, y)

        # expert-vs-leave-one-out-consensus, the human reference point
        eb = []
        for i in range(E.shape[1]):
            oth = np.delete(E, i, axis=1)
            cons = (oth.mean(1) >= 0.5).astype(int)
            if cons.sum() in (0, len(cons)):
                continue
            eb.append(bal(E[:, i], cons))

        out.append(f"\n## {name}  (n = {len(d)} EEGs, {len(ex)} experts, prevalence {y.mean():.2f})\n")
        out.append(f"**Morgoth AUROC vs expert majority: {auc:.3f}** (threshold-free).\n")
        out.append("| calls | bal. accuracy vs majority | sens | spec | κ vs each expert (median [IQR]) |")
        out.append("|---|---|---|---|---|")
        for lab, p in [("Morgoth, shipped threshold", shipped),
                       ("Morgoth, LOO Platt @0.5", platt),
                       ("Morgoth, LOO Youden threshold", youden)]:
            k = ae_kappas(p, E)
            out.append(f"| {lab} | {bal(p,y):.3f} | {p[y==1].mean():.3f} | {1-p[y==0].mean():.3f} | "
                       f"{np.median(k):.3f} [{np.percentile(k,25):.3f}–{np.percentile(k,75):.3f}] |")
        out.append(f"| *average expert vs consensus* | *{np.mean(eb):.3f}* | — | — | "
                   f"*{np.median(kee):.3f} [{np.percentile(kee,25):.3f}–{np.percentile(kee,75):.3f}]* (expert–expert) |")

        ky = ae_kappas(youden, E)
        boot = [np.median(rng.choice(ky, len(ky))) - np.median(rng.choice(kee, len(kee))) for _ in range(2000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        out.append(f"\n- expert–expert κ median **{np.median(kee):.3f}**; attenuation benchmark √κ_ee = "
                   f"**{np.sqrt(max(np.median(kee),0)):.3f}**")
        out.append(f"- Morgoth (LOO Youden) vs each expert: κ median **{np.median(ky):.3f}**")
        out.append(f"- difference κ_ae − κ_ee = **{np.median(ky)-np.median(kee):+.3f}** "
                   f"[95% CI {lo:+.3f}, {hi:+.3f}] → "
                   f"{'**ea-IRR exceeds ee-IRR**' if lo > 0 else 'not distinguishable from zero'}")

    out.append("\n## Reading this\n")
    out.append("Recalibration cannot change ranking (AUROC is fixed); it changes *what we do with the ranking*. ")
    out.append("Reporting only the shipped threshold understates the system that can actually be deployed. ")
    out.append("Reporting only the LOO-Youden point risks flattering it — so both are given, and the Youden ")
    out.append("threshold is chosen without the EEG it is applied to.\n")
    out.append("κ_ae > κ_ee, if it holds, is a substantive claim: the algorithm agrees with the average expert ")
    out.append("better than two experts agree with each other. It is *not* a claim that the algorithm is right ")
    out.append("and the experts wrong — consensus is not truth (see docs/validation_plan.md V4).")

    txt = "\n".join(out) + "\n"
    Path("results/ea_irr_and_recalibration.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
