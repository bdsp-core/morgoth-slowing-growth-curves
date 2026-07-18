#!/usr/bin/env python3
"""SECTION 0b — Morgoth EEG-level detection vs the MoE expert panel (the large, band-resolved panel).

MoE events (15 s clips, 0-padded to 30 s for Morgoth) scored by ~21 experts, band-resolved. We collapse to
EEG-level SLOWING per axis: a rater marks FOCAL (resp. GENERALIZED) slowing on an event if they marked ANY
band (delta/theta/alpha) of that type, unioned over the three (disjoint-event) rounds r1/r2/r3. Focal and
generalized are separate binary axes.

Morgoth's EEG-level probability for each MoE event = gate_eeg_level_rerun (p_focal / p_generalized), joined by
eeg_id = "MOE_" + event. Same analysis as OccasionNoise (scripts/40): panel-majority truth; each expert an
operating point on BOTH ROC and PRC vs the LEAVE-ONE-OUT consensus of the others; % of experts under each.

PHI/authorship: rater columns are real usernames. `bwestove` (an author of this system) is EXCLUDED from the
panel entirely (validation_plan.md §76). Remaining raters are anonymized R01..Rnn (never written out).

Labels are read from the scratchpad copy of Box MoE labels (not committed). Writes
figures/story/s0_moe_{focal,generalized}.png + results/story/s0_moe.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/45_moe_section0.py
"""
from __future__ import annotations
import glob, os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

LBL = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
       "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/labels")
META = {"eeg", "event", "index", "Unnamed: 0"}
EXCLUDE = {"bwestove"}                                  # author-rater, excluded from the panel
FIG = Path("figures/story"); RES = Path("results/story")
AX = [("focal", "focalslowing", "p_focal", "#c8443c"),
      ("generalized", "genslowing", "p_generalized", "#2c7fb8")]


def build_matrix(cat):
    """(event x rater) binary: rater marks the event if ANY band/round == 1; NaN if they never read it."""
    frames = []
    for f in glob.glob(f"{LBL}/r*_csv_labels_20241028/moe_*{cat}-*.csv"):
        d = pd.read_csv(f)
        raters = [c for c in d.columns if c not in META]
        frames.append(d.set_index("event")[raters])
    allr = sorted(set().union(*[set(f.columns) for f in frames]) - EXCLUDE)
    alle = sorted(set().union(*[set(f.index) for f in frames]))
    seen = pd.DataFrame(False, index=alle, columns=allr)          # did rater read event (in any file)
    pos = pd.DataFrame(0.0, index=alle, columns=allr)             # did rater ever mark it 1
    for f in frames:
        g = f.reindex(index=alle, columns=allr)
        seen |= g.notna()
        pos = np.fmax(pos, g.fillna(0))
    M = pos.where(seen, np.nan)
    return M


def expert_points(M):
    pts = {}
    for r in M.columns:
        others = M.drop(columns=r)
        me = M[r]
        rows = me.notna() & others.notna().any(axis=1)
        if rows.sum() < 10:
            continue
        cons = (others.loc[rows].mean(axis=1) >= 0.5).astype(int)
        mv = me[rows].astype(int)
        tp = int(((mv == 1) & (cons == 1)).sum()); fp = int(((mv == 1) & (cons == 0)).sum())
        fn = int(((mv == 0) & (cons == 1)).sum()); tn = int(((mv == 0) & (cons == 0)).sum())
        if (tp + fn) == 0 or (fp + tn) == 0:
            continue
        pts[r] = {"fpr": fp / (fp + tn), "tpr": tp / (tp + fn),
                  "recall": tp / (tp + fn), "precision": (tp / (tp + fp)) if (tp + fp) else np.nan}
    return pts


def under_roc(fpr, tpr, pts):
    f = {r: float(np.interp(p["fpr"], fpr, tpr)) >= p["tpr"] - 1e-9 for r, p in pts.items()}
    return (sum(f.values()) / len(f) if f else np.nan), f


