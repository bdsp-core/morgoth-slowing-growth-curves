"""ROC and Precision-Recall curves for the key discriminations.

Panels:
  A. Our deviation-feature LR (OOF, 5-fold) vs clinical label: normal-vs-focal, normal-vs-generalized.
  B. Morgoth EEG-level probs vs the report-derived flags: abnormal, focal, generalized.
Outputs: figures/roc_prc/roc.png, figures/roc_prc/prc.png
Run: after 06 (adjusted_z), 14 (gate_probs), 19 (report_flags_matched.parquet).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

DER = Path("data/derived"); FIG = Path("figures/roc_prc"); FIG.mkdir(parents=True, exist_ok=True)


def our_lr_oof(pos):
    az = pd.read_parquet(DER / "adjusted_z.parquet"); az["fr"] = az.feature + "@" + az.region
    X = az.pivot_table(index="bdsp_id", columns="fr", values="z", aggfunc="mean")
    lab = az.drop_duplicates("bdsp_id").set_index("bdsp_id").label
    d = X.join(lab).dropna(subset=["label"])
    d = d[d.label.isin(["normal", pos])]
    y = (d.label == pos).astype(int).values
    Xv = d.drop(columns=["label"]).fillna(0.0).values
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    p = cross_val_predict(lr, Xv, y, cv=5, method="predict_proba")[:, 1]
    return y, p


def main():
    curves = []  # (name, y, score)
    for pos, nm in [("focal_slow", "our-LR normal vs focal"), ("general_slow", "our-LR normal vs generalized")]:
        y, p = our_lr_oof(pos); curves.append((nm, y, p))
    rf = DER / "report_flags_matched.parquet"
    if rf.exists():
        m = pd.read_parquet(rf)
        for prob, flag, nm in [("p_abnormal", "r_abnormal", "Morgoth vs report: abnormal"),
                               ("p_focal", "r_focal", "Morgoth vs report: focal"),
                               ("p_generalized", "r_gen", "Morgoth vs report: generalized")]:
            d = m[[prob, flag]].dropna()
            curves.append((nm, d[flag].values.astype(int), d[prob].values))

    # ROC
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for nm, y, s in curves:
        fpr, tpr, _ = roc_curve(y, s); ax.plot(fpr, tpr, lw=2, label=f"{nm} (AUC {roc_auc_score(y,s):.2f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=.5); ax.set_xlabel("false positive rate"); ax.set_ylabel("true positive rate")
    ax.set_title("ROC"); ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(FIG / "roc.png", dpi=120); plt.close(fig)

    # PRC
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for nm, y, s in curves:
        pr, rc, _ = precision_recall_curve(y, s)
        ax.plot(rc, pr, lw=2, label=f"{nm} (AP {average_precision_score(y,s):.2f}, prev {y.mean():.2f})")
    ax.set_xlabel("recall"); ax.set_ylabel("precision"); ax.set_title("Precision–Recall")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(FIG / "prc.png", dpi=120); plt.close(fig)
    print("wrote figures/roc_prc/roc.png and prc.png")
    for nm, y, s in curves:
        print(f"  {nm}: AUC {roc_auc_score(y,s):.3f}, AP {average_precision_score(y,s):.3f}, prev {y.mean():.2f}, n {len(y)}")


if __name__ == "__main__":
    main()
