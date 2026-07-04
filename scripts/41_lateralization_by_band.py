"""Band-matched gated lateralization: lateralize focal slowing using the asymmetry of the SAME band the
slowing is in (delta / theta / both-for-mixed) — face validity + performance.

Brandon's point: if we report the slowing as theta, lateralizing it from *delta* asymmetry is incoherent
even if it happens to work. So we build band-specific L-vs-R classifiers (delta-asym, theta-asym, both)
and cross-evaluate them on delta-/theta-/mixed-predominant focal cases. The band-matched classifier
should win (or at least hold) on its own band; a combined "band-aware" predictor routes each case to the
matching features. Focal + stated side only.

Writes results/lateralization_by_band.md + results/figs/lateralization_by_band.png.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import roc_auc_score

FEATBANDS = {"delta": ["delta"], "theta": ["theta"], "both": ["delta", "theta"]}
CASEBANDS = ["delta", "theta", "mixed"]


def cols_for(asym, bands):
    return [c for c in asym.columns if c.startswith("asym_") and any(c.endswith("_" + b) for b in bands)]


def oof(asym_df, cols, y):
    X = asym_df[cols].replace([np.inf, -np.inf], np.nan).fillna(0.0).values
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, class_weight="balanced"))
    return cross_val_predict(clf, X, y, cv=5, method="predict_proba")[:, 1]


def main():
    asym = pd.read_parquet("data/derived/recording_asymmetry.parquet")
    rep = pd.read_csv("results/report_extracted_labels.csv").drop_duplicates("bdsp_id")[["bdsp_id", "side", "band"]]
    df = asym.merge(rep, on="bdsp_id")
    df = df[(df.label == "focal_slow") & df.side.isin(["left", "right"])].reset_index(drop=True)
    y = (df.side == "left").astype(int).to_numpy()
    print("focal-lateralized:", len(df), "band:", df.band.value_counts(dropna=False).to_dict())

    # OOF scores from each feature-band classifier (trained on all focal-lateralized)
    scores = {fb: oof(df, cols_for(df, bands), y) for fb, bands in FEATBANDS.items()}
    # band-aware routed predictor: delta cases use delta score, theta use theta, mixed use both
    routed = np.where(df.band == "delta", scores["delta"],
             np.where(df.band == "theta", scores["theta"], scores["both"]))

    rows = []
    for cb in CASEBANDS:
        m = (df.band == cb).to_numpy()
        if m.sum() < 15 or len(np.unique(y[m])) < 2:
            rows.append({"case_band": cb, "n": int(m.sum()), **{f"clf_{fb}": None for fb in FEATBANDS}}); continue
        rows.append({"case_band": cb, "n": int(m.sum()),
                     **{f"clf_{fb}": round(roc_auc_score(y[m], scores[fb][m]), 3) for fb in FEATBANDS}})
    tab = pd.DataFrame(rows)
    auc_routed = roc_auc_score(y, routed)
    auc_deltaonly = roc_auc_score(y, scores["delta"])

    out = ["# Band-matched lateralization (focal, L vs R)\n",
           f"n={len(df)} focal-lateralized. Rows = the case's reported band; columns = which band's "
           "asymmetry features the classifier used. AUROC for left-vs-right.\n",
           tab.to_markdown(index=False) + "\n",
           f"\n- **Band-aware routed predictor** (delta→delta, theta→theta, mixed→both): overall AUROC **{auc_routed:.3f}**",
           f"\n- Delta-only-always baseline: AUROC {auc_deltaonly:.3f}",
           "\n\n**Face validity:** on theta-predominant focal cases, the theta-asymmetry classifier "
           "should lateralize at least as well as the delta one — so the side we report is driven by the "
           "same band we call the slowing. (theta n is small; treat as indicative.)\n"]

    # plot: grouped bars per case-band
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    x = np.arange(len(CASEBANDS)); w = 0.25
    colors = {"delta": "#4a90e2", "theta": "#e0568a", "both": "#2ec4b6"}
    for i, fb in enumerate(FEATBANDS):
        vals = [tab.loc[tab.case_band == cb, f"clf_{fb}"].values[0] if (tab.case_band == cb).any() else np.nan for cb in CASEBANDS]
        vals = [v if v is not None else np.nan for v in vals]
        ax.bar(x + (i - 1) * w, vals, w, label=f"{fb}-asym clf", color=colors[fb])
    ax.axhline(0.5, ls=":", color="#aaa")
    ax.set_xticks(x); ax.set_xticklabels([f"{cb}\n(n={tab.loc[tab.case_band==cb,'n'].values[0]})" for cb in CASEBANDS])
    ax.set_ylabel("AUROC (L vs R)"); ax.set_ylim(0.4, 1.0)
    ax.set_title("Lateralization by reported band × classifier band (focal)")
    ax.legend(); ax.grid(alpha=0.25, axis="y")
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/lateralization_by_band.png", dpi=130)
    Path("results/lateralization_by_band.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
