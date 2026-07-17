#!/usr/bin/env python3
"""SECTION 0 — Morgoth EEG-level detection of focal & generalized slowing, vs the expert panel.

Multi-scored panel (OccasionNoise, N=100 EEGs, 18 raters). Focal (FN) and generalized (GN) slowing are
SEPARATE binary axes — an EEG can be positive on both (confirmed: raters mark both on 29/100 EEGs) — so we
score each axis independently, exactly as Morgoth's two independent EEG-level sigmoids emit them.

For each axis:
  * ground truth  = the panel MAJORITY vote (>=50% of the raters who read that EEG call it positive).
  * Morgoth       = M_pred (continuous gate probability) -> ROC (AUROC) and PRC (average precision).
  * each expert   = one operating point (1-specificity, sensitivity) against the LEAVE-ONE-OUT consensus of
                    the OTHER raters, so no rater is scored against a consensus containing their own vote.
  * "% of experts UNDER the curve" = the fraction of expert operating points that lie on/below Morgoth's ROC
                    (Morgoth's sensitivity at that rater's false-positive rate is >= the rater's) — i.e. how
                    much of the human panel Morgoth's curve dominates.

Writes:  figures/story/s0_occasion_{focal,generalized}.png   results/story/s0_occasion.md
Run:     PYTHONPATH=src MPLBACKEND=Agg python3 scripts/40_section0_detection_vs_experts.py

MoE (the larger panel, ~18-21 experts, band-resolved) is NOT included yet: its per-rater labels are not
committed (they live only in ephemeral scratchpad CSVs). Add MoE here once those labels are re-supplied.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

AX = [("focal", "FN", "#c8443c"), ("generalized", "GN", "#2c7fb8")]
FIGDIR = Path("figures/story"); RESDIR = Path("results/story")


def expert_points(V, col):
    """One operating point per rater vs the LEAVE-ONE-OUT majority of the OTHER raters (the scored rater's
    own votes are excluded from the consensus). Returns rater -> dict(fpr, tpr, recall, precision)."""
    wide = V.pivot_table(index="fid", columns="rater", values=col)      # NaN where a rater didn't read
    pts = {}
    for r in wide.columns:
        others = wide.drop(columns=r)                                   # <-- LOO: drop this rater
        me = wide[r]
        rows = me.notna() & others.notna().any(axis=1)
        if rows.sum() < 5:
            continue
        cons = (others.loc[rows].mean(axis=1) >= 0.5).astype(int)       # consensus of the OTHER raters only
        mv = me[rows].astype(int)
        tp = int(((mv == 1) & (cons == 1)).sum()); fp = int(((mv == 1) & (cons == 0)).sum())
        fn = int(((mv == 0) & (cons == 1)).sum()); tn = int(((mv == 0) & (cons == 0)).sum())
        if (tp + fn) == 0 or (fp + tn) == 0:
            continue
        pts[r] = {"fpr": fp / (fp + tn), "tpr": tp / (tp + fn),
                  "recall": tp / (tp + fn), "precision": (tp / (tp + fp)) if (tp + fp) else np.nan}
    return pts


def frac_under_roc(fpr, tpr, pts):
    if not pts:
        return np.nan, {}
    flags = {r: float(np.interp(p["fpr"], fpr, tpr)) >= p["tpr"] - 1e-9 for r, p in pts.items()}
    return sum(flags.values()) / len(flags), flags


def frac_under_pr(prec, rec, pts):
    """Morgoth precision at each expert's recall (interp on recall-sorted PR curve); expert 'under' if
    Morgoth's precision there >= the expert's precision."""
    o = np.argsort(rec); rs, ps = np.asarray(rec)[o], np.asarray(prec)[o]
    valid = {r: p for r, p in pts.items() if np.isfinite(p["precision"])}
    if not valid:
        return np.nan, {}
    flags = {r: float(np.interp(p["recall"], rs, ps)) >= p["precision"] - 1e-9 for r, p in valid.items()}
    return sum(flags.values()) / len(flags), flags


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True); RESDIR.mkdir(parents=True, exist_ok=True)
    M = pd.read_parquet("data/derived/occasion_morgoth_preds.parquet")
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    md = ["# Section 0 — Morgoth EEG-level detection vs the expert panel (OccasionNoise, N=100, 18 raters)\n",
          "Focal and generalized slowing are scored as **separate binary axes** (they co-occur — 29/100 EEGs "
          "have a rater marking both). Ground truth = panel majority; each expert is an operating point vs the "
          "leave-one-out consensus of the others.\n",
          "| axis | n pos / N | AUROC | AP | experts | % under ROC | % under PR |",
          "|---|---|---|---|---|---|---|"]

    for name, ax, color in AX:
        col = f"r1.{ax}"
        v = V.dropna(subset=[col])
        vote = v.pivot_table(index="fid", columns="rater", values=col)
        y = (vote.mean(axis=1) >= 0.5).astype(int)                       # panel-majority ground truth
        mp = M[M.axis == ax].set_index("fid").M_pred
        idx = y.index.intersection(mp.index)
        y = y.loc[idx].values; s = mp.loc[idx].values
        auc = roc_auc_score(y, s); ap = average_precision_score(y, s)
        fpr, tpr, _ = roc_curve(y, s)
        prec, rec, _ = precision_recall_curve(y, s)
        pts = expert_points(v, col)
        pu_roc, flags_roc = frac_under_roc(fpr, tpr, pts)
        pu_pr, flags_pr = frac_under_pr(prec, rec, pts)
        md.append(f"| {name} | {int(y.sum())}/{len(y)} | {auc:.3f} | {ap:.3f} | {len(pts)} | "
                  f"**{100*pu_roc:.0f}%** | **{100*pu_pr:.0f}%** |")

        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.6))
        # ---- ROC ----
        a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
        a0.plot(fpr, tpr, color=color, lw=2.4, label=f"Morgoth (AUROC {auc:.2f})")
        nu = sum(flags_roc.values())
        for r, p in pts.items():
            u = flags_roc.get(r, False)
            a0.plot(p["fpr"], p["tpr"], "o", ms=6, mfc=("#888" if u else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a0.plot([], [], "o", mfc="#888", mec="k", label=f"expert under curve ({nu})")
        a0.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"expert above curve ({len(pts)-nu})")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity")
        a0.set_title(f"{name.upper()} — ROC\n{100*pu_roc:.0f}% of {len(pts)} experts under Morgoth", fontsize=10)
        a0.legend(frameon=False, fontsize=7.5, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
        # ---- PRC (with expert operating points) ----
        base = y.mean()
        a1.plot(rec, prec, color=color, lw=2.4, label=f"Morgoth (AP {ap:.2f})")
        a1.axhline(base, ls="--", color="#bbb", lw=1, label=f"prevalence {base:.2f}")
        npu = sum(flags_pr.values())
        for r, p in pts.items():
            if not np.isfinite(p["precision"]):
                continue
            u = flags_pr.get(r, False)
            a1.plot(p["recall"], p["precision"], "o", ms=6, mfc=("#888" if u else "#e41a1c"),
                    mec="k", mew=.4, alpha=.85)
        a1.plot([], [], "o", mfc="#888", mec="k", label=f"expert under PR ({npu})")
        a1.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"expert above PR ({len(flags_pr)-npu})")
        a1.set_xlabel("recall (sensitivity)"); a1.set_ylabel("precision")
        a1.set_title(f"{name.upper()} — PRC\n{100*pu_pr:.0f}% of {len(flags_pr)} experts under Morgoth", fontsize=10)
        a1.legend(frameon=False, fontsize=7.5, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"Morgoth EEG-level detection of {name} slowing vs {len(pts)} experts "
                     f"(OccasionNoise) — experts scored vs leave-one-out consensus", fontsize=10.5)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(FIGDIR / f"s0_occasion_{name}.png", dpi=150); plt.close(fig)

    md.append("\n*MoE (larger, band-resolved panel) pending re-supply of its per-rater labels.*")
    (RESDIR / "s0_occasion.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nwrote figures/story/s0_occasion_*.png + results/story/s0_occasion.md")


if __name__ == "__main__":
    main()
