#!/usr/bin/env python3
"""OccasionNoise — Morgoth vs a Morgoth-FREE classifier vs the expert panel, ON THE SAME AXES.

One ROC+PRC figure per axis (focal, generalized) overlaying:
  * Morgoth's EEG-level gate probability  (occasion_morgoth_preds M_pred)
  * our best Morgoth-free classifier      (focal: all-stage localized; generalized: W+N1 amount; LOO-CV)
  * the 18 experts as operating points     (vs leave-one-out consensus)
Reports % of experts under EACH curve. Ground truth = panel majority.

Writes figures/story/s0_occasion_combined_{focal,generalized}.png + results/story/s0_occasion_combined.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/51_occasion_combined.py
"""
from __future__ import annotations
import importlib.util, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

m49 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py"))
importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py").loader.exec_module(m49)
m46 = m49.m46
FIG = Path("figures/story"); RES = Path("results/story")
C_MORG, C_OURS = "#6a3d9a", "#e6550d"


def build_T(stageset):
    m49.STAGESET = stageset                       # threads share module state
    F = pd.read_parquet("data/derived/occasion_features.parquet")
    age = F[(F.stage == "W") & (F.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    fids = sorted(int(x) for x in F.fid.unique())
    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = [r for r in ex.map(m49.per_fid, [(i, float(age.get(i, np.nan))) for i in fids]) if r]
    T = pd.DataFrame(rows).set_index("fid"); T["age"] = age.reindex(T.index)
    return T


def under_curve_roc(fpr, tpr, pts):
    return {r: float(np.interp(p["fpr"], fpr, tpr)) >= p["tpr"] - 1e-9 for r, p in pts.items()}


def under_curve_pr(prec, rec, pts):
    o = np.argsort(rec); rs, ps = np.asarray(rec)[o], np.asarray(prec)[o]
    return {r: float(np.interp(p["recall"], rs, ps)) >= p["precision"] - 1e-9
            for r, p in pts.items() if np.isfinite(p["precision"])}


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    T_all = build_T(["W", "N1", "N2", "N3", "REM"])
    foc_cols = [c for c in T_all.columns if c.startswith(("peak_", "foc_", "asym_", "peak_region"))] + ["age"]
    T_wn1 = build_T(["W", "N1"])
    amt_cols = [c for c in T_wn1.columns if c.startswith("amt_")] + ["age"]
    M = pd.read_parquet("data/derived/occasion_morgoth_preds.parquet")
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")

    md = ["# OccasionNoise — Morgoth vs Morgoth-FREE vs experts, same axes\n",
          "| axis | Morgoth AUROC | ours AUROC | experts under Morgoth (ROC/PR) | experts under OURS (ROC/PR) |",
          "|---|---|---|---|---|"]

    for name, mx, T, cols, color in [("focal", "FN", T_all, foc_cols, "#c8443c"),
                                     ("generalized", "GN", T_wn1, amt_cols, "#2c7fb8")]:
        wide = V.dropna(subset=[f"r1.{mx}"]).pivot_table(index="fid", columns="rater", values=f"r1.{mx}")
        y = (wide.mean(axis=1) >= 0.5).astype(int)
        pts = m46.expert_points(wide)
        s_m = M[M.axis == mx].set_index("fid").M_pred.reindex(y.index)
        p_o = pd.Series(m46.loo_proba(T.reindex(y.index)[cols], y.values), index=y.index)

        curves = {}
        for tag, s in [("Morgoth", s_m.values), ("ours", p_o.values)]:
            fpr, tpr, _ = roc_curve(y, s); prec, rec, _ = precision_recall_curve(y, s)
            curves[tag] = dict(auc=roc_auc_score(y, s), ap=average_precision_score(y, s),
                               fpr=fpr, tpr=tpr, prec=prec, rec=rec,
                               ur=under_curve_roc(fpr, tpr, pts), up=under_curve_pr(prec, rec, pts))
        cm, co = curves["Morgoth"], curves["ours"]
        md.append(f"| {name} | {cm['auc']:.3f} | {co['auc']:.3f} | "
                  f"{100*np.mean(list(cm['ur'].values())):.0f}% / {100*np.mean(list(cm['up'].values())):.0f}% | "
                  f"**{100*np.mean(list(co['ur'].values())):.0f}% / {100*np.mean(list(co['up'].values())):.0f}%** |")

        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11.5, 4.8))
        a0.plot([0, 1], [0, 1], "--", color="#ccc", lw=1)
        a0.plot(cm["fpr"], cm["tpr"], color=C_MORG, lw=2.4, label=f"Morgoth (AUROC {cm['auc']:.2f}, {100*np.mean(list(cm['ur'].values())):.0f}% under)")
        a0.plot(co["fpr"], co["tpr"], color=C_OURS, lw=2.4, label=f"Morgoth-free (AUROC {co['auc']:.2f}, {100*np.mean(list(co['ur'].values())):.0f}% under)")
        for r, p in pts.items():
            a0.plot(p["fpr"], p["tpr"], "o", ms=6, mfc="#999", mec="k", mew=.4, alpha=.8)
        a0.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity"); a0.set_title(f"{name.upper()} — ROC", fontsize=11)
        a0.legend(frameon=False, fontsize=8, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)

        a1.axhline(y.mean(), ls="--", color="#ccc", lw=1, label=f"prevalence {y.mean():.2f}")
        a1.plot(cm["rec"], cm["prec"], color=C_MORG, lw=2.4, label=f"Morgoth (AP {cm['ap']:.2f}, {100*np.mean(list(cm['up'].values())):.0f}% under)")
        a1.plot(co["rec"], co["prec"], color=C_OURS, lw=2.4, label=f"Morgoth-free (AP {co['ap']:.2f}, {100*np.mean(list(co['up'].values())):.0f}% under)")
        for r, p in pts.items():
            if np.isfinite(p["precision"]):
                a1.plot(p["recall"], p["precision"], "o", ms=6, mfc="#999", mec="k", mew=.4, alpha=.8)
        a1.set_xlabel("recall"); a1.set_ylabel("precision"); a1.set_title(f"{name.upper()} — PRC", fontsize=11)
        a1.legend(frameon=False, fontsize=8, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"OccasionNoise {name} slowing — Morgoth vs a Morgoth-FREE classifier vs {len(pts)} experts "
                     f"(LOO-CV; experts vs LOO consensus)", fontsize=10.5)
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        fig.savefig(FIG / f"s0_occasion_combined_{name}.png", dpi=150); plt.close(fig)

    (RES / "s0_occasion_combined.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_occasion_combined_*.png + results/story/s0_occasion_combined.md")


if __name__ == "__main__":
    main()
