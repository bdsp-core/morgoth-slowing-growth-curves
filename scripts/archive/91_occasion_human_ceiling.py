"""OccasionNoise: the human ceiling for slowing, and Morgoth's position relative to it.

100 EEGs, 18 experts, recording-level votes on focal/generalized x epileptiform/non-epileptiform.
Non-epileptiform == slowing:  FN = focal slowing, GN = generalized slowing.
Part I / Part II = the same experts re-reading the same EEGs -> WITHIN-rater test-retest.

Also reads Morgoth's own predictions on these EEGs (`Morgoth_results/*Slowing*_Morgoth_experts.xlsx`),
which ship with the dataset: `M_pred` (continuous), `M_pred_class` (thresholded), `majority` (expert
majority), and one column per expert.

Nothing here involves this paper's normative model -- this is the human ceiling alone, plus the Morgoth
baseline. Our model is scored against these same targets in Phase A (see docs/phaseA_preregistration.md),
which must not be run until the predictions in that document are written down.

Run: python scripts/91_occasion_human_ceiling.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score

SC = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
      "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/occ")
AXES = {"FS": "focal epileptiform", "FN": "FOCAL SLOWING",
        "GS": "generalized epileptiform", "GN": "GENERALIZED SLOWING"}


def fleiss(counts):
    n = counts.sum(1); keep = n >= 2
    counts, n = counts[keep], n[keep]
    P = ((counts ** 2).sum(1) - n) / (n * (n - 1))
    p = counts.sum(0) / counts.sum()
    Pe = (p ** 2).sum()
    return (P.mean() - Pe) / (1 - Pe)


def main():
    xl = pd.ExcelFile(f"{SC}/Occasion.xlsx")
    db, files = xl.parse("DB"), xl.parse("Files")
    out = ["# OccasionNoise — the human ceiling for slowing\n",
           f"100 EEGs, {db.uid.nunique()} experts, 15–18 raters per EEG. Balanced by design "
           "(20 focal-epileptiform / 20 generalized-epileptiform / 20 focal-non-epileptiform / "
           "20 generalized-non-epileptiform / 16 normal / 4 normal-variant), so AUROC and κ transfer but "
           "prevalence-dependent metrics (PPV) do not.\n"]

    out += ["## Between-rater agreement (Part I)\n",
            "| axis | prevalence | Fleiss κ | pairwise Cohen κ median [IQR] |", "|---|---|---|---|"]
    for ax, nm in AXES.items():
        c = db.pivot_table(index="fid", columns="uid", values=f"r1.{ax}")
        pos, tot = c.sum(1).values, c.notna().sum(1).values
        fk = fleiss(np.c_[tot - pos, pos])
        ks, us = [], list(c.columns)
        for i in range(len(us)):
            for j in range(i + 1, len(us)):
                a, b = c[us[i]], c[us[j]]
                ok = a.notna() & b.notna()
                if ok.sum() >= 20 and a[ok].nunique() > 1 and b[ok].nunique() > 1:
                    ks.append(cohen_kappa_score(a[ok], b[ok]))
        out.append(f"| {nm} | {db[f'r1.{ax}'].mean():.3f} | {fk:.3f} | {np.median(ks):.3f} "
                   f"[{np.percentile(ks,25):.3f}–{np.percentile(ks,75):.3f}] |")

    out += ["\n## Within-rater: the SAME expert re-reading the SAME EEG (Part I vs Part II)\n",
            "| axis | raw agreement | Cohen κ |", "|---|---|---|"]
    b = db.dropna(subset=["r2.FN"])
    for ax, nm in AXES.items():
        a1, a2 = b[f"r1.{ax}"].astype(int), b[f"r2.{ax}"].astype(int)
        out.append(f"| {nm} | {(a1==a2).mean():.3f} | {cohen_kappa_score(a1,a2):.3f} |")
    out.append(f"\n(n = {len(b)} repeat reads by {b.uid.nunique()} experts)")

    out += ["\n## Expert vs consensus (leave-one-out majority of the other raters)\n",
            "| axis | sensitivity | specificity | balanced accuracy | κ |", "|---|---|---|---|---|"]
    ceiling = {}
    for ax in ["FN", "GN"]:
        c = db.pivot_table(index="fid", columns="uid", values=f"r1.{ax}")
        se, sp, ba, kp = [], [], [], []
        for u in c.columns:
            cons = (c.drop(columns=[u]).mean(1) >= 0.5).astype(int)
            mine, ok = c[u], c[u].notna()
            y, yh = cons[ok].values, mine[ok].values.astype(int)
            if y.sum() in (0, len(y)):
                continue
            s1, s0 = yh[y == 1].mean(), 1 - yh[y == 0].mean()
            se.append(s1); sp.append(s0); ba.append((s1 + s0) / 2); kp.append(cohen_kappa_score(y, yh))
        ceiling[ax] = (np.mean(se), np.mean(sp), np.mean(ba))
        out.append(f"| {AXES[ax]} | {np.mean(se):.3f} | {np.mean(sp):.3f} | "
                   f"**{np.mean(ba):.3f}** (range {min(ba):.3f}–{max(ba):.3f}) | {np.mean(kp):.3f} |")

    out += ["\n## Signed clinical report vs the expert panel\n",
            "Fraction of experts marking each axis, by the category assigned from the signed report:\n"]
    cs = xl.parse("Consensus").merge(files, on="fid")
    g = cs.groupby("category")[["Average of r1.FN", "Average of r1.GN"]].mean().round(3)
    out.append("| signed-report category | experts marking focal slowing | experts marking gen. slowing |")
    out.append("|---|---|---|")
    for k, r in g.iterrows():
        out.append(f"| {k} | {r['Average of r1.FN']:.3f} | {r['Average of r1.GN']:.3f} |")
    out.append("\nOn EEGs the **signed report** called focal non-epileptiform, only "
               f"{g.loc['Focal non-epileptiform','Average of r1.FN']:.1%} of experts marked focal slowing. "
               "This bounds every 'agreement with the report' number in the paper.")

    out += ["\n## Morgoth (the gate) against the same expert majority\n",
            "| axis | AUROC vs majority | Morgoth's own threshold | expert-vs-consensus |", "|---|---|---|---|"]
    for f, ax in [("FocalSlowingOutput_Morgoth_experts.xlsx", "FN"),
                  ("GenSlowingOutput_Morgoth_experts.xlsx", "GN")]:
        d = pd.read_excel(f"{SC}/results/{f}")
        y = d["majority"].values
        auc = roc_auc_score(y, d.M_pred.values)
        ms = d.M_pred_class.values
        se, sp = ms[y == 1].mean(), 1 - ms[y == 0].mean()
        _, _, cba = ceiling[ax]
        out.append(f"| {AXES[ax]} | **{auc:.3f}** | bal-acc {(se+sp)/2:.3f} (sens {se:.3f}, spec {sp:.3f}) "
                   f"| bal-acc {cba:.3f} |")
    out.append("\nMorgoth **ranks** better than the average expert but its **thresholded operating point** is "
               "far below them: near-perfect specificity, badly deficient sensitivity. Ranking quality and "
               "operating-point calibration are different claims and must be reported separately.")

    txt = "\n".join(out) + "\n"
    Path("results/occasion_human_ceiling.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
