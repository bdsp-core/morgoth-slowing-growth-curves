"""Fix oversight #4: DATA-DRIVEN region/side localization (replaces the temporal-defaulting text rule).

Predicted region = the lobe with the largest slowing deviation from age-matched normals, where lobes are
built from the per-bipolar-channel features (recording_features.parquet). Predicted side = from the
left-vs-right slowing deviation. Evaluated against the report's region/side (report_extracted_labels.csv)
on abnormal recordings, with ROW-NORMALIZED confusion matrices + per-region precision/recall/F1.

Writes results/figs/region_confusion_pred.png, side_confusion_pred.png ; results/region_pred_eval.md
Run: PYTHONPATH=src python scripts/37_region_predictor.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score

# lobe -> representative bipolar channels (double banana)
LOBES = {
    "frontal":   ["Fp1-F3", "Fp2-F4", "Fp1-F7", "Fp2-F8"],
    "temporal":  ["F7-T3", "T3-T5", "F8-T4", "T4-T6"],
    "central":   ["F3-C3", "F4-C4", "Fz-Cz"],
    "parietal":  ["C3-P3", "C4-P4", "Cz-Pz"],
    "occipital": ["T5-O1", "T6-O2", "P3-O1", "P4-O2"],
}
LEFT = {"Fp1-F3", "Fp1-F7", "F7-T3", "T3-T5", "F3-C3", "C3-P3", "T5-O1", "P3-O1"}
RIGHT = {"Fp2-F4", "Fp2-F8", "F8-T4", "T4-T6", "F4-C4", "C4-P4", "T6-O2", "P4-O2"}
REGIONS = list(LOBES); SIDES = ["left", "right", "bilateral"]
AGE_BINS = [0, 18, 45, 60, 75, 120]
METRIC = "DAR"                                  # delta/alpha ratio: slowing-direction, robust


def heatmap(cm, labels, title, path, cmap="Blues"):
    n_row = cm.sum(axis=1, keepdims=True); cmn = cm / n_row.clip(min=1)
    ylab = [f"{l} (n={int(n)})" for l, n in zip(labels, n_row.ravel())]
    fig, ax = plt.subplots(figsize=(1.7 + 1.1 * len(labels), 1.3 + 1.0 * len(labels)))
    im = ax.imshow(cmn, cmap=cmap, vmin=0, vmax=1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(ylab)
    ax.set_xlabel("our prediction (max-deviation lobe)"); ax.set_ylabel("report (reference)"); ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center",
                    color="white" if cmn[i, j] > 0.5 else "#333", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, label="row-normalized")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    rf = pd.read_parquet("data/derived/recording_features.parquet")
    ch = rf[rf.region.isin(set().union(*LOBES.values()))].copy()
    ch["ageband"] = pd.cut(pd.to_numeric(ch.age, errors="coerce"), bins=AGE_BINS)
    # per-channel deviation vs age-matched normals (z of the slowing metric)
    norm = ch[ch.label == "normal"].groupby(["region", "ageband"], observed=True)[METRIC].agg(["mean", "std"])
    ch = ch.join(norm, on=["region", "ageband"])
    ch["z"] = (ch[METRIC] - ch["mean"]) / (ch["std"] + 1e-9)
    # lobe score per recording = mean channel-z in that lobe; side = mean z over left vs right channels
    piv = ch.pivot_table(index="bdsp_id", columns="region", values="z")
    lobe_score = pd.DataFrame({lobe: piv[[c for c in chans if c in piv.columns]].mean(axis=1)
                               for lobe, chans in LOBES.items()})
    pred_region = lobe_score.idxmax(axis=1)
    zL = piv[[c for c in LEFT if c in piv.columns]].mean(axis=1)
    zR = piv[[c for c in RIGHT if c in piv.columns]].mean(axis=1)
    d = (zL - zR)
    pred_side = pd.Series(np.where(d > 0.5, "left", np.where(d < -0.5, "right", "bilateral")), index=piv.index)

    rep = pd.read_csv("results/report_extracted_labels.csv")
    rep = rep[rep.label != "normal"].drop_duplicates("bdsp_id").set_index("bdsp_id")
    P = pd.DataFrame({"pred_region": pred_region, "pred_side": pred_side}).join(
        rep[["region", "side"]], how="inner")

    Path("results/figs").mkdir(parents=True, exist_ok=True)
    out = ["# Data-driven region/side localization (max-deviation lobe) vs reports\n",
           f"Predictor: lobe with max age-matched {METRIC} deviation. Abnormal recordings only.\n"]
    # region
    r = P.dropna(subset=["region", "pred_region"]); r = r[r.region.isin(REGIONS)]
    if len(r):
        cm = confusion_matrix(r.region, r.pred_region, labels=REGIONS)
        acc = accuracy_score(r.region, r.pred_region)
        p, rc, f1, sup = precision_recall_fscore_support(r.region, r.pred_region, labels=REGIONS, zero_division=0)
        heatmap(cm, REGIONS, f"Region (data-driven) n={len(r)} acc={acc:.2f}", "results/figs/region_confusion_pred.png")
        out += [f"\n## Region — accuracy {acc:.3f}, macro-F1 {f1.mean():.3f} (n={len(r)})\n",
                pd.DataFrame({"region": REGIONS, "precision": p.round(3), "recall": rc.round(3),
                              "f1": f1.round(3), "n_report": sup}).to_markdown(index=False) + "\n"]
    # side
    s = P.dropna(subset=["side", "pred_side"]); s = s[s.side.isin(SIDES)]
    if len(s):
        cm = confusion_matrix(s.side, s.pred_side, labels=SIDES)
        acc = accuracy_score(s.side, s.pred_side)
        p, rc, f1, sup = precision_recall_fscore_support(s.side, s.pred_side, labels=SIDES, zero_division=0)
        heatmap(cm, SIDES, f"Side (data-driven) n={len(s)} acc={acc:.2f}", "results/figs/side_confusion_pred.png", "Purples")
        out += [f"\n## Side — accuracy {acc:.3f} (n={len(s)})\n",
                pd.DataFrame({"side": SIDES, "precision": p.round(3), "recall": rc.round(3),
                              "f1": f1.round(3), "n_report": sup}).to_markdown(index=False) + "\n"]
    out.append("\n_Predicts a specific lobe for every recording (no temporal default), so per-region "
               "recall is now meaningful. Deviation is age-band-matched vs normals per channel._\n")
    Path("results/region_pred_eval.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
