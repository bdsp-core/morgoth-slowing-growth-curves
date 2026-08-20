#!/usr/bin/env python3
"""Is k=5 the right recording-level aggregation? Sweep it (review item: k provenance).

A recording's LENS score is the mean of its top-k segment scores. scripts/54 hard-codes K=5 and its docstring
calls this "the §1b winner", but that sweep is not in this repository, so the choice was undocumented. This
recovers it: retrain the model once, then vary k only at the aggregation step and re-score.

k is varied ONLY on the aggregation, never on the fit, so every k sees the identical trained model. Reported
on the report-test split (the development data, where k was legitimately chosen) and on ON-100 (external,
shown to confirm the choice does not depend on which set you look at, NOT to select k).

Writes results/story/topk_sweep.md + figures/story/s11_topk_sweep.png
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/80_topk_sweep.py
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_argv = sys.argv[:]
sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py")
m54 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m54)
sys.argv = _argv

KS = [1, 2, 3, 5, 8, 10, 15, 20, 30, 50]
FIG = Path("figures/story")
RES = Path("results/story")


def topk_mean(v: np.ndarray, k: int) -> float:
    return float(np.sort(v)[::-1][:k].mean())


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    tr = S[(S.dataset == "report") & (S.split == "train")]
    print(f"train segments: {len(tr):,}")

    # identical training to scripts/54 — v2 (MIL) is LENS
    for tag, cols, ylab in [("focal", m54.FOC, "y_focal"), ("generalized", m54.AMT, "y_gen")]:
        h = m54.train_mil(tr, cols, ylab)
        S[f"v2_{tag}"] = h.score(S[cols].fillna(S[cols].median()).values)
        print(f"  trained {tag} head")

    panels = m54.expert_and_morgoth("occasion")
    rows = []
    for tag, ylab in [("focal", "y_focal"), ("generalized", "y_gen")]:
        rep = S[(S.dataset == "report") & (S.split == "test")]
        y_rep = rep.groupby("eeg_id")[ylab].max()
        occ = S[S.dataset == "occasion"]
        wide, _ = panels[tag]
        y_occ = (wide.mean(axis=1) > 0.5).astype(int)          # expert-vote majority
        for k in KS:
            s_rep = rep.groupby("eeg_id")[f"v2_{tag}"].apply(lambda v: topk_mean(v.values, k))
            a_rep = roc_auc_score(y_rep.loc[s_rep.index], s_rep)
            s_occ = occ.groupby("eeg_id")[f"v2_{tag}"].apply(lambda v: topk_mean(v.values, k))
            idx = [i for i in s_occ.index if i in y_occ.index]
            a_occ = roc_auc_score(y_occ.loc[idx], s_occ.loc[idx]) if len(set(y_occ.loc[idx])) > 1 else np.nan
            rows.append(dict(axis=tag, k=k, auroc_report_test=a_rep, auroc_on100=a_occ,
                             n_report=len(s_rep), n_on100=len(idx)))
            print(f"  {tag:12s} k={k:3d}  report-test {a_rep:.4f}   ON-100 {a_occ:.4f}", flush=True)

    t = pd.DataFrame(rows)
    t.to_csv(RES / "topk_sweep.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.6), squeeze=False)
    lines = ["# Recording-level top-k aggregation sweep", "",
             "A recording's score is the mean of its top-k segment scores. The model is trained once; k is "
             "varied only at aggregation, so every row uses the identical fitted model.", ""]
    for j, tag in enumerate(["generalized", "focal"]):
        ax = axes[0][j]
        d = t[t.axis == tag]
        ax.plot(d.k, d.auroc_report_test, marker="o", ms=3.5, lw=1.5, color="#1b6ca8", label="report-test")
        ax.plot(d.k, d.auroc_on100, marker="s", ms=3.5, lw=1.5, color="#c1440e", label="ON-100 (external)")
        ax.axvline(5, color="#666", ls="--", lw=1.0)
        ax.set_xscale("log")
        ax.set_xticks(KS)
        ax.set_xticklabels([str(k) for k in KS], fontsize=6)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.18)
        ax.set_title(tag, fontsize=9)
        ax.set_xlabel("k (segments averaged)", fontsize=8)
        if j == 0:
            ax.set_ylabel("AUROC", fontsize=8)
            ax.legend(fontsize=7, frameon=False, loc="lower left")
        best_r = d.loc[d.auroc_report_test.idxmax()]
        at5 = d[d.k == 5].iloc[0]
        lines += [f"**{tag}** — best on report-test at k={int(best_r.k)} (AUROC {best_r.auroc_report_test:.4f}); "
                  f"k=5 gives {at5.auroc_report_test:.4f} "
                  f"(Δ {at5.auroc_report_test - best_r.auroc_report_test:+.4f}). "
                  f"Externally k=5 gives {at5.auroc_on100:.4f}, best {d.auroc_on100.max():.4f}.", ""]
    lines += ["| axis | k | AUROC report-test | AUROC ON-100 |", "|---|---|---|---|"]
    for _, r in t.iterrows():
        lines.append(f"| {r.axis} | {int(r.k)} | {r.auroc_report_test:.4f} | {r.auroc_on100:.4f} |")
    (RES / "topk_sweep.md").write_text("\n".join(lines) + "\n")
    fig.suptitle("Recording-level top-k aggregation (dashed = the k=5 used throughout)", fontsize=9)
    fig.tight_layout()
    out = FIG / "s11_topk_sweep.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nwrote {out} and {RES/'topk_sweep.md'}")


if __name__ == "__main__":
    main()
