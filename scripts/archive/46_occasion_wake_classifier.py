#!/usr/bin/env python3
"""Can a Morgoth-FREE classifier on the AWAKE segments beat the experts on OccasionNoise?

Two independent detectors — FOCAL slowing and GENERALIZED slowing — built ONLY from the spectral features of
the WAKE (stage='W') segments of each OccasionNoise EEG (occasion_features.parquet, keyed by fid, same key as
the expert votes, so no crosswalk needed). No Morgoth anywhere.

  generalized detector  <- whole-head wake slowing amount (log/rel band powers, ratios) + age
  focal detector        <- left-right ASYMMETRY of wake slowing (temporal & parasagittal) + amount + age

Each is an L2 logistic regression, evaluated LEAVE-ONE-OUT so the ROC/PRC is honest out-of-fold on N=100.
Ground truth = panel majority (FN=focal, GN=generalized). Each of the 18 experts is an operating point vs the
leave-one-out consensus of the others (their own vote excluded). Headline = % of experts UNDER our ROC and PR.

Writes figures/story/s0_occasion_ours_{focal,generalized}.png + results/story/s0_occasion_ours.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/46_occasion_wake_classifier.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

FIG = Path("figures/story"); RES = Path("results/story")
AMOUNT = ["log_delta", "log_theta", "rel_delta", "rel_theta", "TAR", "DAR", "DTR", "low_freq_rel", "rel_alpha"]
# homologous left|right bipolar channel pairs — a focal slow focus is LOCAL, so the max asymmetry across
# pairs localizes it wherever it sits (the 2 region-aggregates washed it out).
CHPAIRS = [("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"), ("T5-O1", "T6-O2"),
           ("Fp1-F3", "Fp2-F4"), ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("P3-O1", "P4-O2")]
ASYM_F = ["log_delta", "rel_delta", "TAR", "DAR"]


def wake_features():
    F = pd.read_parquet("data/derived/occasion_features.parquet")
    W = F[F.stage == "W"]
    wh = W[W.region == "whole_head"].set_index("fid")
    age = wh["age"]
    # generalized: whole-head amount + age
    Xg = wh[AMOUNT].copy(); Xg["age"] = age
    # focal: for each slowing feature, the MAX |L-R| across all homologous channel pairs (localizes a focal
    # focus anywhere), the single largest asymmetry, and whole-head amount + age as context.
    reg = {r: W[W.region == r].set_index("fid").reindex(wh.index) for r in set(sum(CHPAIRS, ()))}
    Xf = pd.DataFrame(index=wh.index)
    per_pair = {}
    for ft in ASYM_F:
        cols = []
        for L, R in CHPAIRS:
            if L in reg and R in reg:
                a = (reg[L][ft] - reg[R][ft]).abs()
                per_pair[f"{ft}_{L}"] = a; cols.append(a)
        M = pd.concat(cols, axis=1)
        Xf[f"asymmax_{ft}"] = M.max(axis=1)
        Xf[f"asymmean_{ft}"] = M.mean(axis=1)          # diffuse vs one-focus contrast
    Xf["asym_overall_max"] = pd.concat(list(per_pair.values()), axis=1).max(axis=1)
    for ft in ["log_delta", "rel_delta", "TAR"]:
        Xf[f"wh_{ft}"] = wh[ft]
    Xf["age"] = age
    return Xg, Xf


def loo_proba(X, y):
    """out-of-fold predicted probability, L2 logistic, standardized, class-balanced."""
    X = X.fillna(X.median()).values; y = np.asarray(y)
    p = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000)
        m.fit(sc.transform(X[tr]), y[tr])
        p[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    return p


def expert_points(wide):
    pts = {}
    for r in wide.columns:
        others = wide.drop(columns=r); me = wide[r]
        rows = me.notna() & others.notna().any(axis=1)
        if rows.sum() < 5:
            continue
        cons = (others.loc[rows].mean(axis=1) >= 0.5).astype(int); mv = me[rows].astype(int)
        tp = int(((mv == 1) & (cons == 1)).sum()); fp = int(((mv == 1) & (cons == 0)).sum())
        fn = int(((mv == 0) & (cons == 1)).sum()); tn = int(((mv == 0) & (cons == 0)).sum())
        if (tp + fn) == 0 or (fp + tn) == 0:
            continue
        pts[r] = {"fpr": fp/(fp+tn), "tpr": tp/(tp+fn), "recall": tp/(tp+fn),
                  "precision": (tp/(tp+fp)) if (tp+fp) else np.nan}
    return pts


def under_roc(fpr, tpr, pts):
    f = {r: float(np.interp(p["fpr"], fpr, tpr)) >= p["tpr"]-1e-9 for r, p in pts.items()}
    return (sum(f.values())/len(f) if f else np.nan), f


def under_pr(prec, rec, pts):
    o = np.argsort(rec); rs, ps = np.asarray(rec)[o], np.asarray(prec)[o]
    v = {r: p for r, p in pts.items() if np.isfinite(p["precision"])}
    f = {r: float(np.interp(p["recall"], rs, ps)) >= p["precision"]-1e-9 for r, p in v.items()}
    return (sum(f.values())/len(f) if f else np.nan), f


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    Xg, Xf = wake_features()
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    md = ["# Can a Morgoth-FREE wake-segment classifier beat the experts? (OccasionNoise, N=100)\n",
          "L2 logistic on WAKE spectral features only, leave-one-out CV. Ground truth = panel majority; each "
          "expert an operating point vs the leave-one-out consensus of the others.\n",
          "| axis | features | n pos/N | AUROC (LOO) | AP | experts | % under ROC | % under PR |",
          "|---|---|---|---|---|---|---|---|"]

    for name, ax, X, color, desc in [("focal", "FN", Xf, "#c8443c", "wake L-R asymmetry + amount"),
                                     ("generalized", "GN", Xg, "#2c7fb8", "wake whole-head amount")]:
        wide = V.dropna(subset=[f"r1.{ax}"]).pivot_table(index="fid", columns="rater", values=f"r1.{ax}")
        y = (wide.mean(axis=1) >= 0.5).astype(int)
        X = X.reindex(y.index)
        p = loo_proba(X, y.values)
        auc = roc_auc_score(y, p); ap = average_precision_score(y, p)
        fpr, tpr, _ = roc_curve(y, p); prec, rec, _ = precision_recall_curve(y, p)
        pts = expert_points(wide)
        pu_roc, fr = under_roc(fpr, tpr, pts); pu_pr, fp = under_pr(prec, rec, pts)
        md.append(f"| {name} | {desc} | {int(y.sum())}/{len(y)} | {auc:.3f} | {ap:.3f} | {len(pts)} | "
                  f"**{100*pu_roc:.0f}%** | **{100*pu_pr:.0f}%** |")

        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.6))
        a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
        a0.plot(fpr, tpr, color=color, lw=2.4, label=f"our wake classifier (AUROC {auc:.2f})")
        for r, pp in pts.items():
            a0.plot(pp["fpr"], pp["tpr"], "o", ms=6, mfc=("#888" if fr.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a0.plot([], [], "o", mfc="#888", mec="k", label=f"under curve ({sum(fr.values())})")
        a0.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above curve ({len(pts)-sum(fr.values())})")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity")
        a0.set_title(f"{name.upper()} — ROC\n{100*pu_roc:.0f}% of {len(pts)} experts under our curve", fontsize=10)
        a0.legend(frameon=False, fontsize=7.5, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
        a1.plot(rec, prec, color=color, lw=2.4, label=f"our wake classifier (AP {ap:.2f})")
        a1.axhline(y.mean(), ls="--", color="#bbb", lw=1, label=f"prevalence {y.mean():.2f}")
        for r, pp in pts.items():
            if not np.isfinite(pp["precision"]):
                continue
            a1.plot(pp["recall"], pp["precision"], "o", ms=6, mfc=("#888" if fp.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a1.plot([], [], "o", mfc="#888", mec="k", label=f"under PR ({sum(fp.values())})")
        a1.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above PR ({len(fp)-sum(fp.values())})")
        a1.set_xlabel("recall"); a1.set_ylabel("precision")
        a1.set_title(f"{name.upper()} — PRC\n{100*pu_pr:.0f}% of {len(fp)} experts under our curve", fontsize=10)
        a1.legend(frameon=False, fontsize=7.5, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"Morgoth-FREE wake-segment {name} detector vs {len(pts)} experts (OccasionNoise, LOO-CV)",
                     fontsize=10.5)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(FIG / f"s0_occasion_ours_{name}.png", dpi=150); plt.close(fig)

    (RES / "s0_occasion_ours.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_occasion_ours_*.png + results/story/s0_occasion_ours.md")


if __name__ == "__main__":
    main()
