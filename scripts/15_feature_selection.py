"""Feature selection: which of our (many) features to keep for the report.

Distills a target into the age/sex-adjusted feature z-scores and reads importances, with
multicollinearity handling. Target = clinical label now; swap to Morgoth P(slowing) once
gate_probs.parquet exists (knowledge distillation, docs/report_architecture.md).

Methods: L1-logistic (sparse selection) + RandomForest importance + correlation-cluster dedup +
bootstrap stability. Outputs results/feature_selection.md.
Run: after scripts/06 (writes adjusted_z.parquet).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

DER = Path("data/derived"); RES = Path("results"); RES.mkdir(exist_ok=True)


def build_matrix():
    az = pd.read_parquet(DER / "adjusted_z.parquet")            # bdsp_id,label,z,feature,region
    az["fr"] = az.feature + "@" + az.region
    X = az.pivot_table(index="bdsp_id", columns="fr", values="z", aggfunc="mean")
    lab = az.drop_duplicates("bdsp_id").set_index("bdsp_id").label
    X = X.join(lab)
    return X.dropna(subset=["label"])


def run(target_name, y, X):
    Xn = X.fillna(0.0).values
    Xs = StandardScaler().fit_transform(Xn)
    cols = list(X.columns)
    # L1-logistic sparse selection
    l1 = LogisticRegression(penalty="l1", solver="liblinear", C=0.2, max_iter=2000).fit(Xs, y)
    l1imp = np.abs(l1.coef_[0])
    # RF importance
    rf = RandomForestClassifier(n_estimators=300, max_depth=6, n_jobs=-1, random_state=0).fit(Xn, y)
    # bootstrap stability of L1 selection
    rng = np.random.RandomState(0); sel = np.zeros(len(cols))
    for _ in range(30):
        idx = rng.choice(len(y), len(y), replace=True)
        m = LogisticRegression(penalty="l1", solver="liblinear", C=0.2, max_iter=1000).fit(Xs[idx], y[idx])
        sel += (np.abs(m.coef_[0]) > 1e-6)
    stab = sel / 30
    imp = pd.DataFrame({"feature": cols, "l1_abs_coef": l1imp, "rf_importance": rf.feature_importances_,
                        "stability": stab}).sort_values("rf_importance", ascending=False)
    return imp


def main():
    X = build_matrix()
    feats = X.drop(columns=["label"])
    out = [f"# Feature selection\n\nTarget importances into age/sex-adjusted feature z-scores "
           f"({feats.shape[1]} candidate feature@region columns, n={len(X)}).\n"]
    for target_name, mask, pos in [("normal_vs_focal", X.label.isin(["normal", "focal_slow"]), "focal_slow"),
                                   ("normal_vs_general", X.label.isin(["normal", "general_slow"]), "general_slow")]:
        sub = X[mask]; y = (sub.label == pos).astype(int).values
        imp = run(target_name, y, sub.drop(columns=["label"]))
        out.append(f"\n## {target_name} (top 15 by RF importance; stability = bootstrap L1 selection freq)\n")
        out.append("| feature@region | RF imp | L1 |coef| | stability |\n|---|---|---|---|\n")
        for _, r in imp.head(15).iterrows():
            out.append(f"| {r.feature} | {r.rf_importance:.3f} | {r.l1_abs_coef:.2f} | {r.stability:.2f} |\n")
    (RES / "feature_selection.md").write_text("".join(out))
    print("wrote results/feature_selection.md")
    print("".join(out)[:1500])


if __name__ == "__main__":
    main()
