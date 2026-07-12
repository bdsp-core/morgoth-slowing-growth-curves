"""Gated region localization, split by slowing type (Brandon's point 2):
  (A) FOCAL cases only -> which lobe (temporal/frontal/central/...); don't let generalized swamp it.
  (B) GENERALIZED cases -> not a side question, but an ANTERIOR vs POSTERIOR predominance one
      (FIRDA-like frontal vs OIRDA-like posterior), scored from an anterior-minus-posterior slowing
      gradient.
Uses per-bipolar-channel age-adjusted deviations (recording_features.parquet).
Writes results/region_gated.md + results/figs/{region_focal_gated.png, generalized_ap.png}.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score, f1_score, roc_auc_score

CH = ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2",
      "Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2", "Fz-Cz", "Cz-Pz"]
ANTERIOR = ["Fp1-F3", "Fp2-F4", "Fp1-F7", "Fp2-F8", "F3-C3", "F4-C4", "Fz-Cz"]
POSTERIOR = ["C3-P3", "C4-P4", "P3-O1", "P4-O2", "T5-O1", "T6-O2", "Cz-Pz"]
METRICS = ["rel_delta", "DAR", "TAR", "log_delta"]
AGE_BINS = [0, 18, 45, 60, 75, 120]
FOCAL_REGIONS = ["temporal", "frontal", "central", "parietal", "occipital"]


def channel_z():
    rf = pd.read_parquet("data/derived/recording_features.parquet")
    ch = rf[rf.region.isin(CH)].copy()
    ch["ageband"] = pd.cut(pd.to_numeric(ch.age, errors="coerce"), bins=AGE_BINS)
    for m in METRICS:
        norm = ch[ch.label == "normal"].groupby(["region", "ageband"], observed=True)[m].agg(["mean", "std"])
        j = ch.join(norm, on=["region", "ageband"])
        ch[f"z_{m}"] = (j[m] - j["mean"]) / (j["std"] + 1e-9)
    return ch


def main():
    ch = channel_z()
    rep = pd.read_csv("results/report_extracted_labels.csv").drop_duplicates("bdsp_id").set_index("bdsp_id")
    feats = ch.pivot_table(index="bdsp_id", columns="region", values=[f"z_{m}" for m in METRICS])
    feats.columns = [f"{a}_{b}" for a, b in feats.columns]
    out = ["# Gated region localization (split by slowing type)\n"]

    # ---- (A) FOCAL-only lobe classifier ----
    fr = rep[(rep.label == "focal_slow") & rep.region.isin(FOCAL_REGIONS)]
    A = feats.join(fr["region"], how="inner").dropna(subset=["region"])
    X = A.drop(columns="region").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = A.region.to_numpy()
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, class_weight="balanced", C=0.5))
    oof = cross_val_predict(clf, X.values, y, cv=5)
    acc = accuracy_score(y, oof); mf1 = f1_score(y, oof, labels=FOCAL_REGIONS, average="macro", zero_division=0)
    p, rc, f1, sup = precision_recall_fscore_support(y, oof, labels=FOCAL_REGIONS, zero_division=0)
    out += [f"\n## (A) FOCAL-only lobe localization (n={len(A)}) — acc {acc:.3f}, macro-F1 {mf1:.3f}\n",
            pd.DataFrame({"region": FOCAL_REGIONS, "precision": p.round(3), "recall": rc.round(3),
                          "f1": f1.round(3), "n": sup}).to_markdown(index=False) + "\n"]
    cm = confusion_matrix(y, oof, labels=FOCAL_REGIONS); cmn = cm / cm.sum(1, keepdims=True).clip(min=1)
    fig, ax = plt.subplots(figsize=(6.2, 5.4)); im = ax.imshow(cmn, cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(5)); ax.set_xticklabels(FOCAL_REGIONS, rotation=40, ha="right"); ax.set_yticks(range(5))
    ax.set_yticklabels([f"{r} (n={int(n)})" for r, n in zip(FOCAL_REGIONS, cm.sum(1))])
    ax.set_xlabel("predicted"); ax.set_ylabel("report"); ax.set_title(f"Focal-gated lobe (acc {acc:.2f}, macroF1 {mf1:.2f})")
    for i in range(5):
        for j in range(5): ax.text(j, i, f"{cmn[i,j]:.2f}", ha="center", va="center", color="white" if cmn[i,j]>0.5 else "#333", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046); fig.tight_layout(); fig.savefig("results/figs/region_focal_gated.png", dpi=130); plt.close(fig)

    # ---- (B) GENERALIZED anterior vs posterior predominance ----
    # SAP §8.2: generalized topography lives in its OWN column gen_topography (anterior/posterior/unspec),
    # not the focal `region` column (which is NaN for generalized cases). Use it directly.
    g = rep[(rep.label == "general_slow") & rep.gen_topography.isin(["anterior", "posterior"])].copy()
    g["ap"] = g.gen_topography
    G = feats.join(g["ap"], how="inner").dropna(subset=["ap"])
    # anterior-minus-posterior delta gradient
    az = G[[f"z_rel_delta_{c}" for c in ANTERIOR if f"z_rel_delta_{c}" in G]].mean(axis=1)
    pz = G[[f"z_rel_delta_{c}" for c in POSTERIOR if f"z_rel_delta_{c}" in G]].mean(axis=1)
    grad = (az - pz).fillna(0).to_numpy()
    yb = (G.ap == "anterior").astype(int).to_numpy()
    auc_grad = roc_auc_score(yb, grad); auc_grad = max(auc_grad, 1 - auc_grad)
    # supervised version
    Xg = G.drop(columns="ap").replace([np.inf, -np.inf], np.nan).fillna(0.0).values
    oofg = cross_val_predict(make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, class_weight="balanced")),
                             Xg, yb, cv=5, method="predict_proba")[:, 1]
    auc_sup = roc_auc_score(yb, oofg)
    out += [f"\n## (B) GENERALIZED: anterior (FIRDA-like) vs posterior (OIRDA-like) predominance",
            f"\n- n={len(G)} (anterior/frontal {int(yb.sum())}, posterior {int((1-yb).sum())})",
            f"\n- anterior-minus-posterior delta gradient: AUROC **{auc_grad:.3f}**",
            f"\n- supervised LR on channel deviations: AUROC **{auc_sup:.3f}**\n",
            "\n_For generalized slowing, side is undefined but A-P predominance is a real, reportable axis "
            "(frontal-predominant vs posterior-predominant intermittent rhythmic delta)._\n"]
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    for lab, c in [("anterior", "#f5a623"), ("posterior", "#4a90e2")]:
        ax.hist(grad[G.ap.values == lab], bins=25, alpha=0.6, label=lab, color=c, density=True)
    ax.set_xlabel("anterior − posterior delta deviation"); ax.set_ylabel("density")
    ax.set_title(f"Generalized A–P predominance (grad AUROC {auc_grad:.2f})"); ax.legend()
    fig.tight_layout(); fig.savefig("results/figs/generalized_ap.png", dpi=130); plt.close(fig)

    Path("results/region_gated.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
