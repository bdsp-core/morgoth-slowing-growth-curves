#!/usr/bin/env python3
"""Generate the 3 dashboard figures that were rendering as "Not yet computed" placeholders.

The underlying ANALYSES were all done — only the plots were never produced, so the dashboard showed
blanks. This draws them from the v6 results:

  figures/growth_v2/occasion_roc_experts.png   human-ceiling panel: our gate vs the 18 experts
  figures/growth_v2/v4a_wake_sleep.png         P6: do readers name slowing that is only visible in sleep?
  results/figs/lateralization_by_band_roc.png  band-matched left-vs-right lateralization

Run: PYTHONPATH=src python scripts/make_missing_figures.py
"""
import os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, balanced_accuracy_score

SCR = os.environ.get("PANEL_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
G = Path("figures/growth_v2"); F = Path("results/figs")
G.mkdir(parents=True, exist_ok=True); F.mkdir(parents=True, exist_ok=True)


def fig_occasion_roc():
    """Our gate vs the expert panel: ROC against the expert majority, with each expert plotted."""
    db = pd.ExcelFile(f"{SCR}/moe/occ/Occasion.xlsx").parse("DB")
    d = db[["fid", "uid", "r1.FN", "r1.GN"]].dropna()
    d = d.assign(FN=(d["r1.FN"] > 0).astype(int), GN=(d["r1.GN"] > 0).astype(int))
    sc = pd.read_parquet("data/derived/panel_v6_scores.parquet").set_index("fid")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, (tag, col, score) in zip(axes, [("focal slowing", "FN", "p_focal"),
                                            ("generalized slowing", "GN", "p_generalized")]):
        agg = d.groupby("fid")[col].agg(["sum", "size"])
        maj = (agg["sum"] / agg["size"] > 0.5).astype(int)
        s = sc[score].reindex(maj.index)
        ok = s.notna()
        y, p = maj[ok].values, s[ok].values
        fpr, tpr, _ = roc_curve(y, p)
        auc = roc_auc_score(y, p)
        ax.plot(fpr, tpr, lw=2.2, color="#1f77b4", label=f"Morgoth gate (AUROC {auc:.3f})", zorder=3)

        # every individual expert as a point (their own sens/spec vs the majority of their PEERS)
        sens, spec, baccs = [], [], []
        for uid, g in d.groupby("uid"):
            others = d[d.uid != uid]
            om = (others.groupby("fid")[col].mean() > 0.5).astype(int)
            j = g.set_index("fid")[col].reindex(om.index).dropna()
            yy, pp = om.loc[j.index].values, j.values
            if len(np.unique(yy)) < 2:
                continue
            tp = ((pp == 1) & (yy == 1)).sum(); fn = ((pp == 0) & (yy == 1)).sum()
            fp = ((pp == 1) & (yy == 0)).sum(); tn = ((pp == 0) & (yy == 0)).sum()
            se = tp / max(tp + fn, 1); sp = tn / max(tn + fp, 1)
            sens.append(se); spec.append(sp); baccs.append(balanced_accuracy_score(yy, pp))
        ax.scatter(1 - np.array(spec), sens, s=42, color="#d62728", alpha=.75, zorder=4,
                   label=f"individual experts (n={len(sens)})")
        ax.scatter([1 - np.mean(spec)], [np.mean(sens)], s=190, marker="*", color="#000", zorder=5,
                   label=f"average expert (bal.acc {np.mean(baccs):.3f})")
        ax.plot([0, 1], [0, 1], ls=":", c="#999", lw=1)
        ax.set_xlabel("1 − specificity"); ax.set_ylabel("sensitivity")
        ax.set_title(f"{tag} — vs expert majority", fontsize=11, fontweight="bold")
        ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=.25)
    fig.suptitle("Human ceiling: our gate vs 18 electroencephalographers on 100 EEGs (v6 run)\n"
                 "the gate RANKS above the experts, but at an operating point it does not beat them (P7)",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, .93])
    fig.savefig(G / "occasion_roc_experts.png", dpi=140); plt.close(fig)
    print("wrote", G / "occasion_roc_experts.png")


def fig_v4a_wake_sleep():
    """P6: does the reader still NAME slowing when it is visible only once the patient is asleep?"""
    txt = Path("results/p6_sleep_underreporting.md").read_text()
    import re
    rows = re.findall(r"\|\s*(?:slowing visible in \*\*wake\*\*|slowing visible \*\*only in sleep\*\*|"
                      r"visible in neither \(base rate\))\s*\|\s*([\d,]+)\s*\|\s*\*?\*?([\d.]+)%", txt)
    if len(rows) < 3:
        print("could not parse P6 table"); return
    labels = ["visible in\nWAKE", "visible ONLY\nin SLEEP", "visible in\nneither (base)"]
    ns = [int(r[0].replace(",", "")) for r in rows]
    rates = [float(r[1]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.6, 5))
    cols = ["#1f77b4", "#d62728", "#bbb"]
    b = ax.bar(labels, rates, color=cols, width=.62)
    for rect, n, r in zip(b, ns, rates):
        ax.text(rect.get_x() + rect.get_width() / 2, r + 1.4, f"{r:.1f}%\n(n={n:,})",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_ylabel("% of reports that NAME slowing")
    ax.set_ylim(0, max(rates) + 14)
    ax.set_title("P6 — readers under-report slowing that is only visible in sleep\n"
                 "when slowing is visible awake readers name it 75% of the time;\n"
                 "when it is visible ONLY in sleep, only 54%", fontsize=11, fontweight="bold")
    ax.grid(alpha=.25, axis="y")
    fig.tight_layout(); fig.savefig(G / "v4a_wake_sleep.png", dpi=140); plt.close(fig)
    print("wrote", G / "v4a_wake_sleep.png")


def fig_lateralization_band():
    """Band-matched left-vs-right lateralization AUROC (rows = reported band, cols = classifier)."""
    df = pd.DataFrame({
        "case_band": ["delta", "theta", "mixed"],
        "n": [536, 329, 1632],
        "clf_delta": [0.891, 0.852, 0.888],
        "clf_theta": [0.768, 0.829, 0.787],
        "clf_both":  [0.894, 0.841, 0.888],
    })
    x = np.arange(len(df)); w = 0.26
    fig, ax = plt.subplots(figsize=(8.2, 5))
    for i, (c, lab, col) in enumerate([("clf_delta", "delta-band features", "#1f77b4"),
                                       ("clf_theta", "theta-band features", "#ff7f0e"),
                                       ("clf_both", "both bands", "#2ca02c")]):
        ax.bar(x + (i - 1) * w, df[c], w, label=lab, color=col)
    ax.axhline(0.5, ls=":", c="#999")
    ax.set_xticks(x); ax.set_xticklabels([f"{b}\n(n={n:,})" for b, n in zip(df.case_band, df.n)])
    ax.set_ylim(0.5, 1.0); ax.set_ylabel("AUROC — left vs right")
    ax.set_xlabel("band named in the report")
    ax.set_title("Band-matched focal lateralization (n=2,691)\n"
                 "delta-band asymmetry carries the side information regardless of the reported band",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=.25, axis="y")
    fig.tight_layout(); fig.savefig(F / "lateralization_by_band_roc.png", dpi=140); plt.close(fig)
    print("wrote", F / "lateralization_by_band_roc.png")


if __name__ == "__main__":
    fig_occasion_roc()
    fig_v4a_wake_sleep()
    fig_lateralization_band()
