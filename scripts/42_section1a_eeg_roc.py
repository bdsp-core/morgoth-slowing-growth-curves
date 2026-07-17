#!/usr/bin/env python3
"""SECTION 1a — Morgoth's EEG-level slowing detector on the REPORT dataset (single scorer).

ONLY Morgoth's EEG-level heads (gate_eeg_level_rerun: p_focal, p_generalized), scored against the
report-derived flags on clean_pair recordings. Focal and generalized as separate binary axes, plus
"any slowing" (max of the two heads vs slowing_positive). No band-power / deviation comparator here —
the deviation field is Section 2.

Writes figures/story/s1a_eeg_roc_prc.png + results/story/s1a_eeg.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/42_section1a_eeg_roc.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

FIG = Path("figures/story"); RES = Path("results/story")


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id")
    d = lab.merge(head[["eeg_id", "p_focal", "p_generalized"]], on="eeg_id", how="inner")
    d = d[(d.clean_pair == True) & (~d.eeg_id.astype(str).str.startswith(("MOE_", "ON_")))]   # noqa: E712
    d["p_any"] = d[["p_focal", "p_generalized"]].max(axis=1)

    tasks = [("focal", "slowing_focal", "p_focal", "#c8443c"),
             ("generalized", "slowing_gen_pathologic", "p_generalized", "#2c7fb8"),
             ("any slowing", "slowing_positive", "p_any", "#66a61e")]

    fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.7))
    a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
    md = ["# Section 1a — Morgoth EEG-level detector vs report labels (clean_pair, single scorer)\n",
          "| axis | n pos / N | AUROC | average precision |", "|---|---|---|---|"]
    for name, labcol, pcol, color in tasks:
        y = d[labcol].fillna(False).astype(int).values
        s = d[pcol].values
        ok = np.isfinite(s)
        y, s = y[ok], s[ok]
        auc = roc_auc_score(y, s); ap = average_precision_score(y, s)
        fpr, tpr, _ = roc_curve(y, s); prec, rec, _ = precision_recall_curve(y, s)
        a0.plot(fpr, tpr, color=color, lw=2.3, label=f"{name} (AUROC {auc:.3f})")
        a1.plot(rec, prec, color=color, lw=2.3, label=f"{name} (AP {ap:.3f})")
        a1.axhline(y.mean(), ls=":", color=color, lw=.8, alpha=.5)
        md.append(f"| {name} | {int(y.sum()):,}/{len(y):,} | {auc:.3f} | {ap:.3f} |")

    a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity"); a0.set_title("ROC", fontsize=11)
    a0.legend(frameon=False, fontsize=8, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
    a1.set_xlabel("recall"); a1.set_ylabel("precision"); a1.set_title("PRC (dotted = prevalence)", fontsize=11)
    a1.legend(frameon=False, fontsize=8, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
    fig.suptitle(f"Morgoth EEG-level slowing detection vs report labels ({len(d):,} clean_pair recordings)",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "s1a_eeg_roc_prc.png", dpi=150); plt.close(fig)
    (RES / "s1a_eeg.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s1a_eeg_roc_prc.png + results/story/s1a_eeg.md")


if __name__ == "__main__":
    main()
