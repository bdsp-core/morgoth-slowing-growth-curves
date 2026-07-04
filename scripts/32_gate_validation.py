"""Validate the Morgoth gate on the newly-ingested (expansion) recordings against report labels.

For each recording we have the report-derived label (normal / focal_slow / general_slow) and the gate's
per-recording probabilities (normal_head_prob = P(abnormal); p_focal; p_generalized). This checks the
gate is calibrated the way we'd expect BEFORE trusting it as the detector in the report pipeline:
  - abnormal recordings (focal/gen) should have HIGHER P(abnormal) than normal ones
  - focal recordings should score higher on p_focal than non-focal
  - generalized recordings should score higher on p_generalized than non-generalized
Reports AUC where each contrast has both classes present (else group means only). Writes
results/expansion_gate_validation.md. Strengthens as more balanced data accumulates.

Run: PYTHONPATH=src python scripts/32_gate_validation.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

GATE = Path("results/expansion_gate_probs.csv")
PROV = Path("results/expansion_provenance.csv")
OUT = Path("results/expansion_gate_validation.md")


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    pos, neg = pos[~np.isnan(pos)], neg[~np.isnan(neg)]
    if len(pos) == 0 or len(neg) == 0:
        return None
    # Mann-Whitney U / (n_pos*n_neg)
    allv = np.concatenate([pos, neg]); order = allv.argsort()
    ranks = np.empty_like(order, float); ranks[order] = np.arange(1, len(allv) + 1)
    r_pos = ranks[:len(pos)].sum()
    return (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    if not GATE.exists() or not PROV.exists():
        print("no gate/provenance yet"); return
    g = pd.read_csv(GATE); p = pd.read_csv(PROV)[["bdsp_id", "label"]]
    df = g.merge(p, on="bdsp_id", how="left")
    n = len(df)
    lines = [f"# Expansion gate validation (n={n} recordings with gate probs)\n",
             f"Label mix: {df.label.value_counts().to_dict()}\n",
             "**Preliminary** — strengthens as the balanced set grows.\n",
             "## Mean gate probability by report label\n"]
    tab = df.groupby("label")[["normal_head_prob", "p_focal", "p_generalized"]].mean().round(3)
    lines.append(tab.to_markdown() + "\n")

    lines.append("## Expected orderings (contrast AUC where both classes present)\n")
    abn = df[df.label.isin(["focal_slow", "general_slow"])]
    nrm = df[df.label == "normal"]
    checks = [
        ("P(abnormal): abnormal > normal", auc(abn.normal_head_prob, nrm.normal_head_prob)),
        ("p_focal: focal > non-focal", auc(df[df.label == "focal_slow"].p_focal, df[df.label != "focal_slow"].p_focal)),
        ("p_generalized: gen > non-gen", auc(df[df.label == "general_slow"].p_generalized, df[df.label != "general_slow"].p_generalized)),
    ]
    for name, a in checks:
        verdict = "n/a (need both classes)" if a is None else (f"AUC={a:.2f} " + ("✅" if a >= 0.6 else ("~" if a >= 0.45 else "⚠️")))
        lines.append(f"- {name}: {verdict}")
    lines.append("\n(AUC ≥ 0.6 = expected direction with useful separation; ~ = weak/underpowered; "
                 "⚠️ = wrong direction — revisit if it persists with more data.)\n")
    lines.append("\nNote: many report-labeled recordings carry BOTH focal and generalized flags, so the "
                 "focal-vs-gen contrast is inherently soft; P(abnormal) is the cleanest check.\n")
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
