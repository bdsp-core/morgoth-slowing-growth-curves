"""How well do we identify the SLOWING LOCATION (region + side) vs the clinical report?

Compares our generated statement's region/side (parsed from final_report.report) against the report's
region/side (report_extracted_labels.csv), on recordings where BOTH state a location. Produces:
  - region confusion matrix (heatmap) + per-region precision/recall/F1 + accuracy
  - side confusion matrix (L/R/bilateral) + accuracy
  -> results/figs/region_confusion.png, region_f1.png, side_confusion.png ; results/region_eval.md
Run: PYTHONPATH=src python scripts/35_region_eval.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score

_s = importlib.util.spec_from_file_location("s18", str(Path("scripts/18_report_agreement.py")))
s18 = importlib.util.module_from_spec(_s); _s.loader.exec_module(s18)

REGIONS = ["frontal", "temporal", "central", "parietal", "occipital"]
SIDES = ["left", "right", "bilateral"]


def heatmap(cm, labels, title, path, cmap="Blues"):
    cmn = cm / cm.sum(axis=1, keepdims=True).clip(min=1)      # row-normalized (recall)
    fig, ax = plt.subplots(figsize=(1.3 + 1.1 * len(labels), 1.1 + 1.0 * len(labels)))
    im = ax.imshow(cmn, cmap=cmap, vmin=0, vmax=1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
    ax.set_xlabel("our prediction"); ax.set_ylabel("report (reference)"); ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center",
                    color="white" if cmn[i, j] > 0.5 else "#333", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, label="row-normalized (recall)")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    rep = pd.read_csv("results/report_extracted_labels.csv")[["bdsp_id", "region", "side"]].rename(
        columns={"region": "region_rep", "side": "side_rep"})
    fr = pd.read_parquet("data/derived/final_report.parquet")[["bdsp_id", "report"]]
    ours = fr.report.map(s18.parse_report)
    fr = fr.assign(region_our=[p["region"] for p in ours], side_our=[p["side"] for p in ours])
    df = rep.merge(fr, on="bdsp_id", how="inner")

    out = ["# Region / side identification vs clinical reports\n"]
    Path("results/figs").mkdir(parents=True, exist_ok=True)

    # ---- REGION ----
    r = df.dropna(subset=["region_rep", "region_our"])
    r = r[r.region_rep.isin(REGIONS) & r.region_our.isin(REGIONS)]
    if len(r):
        cm = confusion_matrix(r.region_rep, r.region_our, labels=REGIONS)
        acc = accuracy_score(r.region_rep, r.region_our)
        p, rec, f1, sup = precision_recall_fscore_support(r.region_rep, r.region_our, labels=REGIONS, zero_division=0)
        heatmap(cm, REGIONS, f"Region confusion (n={len(r)}, acc={acc:.2f})", "results/figs/region_confusion.png")
        # per-region F1 bar
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(REGIONS, f1, color="#4a90e2")
        for i, (v, s) in enumerate(zip(f1, sup)):
            ax.text(i, v + 0.02, f"{v:.2f}\n(n={s})", ha="center", fontsize=8)
        ax.set_ylim(0, 1.05); ax.set_ylabel("F1"); ax.set_title(f"Per-region F1 (overall acc={acc:.2f}, n={len(r)})")
        fig.tight_layout(); fig.savefig("results/figs/region_f1.png", dpi=130); plt.close(fig)
        out += [f"\n## Region (n={len(r)} with region stated by both) — accuracy **{acc:.3f}**\n",
                pd.DataFrame({"region": REGIONS, "precision": p.round(3), "recall": rec.round(3),
                              "f1": f1.round(3), "n": sup}).to_markdown(index=False) + "\n"]
    else:
        out.append("\n## Region: no overlap\n")

    # ---- SIDE ----
    s = df.dropna(subset=["side_rep", "side_our"])
    s = s[s.side_rep.isin(SIDES) & s.side_our.isin(SIDES)]
    if len(s):
        cm = confusion_matrix(s.side_rep, s.side_our, labels=SIDES)
        acc = accuracy_score(s.side_rep, s.side_our)
        p, rec, f1, sup = precision_recall_fscore_support(s.side_rep, s.side_our, labels=SIDES, zero_division=0)
        heatmap(cm, SIDES, f"Side confusion (n={len(s)}, acc={acc:.2f})", "results/figs/side_confusion.png", cmap="Purples")
        out += [f"\n## Side (n={len(s)}) — accuracy **{acc:.3f}**\n",
                pd.DataFrame({"side": SIDES, "precision": p.round(3), "recall": rec.round(3),
                              "f1": f1.round(3), "n": sup}).to_markdown(index=False) + "\n"]
    out.append("\n_Note: comparison is limited to recordings where both our statement and the report "
               "explicitly state a location; region is the sparser of the two. Expands with the ingestion._\n")
    Path("results/region_eval.md").write_text("\n".join(out))
    print("\n".join(out))
    print("\nwrote results/region_eval.md + figs")


if __name__ == "__main__":
    main()