def under_pr(prec, rec, pts):
    o = np.argsort(rec); rs, ps = np.asarray(rec)[o], np.asarray(prec)[o]
    v = {r: p for r, p in pts.items() if np.isfinite(p["precision"])}
    f = {r: float(np.interp(p["recall"], rs, ps)) >= p["precision"] - 1e-9 for r, p in v.items()}
    return (sum(f.values()) / len(f) if f else np.nan), f


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    md = ["# Section 0b — Morgoth EEG-level detection vs the MoE expert panel (band-resolved, author excluded)\n",
          "Events collapsed to EEG-level slowing per axis (any band, any round). Ground truth = panel "
          "majority; each expert scored vs the leave-one-out consensus of the others. `bwestove` (author) "
          "excluded.\n",
          "| axis | n pos / N | AUROC | AP | experts | % under ROC | % under PR |",
          "|---|---|---|---|---|---|---|"]

    for name, cat, headcol, color in AX:
        M = build_matrix(cat)
        M.index = [f"MOE_{e}" for e in M.index]
        keep = M.index.intersection(head.index)                   # events Morgoth actually scored
        M = M.loc[keep]
        s = head.loc[keep, headcol].values
        y = (M.mean(axis=1) >= 0.5).astype(int).values
        auc = roc_auc_score(y, s); ap = average_precision_score(y, s)
        fpr, tpr, _ = roc_curve(y, s); prec, rec, _ = precision_recall_curve(y, s)
        pts = expert_points(M)
        pu_roc, fr = under_roc(fpr, tpr, pts); pu_pr, fp = under_pr(prec, rec, pts)
        md.append(f"| {name} | {int(y.sum()):,}/{len(y):,} | {auc:.3f} | {ap:.3f} | {len(pts)} | "
                  f"**{100*pu_roc:.0f}%** | **{100*pu_pr:.0f}%** |")

        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.6))
        a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
        a0.plot(fpr, tpr, color=color, lw=2.4, label=f"Morgoth (AUROC {auc:.2f})")
        for r, p in pts.items():
            a0.plot(p["fpr"], p["tpr"], "o", ms=5, mfc=("#888" if fr.get(r) else "#e41a1c"), mec="k", mew=.3, alpha=.8)
        a0.plot([], [], "o", mfc="#888", mec="k", label=f"under curve ({sum(fr.values())})")
        a0.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above curve ({len(pts)-sum(fr.values())})")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity")
        a0.set_title(f"{name.upper()} — ROC\n{100*pu_roc:.0f}% of {len(pts)} experts under Morgoth", fontsize=10)
        a0.legend(frameon=False, fontsize=7.5, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
        a1.plot(rec, prec, color=color, lw=2.4, label=f"Morgoth (AP {ap:.2f})")
        a1.axhline(y.mean(), ls="--", color="#bbb", lw=1, label=f"prevalence {y.mean():.2f}")
        for r, p in pts.items():
            if not np.isfinite(p["precision"]):
                continue
            a1.plot(p["recall"], p["precision"], "o", ms=5, mfc=("#888" if fp.get(r) else "#e41a1c"),
                    mec="k", mew=.3, alpha=.8)
        a1.plot([], [], "o", mfc="#888", mec="k", label=f"under PR ({sum(fp.values())})")
        a1.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above PR ({len(fp)-sum(fp.values())})")
        a1.set_xlabel("recall"); a1.set_ylabel("precision")
        a1.set_title(f"{name.upper()} — PRC\n{100*pu_pr:.0f}% of {len(fp)} experts under Morgoth", fontsize=10)
        a1.legend(frameon=False, fontsize=7.5, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"Morgoth EEG-level detection of {name} slowing vs {len(pts)} MoE experts "
                     f"(band-resolved; author excluded; LOO consensus)", fontsize=10.5)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(FIG / f"s0_moe_{name}.png", dpi=150); plt.close(fig)

    (RES / "s0_moe.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_moe_*.png + results/story/s0_moe.md")


if __name__ == "__main__":
    main()
