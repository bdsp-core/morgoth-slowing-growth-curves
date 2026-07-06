"""Fix oversight #4 (part b): SUPERVISED region classifier vs the temporal-default + argmax baselines.

Trains a CV logistic regression on age-band-adjusted per-bipolar-channel slowing deviations
(recording_features_py.parquet: 18 channels x {rel_delta, DAR, TAR, log_delta}) to predict the report's
region, on abnormal recordings where the report states a region (~3525). Reports OOF row-normalized
confusion + per-region precision/recall/F1 + macro-F1 + accuracy, next to two baselines:
  - temporal-default (always predict the majority class)
  - argmax deviation lobe (scripts/37)
Writes results/figs/region_confusion_supervised.png + results/region_supervised.md.
Run: PYTHONPATH=src python scripts/39_region_supervised.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score, f1_score

CH = ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2",
      "Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2", "Fz-Cz", "Cz-Pz"]
METRICS = ["rel_delta", "DAR", "TAR", "log_delta"]
REGIONS = ["frontal", "temporal", "central", "parietal", "occipital"]
AGE_BINS = [0, 18, 45, 60, 75, 120]


def heatmap(cm, labels, title, path):
    n = cm.sum(axis=1, keepdims=True); cmn = cm / n.clip(min=1)
    ylab = [f"{l} (n={int(v)})" for l, v in zip(labels, n.ravel())]
    fig, ax = plt.subplots(figsize=(1.7 + 1.1 * len(labels), 1.3 + 1.0 * len(labels)))
    im = ax.imshow(cmn, cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(ylab)
    ax.set_xlabel("predicted (supervised)"); ax.set_ylabel("report (reference)"); ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center",
                    color="white" if cmn[i, j] > 0.5 else "#333", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, label="row-normalized")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    rf = pd.read_parquet("data/derived/recording_features_py.parquet")
    ch = rf[rf.region.isin(CH)].copy()
    ch["ageband"] = pd.cut(pd.to_numeric(ch.age, errors="coerce"), bins=AGE_BINS)
    # age-band-adjusted per-channel deviation z for each metric (vs normals)
    zcols = {}
    for m in METRICS:
        norm = ch[ch.label == "normal"].groupby(["region", "ageband"], observed=True)[m].agg(["mean", "std"])
        j = ch.join(norm, on=["region", "ageband"])
        ch[f"z_{m}"] = (j[m] - j["mean"]) / (j["std"] + 1e-9)
    feats = ch.pivot_table(index="bdsp_id", columns="region", values=[f"z_{m}" for m in METRICS])
    feats.columns = [f"{a}_{b}" for a, b in feats.columns]

    rep = pd.read_csv("results/report_extracted_labels.csv")
    rep = rep[(rep.label != "normal") & rep.region.isin(REGIONS)].drop_duplicates("bdsp_id").set_index("bdsp_id")
    df = feats.join(rep["region"], how="inner").dropna(subset=["region"])
    X = df.drop(columns="region").replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)
    y = df.region.to_numpy()
    print("n =", len(df), "| region mix:", df.region.value_counts().to_dict())

    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, class_weight="balanced",
                                                             C=0.5))
    oof = cross_val_predict(clf, X.values, y, cv=5)
    acc = accuracy_score(y, oof); mf1 = f1_score(y, oof, labels=REGIONS, average="macro", zero_division=0)
    p, rc, f1, sup = precision_recall_fscore_support(y, oof, labels=REGIONS, zero_division=0)
    cm = confusion_matrix(y, oof, labels=REGIONS)
    heatmap(cm, REGIONS, f"Region — supervised (n={len(df)}) acc={acc:.2f} macroF1={mf1:.2f}",
            "results/figs/region_confusion_supervised.png")

    # baselines
    maj = pd.Series(y).value_counts().idxmax()
    acc_major = (y == maj).mean()
    macro_major = f1_score(y, [maj] * len(y), labels=REGIONS, average="macro", zero_division=0)

    out = ["# Region localization — supervised classifier vs baselines\n",
           f"Abnormal recordings with a report region, n={len(df)}. Features: age-band-adjusted per-channel "
           "slowing deviations (18 ch x 4 metrics). 5-fold OOF multinomial LR (balanced).\n",
           "\n## Headline comparison\n",
           "| approach | accuracy | macro-F1 |",
           "|---|---|---|",
           f"| temporal-default (majority) | {acc_major:.3f} | {macro_major:.3f} |",
           f"| argmax-deviation lobe (scripts/37) | 0.162 | 0.115 |",
           f"| **supervised LR (this)** | **{acc:.3f}** | **{mf1:.3f}** |",
           "\n_Accuracy favors the majority-default (temporal ~69%); **macro-F1 is the honest metric** "
           "(equal weight per region) — the default scores ~0.16 there because it never predicts the "
           "other four regions._\n",
           "\n## Supervised per-region metrics\n",
           pd.DataFrame({"region": REGIONS, "precision": p.round(3), "recall": rc.round(3),
                         "f1": f1.round(3), "n": sup}).to_markdown(index=False) + "\n"]
    Path("results/region_supervised.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
