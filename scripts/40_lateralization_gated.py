"""Gated lateralization: among FOCAL recordings with a definite side, predict LEFT vs RIGHT.

Brandon's insight: detection (is there focal slowing?) is side-invariant and easy; lateralization is a
different, focal-only, binary (left vs right) task. Evaluating side over ALL abnormals drowns left/right
in a bilateral majority (generalized slowing is bilateral by definition). Here we GATE on focal + a
stated side, drop bilateral, and predict L vs R from the SIGNED homologous asymmetry features.

Writes results/lateralization_gated.md + results/figs/lateralization_roc.png.
Run: PYTHONPATH=src python scripts/40_lateralization_gated.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve, accuracy_score, balanced_accuracy_score


def main():
    asym = pd.read_parquet("data/derived/recording_asymmetry.parquet")
    rep = pd.read_csv("results/report_extracted_labels.csv").drop_duplicates("bdsp_id")[["bdsp_id", "label", "side"]]
    df = asym.merge(rep, on="bdsp_id", how="inner", suffixes=("", "_rep"))
    side = df["side_rep"] if "side_rep" in df else df["side"]
    # GATE: focal + definite side
    foc = df[(df.label == "focal_slow") & side.isin(["left", "right"])].copy()
    foc["side"] = np.where(rep.set_index("bdsp_id").reindex(foc.bdsp_id).side.values == "left", "left", "right")
    y = (foc.side == "left").astype(int).to_numpy()          # 1 = left
    acols = [c for c in foc.columns if c.startswith("asym_")]
    X = foc[acols].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0.0)
    print(f"focal lateralized n={len(foc)}  (left={y.sum()}, right={(1-y).sum()})")

    out = ["# Gated lateralization — LEFT vs RIGHT among focal recordings with a stated side\n",
           f"n = {len(foc)} (left {int(y.sum())}, right {int((1-y).sum())}). Bilateral & generalized excluded.\n"]

    # (1) single signed features as scores
    out.append("\n## Single signed-asymmetry features (AUROC for left-vs-right)\n")
    singles = {}
    for c in ["asym_temporal_delta", "asym_parasagittal_delta", "asym_temporal_theta"]:
        if c in foc:
            s = foc[c].fillna(0).to_numpy()
            a = roc_auc_score(y, s); a = max(a, 1 - a)        # orientation-agnostic
            singles[c] = a
            out.append(f"- {c}: AUROC {a:.3f}")

    # (2) supervised LR on all signed asymmetry features (5-fold OOF)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, class_weight="balanced"))
    oof = cross_val_predict(clf, X.values, y, cv=5, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, oof)
    pred = (oof >= 0.5).astype(int)
    acc = accuracy_score(y, pred); bacc = balanced_accuracy_score(y, pred)
    out += [f"\n## Supervised LR on all signed asymmetries (5-fold OOF)",
            f"\n- **AUROC (left vs right) = {auc:.3f}**",
            f"\n- accuracy {acc:.3f}, balanced accuracy {bacc:.3f}",
            f"\n- confusion (rows=true L/R, cols=pred L/R):"]
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y, pred, labels=[1, 0])
    out.append("\n```\n" + pd.DataFrame(cm, index=["true L", "true R"], columns=["pred L", "pred R"]).to_string() + "\n```")

    # ROC figure
    fpr, tpr, _ = roc_curve(y, oof)
    fig, ax = plt.subplots(figsize=(5.2, 5))
    ax.plot(fpr, tpr, lw=2, color="#e0568a", label=f"supervised LR (AUROC {auc:.2f})")
    if "asym_temporal_delta" in singles:
        s = foc["asym_temporal_delta"].fillna(0).to_numpy()
        if roc_auc_score(y, s) < 0.5: s = -s
        f2, t2, _ = roc_curve(y, s)
        ax.plot(f2, t2, lw=1.5, color="#4a90e2", ls="--", label=f"temporal δ asym ({singles['asym_temporal_delta']:.2f})")
    ax.plot([0, 1], [0, 1], "k:", lw=1)
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title(f"Focal lateralization: L vs R (n={len(foc)})")
    ax.legend(loc="lower right"); ax.grid(alpha=0.25)
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/lateralization_roc.png", dpi=130)

    out.append("\n\n_Contrast: the ungated 3-way side eval (all abnormals incl. bilateral generalized) gave "
               "left/right F1 0.35/0.24 — an artifact of the bilateral majority. Gating to focal + binary "
               "L/R is the correct, clinically-posed task._\n")
    Path("results/lateralization_gated.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
