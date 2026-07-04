"""Band-conditioned, antisymmetric lateralizer — the consolidated method (Brandon's two ideas).

- ANTISYMMETRIC: features are signed asymmetries, so L/R mirror = negate. We train with no intercept on
  flip-augmented data => f(-x)=1-f(x) exactly (no left prior; sign-audit passes).
- BAND-CONDITIONED with multi-band inputs: dominant band (delta/theta/mixed) modulates the weights via
  asym x dominant-band INTERACTION terms (no band main effects — those would be per-band priors and
  would break antisymmetry). Inputs always include BOTH delta and theta asymmetries. This gives a
  band-specific model that still reads all bands — face validity + full statistical power (no
  fragmentation, so the tiny theta stratum borrows strength).
Grouped CV (a recording never appears mirrored across folds; mirrors are added only within the train
fold). Reports AUROC + balanced accuracy + per-side recall per dominant-band stratum.
Run: PYTHONPATH=src python scripts/44_lateralizer_band_conditioned.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, recall_score


def build():
    asym = pd.read_parquet("data/derived/recording_asymmetry.parquet")
    rep = pd.read_csv("results/report_extracted_labels.csv").drop_duplicates("bdsp_id")[["bdsp_id", "side", "band"]]
    df = asym.merge(rep, on="bdsp_id")
    df = df[(df.label == "focal_slow") & df.side.isin(["left", "right"])].reset_index(drop=True)
    acols = [c for c in df.columns if c.startswith("asym_") and (c.endswith("delta") or c.endswith("theta"))]
    A = df[acols].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    band = df.band.fillna("mixed").to_numpy()
    # dominant-band one-hots (flip-invariant); interaction = asym * onehot
    doms = ["delta", "theta", "mixed"]
    onehot = np.stack([(band == d).astype(float) for d in doms], axis=1)   # (n,3)
    inter = np.concatenate([A * onehot[:, [k]] for k in range(len(doms))], axis=1)  # asym x dom
    X = np.concatenate([A, inter], axis=1)                                 # base + conditioned
    y = (df.side == "left").astype(int).to_numpy()
    return X, y, band


def cv_eval(X, y, seed=0):
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    oof = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        Xtr = np.vstack([X[tr], -X[tr]]); ytr = np.concatenate([y[tr], 1 - y[tr]])   # flip-aug in-fold
        sc = StandardScaler(with_mean=False).fit(Xtr)                                 # antisymmetric: no centering
        clf = LogisticRegression(max_iter=8000, C=0.5, fit_intercept=False).fit(sc.transform(Xtr), ytr)
        oof[te] = clf.predict_proba(sc.transform(X[te]))[:, 1]
    return oof


def main():
    X, y, band = build()
    oof = cv_eval(X, y)
    pred = (oof >= 0.5).astype(int)
    rows = [{"stratum": "ALL", "n": len(y), "auroc": round(roc_auc_score(y, oof), 3),
             "bal_acc": round(balanced_accuracy_score(y, pred), 3),
             "recall_L": round(recall_score(y, pred, pos_label=1), 3),
             "recall_R": round(recall_score(y, pred, pos_label=0), 3)}]
    for d in ["delta", "theta", "mixed"]:
        m = band == d
        if m.sum() >= 15 and len(np.unique(y[m])) == 2:
            rows.append({"stratum": d, "n": int(m.sum()), "auroc": round(roc_auc_score(y[m], oof[m]), 3),
                         "bal_acc": round(balanced_accuracy_score(y[m], pred[m]), 3),
                         "recall_L": round(recall_score(y[m], pred[m], pos_label=1), 3),
                         "recall_R": round(recall_score(y[m], pred[m], pos_label=0), 3)})
    tab = pd.DataFrame(rows)
    out = ["# Band-conditioned antisymmetric lateralizer (focal, L vs R)\n",
           "Antisymmetric (flip-augmented, no-intercept) + dominant-band×asymmetry interactions; multi-band "
           "inputs; grouped CV. Per dominant-band stratum:\n",
           tab.to_markdown(index=False) + "\n",
           "\n_Balanced left/right recall (no left prior), band-specific behavior, and the tiny theta "
           "stratum borrows strength from the shared backbone. This is the model to wire into the report "
           "generator; the reader sees only band-matched deviation magnitudes, not any of this._\n"]
    Path("results/lateralizer_band_conditioned.md").write_text("\n".join(out))
    print(tab.to_string(index=False))


if __name__ == "__main__":
    main()
