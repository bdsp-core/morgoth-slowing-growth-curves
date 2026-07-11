"""REAL stage-stratified abnormal-vs-normal AUROC — now possible after staging the original abnormals.

Combines: staged NORMALS (segment_stages.parquet, already per-segment) + staged ABNORMALS (from
scripts/36 -> original_abnormal_stages/<rid>.csv, per-5s-window -> mapped to the 15-s feature segments),
each joined to whole-head per-segment features (segment_features.parquet). Per recording x stage we take
the median slowing metrics; then per (stage, age band) we score the summed deviation from age-matched
normals and compute AUROC (abnormal vs normal), with a Morgoth recording-level reference.

Writes results/figs/age_auroc_by_stage.png + results/age_auroc_by_stage.csv (now real).
Run: PYTHONPATH=src python scripts/38_stage_stratified_auroc.py
"""
from __future__ import annotations
import glob
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

BANDS = [(0, 18), (19, 45), (46, 60), (61, 75), (76, 100)]
STAGES = [("W", "#f5a623"), ("N2", "#4a90e2"), ("N3", "#2ec4b6"), ("REM", "#e0568a")]
CODE = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}
METRICS = ["rel_delta", "DAR", "TAR"]
SEG, STEP, FS = 3000, 2800, 200.0
NBOOT = 300


def boot(y, s, rng):
    if len(np.unique(y)) < 2 or len(y) < 15:
        return np.nan, np.nan, np.nan
    a = roc_auc_score(y, s); bs = []
    for _ in range(NBOOT):
        b = rng.choice(len(y), len(y), replace=True)
        if len(np.unique(y[b])) == 2:
            bs.append(roc_auc_score(y[b], s[b]))
    return a, (np.percentile(bs, 2.5) if bs else np.nan), (np.percentile(bs, 97.5) if bs else np.nan)


def abnormal_seg_stages():
    """Map each staged abnormal clip's 5-s pred_class windows to the 15-s feature segments."""
    rows = []
    for f in glob.glob("data/derived/original_abnormal_stages/*.csv"):
        rid = Path(f).stem; bid = rid.split("_")[0]
        pred = pd.read_csv(f).pred_class.to_numpy()
        for seg in range(len(pred) * 5 * 200 // STEP + 1):
            wi = int(((seg * STEP + SEG / 2) / FS) / 5.0)
            if 0 <= wi < len(pred):
                rows.append((bid, seg, CODE.get(int(pred[wi]), "Other")))
    return pd.DataFrame(rows, columns=["bdsp_id", "segment", "stage"])


def main():
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "age", "label"]].drop_duplicates("bdsp_id")
    feat = pd.read_parquet("data/derived/segment_features.parquet",
                           columns=["bdsp_id", "region", "segment", "rel_delta", "DAR", "TAR"])
    feat = feat[feat.region == "whole_head"].drop(columns="region")

    ss = pd.read_parquet("data/derived/segment_stages.parquet", columns=["bdsp_id", "segment", "stage"])
    if pd.api.types.is_numeric_dtype(ss.stage):
        ss["stage"] = ss.stage.map(CODE)
    stages = pd.concat([ss, abnormal_seg_stages()], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])

    df = feat.merge(stages, on=["bdsp_id", "segment"], how="inner").merge(meta, on="bdsp_id", how="inner")
    df = df[(df.age >= 0) & (df.age <= 100)].dropna(subset=["label"])
    # per recording x stage median metrics
    rec = df.groupby(["bdsp_id", "stage", "label", "age"], observed=True)[METRICS].median().reset_index()
    print("recordings x stage rows:", len(rec), "| label mix:",
          rec.drop_duplicates("bdsp_id").label.value_counts().to_dict())

    rng = np.random.default_rng(0)
    xs = [(lo + hi) / 2 for lo, hi in BANDS]
    rows = []
    fig, ax = plt.subplots(figsize=(9, 5.4))
    for stage, color in STAGES:
        sub = rec[rec.stage == stage]
        ys, los, his = [], [], []
        for lo, hi in BANDS:
            b = sub[(sub.age >= lo) & (sub.age <= hi)]
            nm = b[b.label == "normal"]
            if len(nm) < 10 or b.label.nunique() < 2:
                ys.append(np.nan); los.append(np.nan); his.append(np.nan)
                rows.append({"stage": stage, "age_band": f"{lo}-{hi}", "n": len(b), "n_abn": int((b.label != 'normal').sum()), "auroc": None}); continue
            score = np.zeros(len(b))
            for m in METRICS:
                score = score + ((b[m] - nm[m].mean()) / (nm[m].std() + 1e-9)).to_numpy()
            y = (b.label != "normal").astype(int).to_numpy()
            a, l, h = boot(y, score, rng)
            ys.append(a); los.append(l); his.append(h)
            rows.append({"stage": stage, "age_band": f"{lo}-{hi}", "n": len(b),
                         "n_abn": int(y.sum()), "auroc": None if np.isnan(a) else round(a, 3)})
        ax.plot(xs, np.array(ys, float), marker="o", color=color, lw=2, label=stage)
        ax.fill_between(xs, np.array(los, float), np.array(his, float), color=color, alpha=0.10)
    ax.axhline(0.5, ls=":", color="#aaa")
    ax.set_xlabel("Age (band midpoint)"); ax.set_ylabel("AUROC — abnormal vs normal")
    ax.set_ylim(0.4, 1.0); ax.set_title("Stage-stratified slowing detection (staged abnormals + normals)")
    ax.legend(title="sleep stage", loc="lower right"); ax.grid(alpha=0.25)
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/age_auroc_by_stage.png", dpi=130)
    pd.DataFrame(rows).to_csv("results/age_auroc_by_stage.csv", index=False)
    print(pd.DataFrame(rows).pivot(index="age_band", columns="stage", values="auroc").to_string())
    print("\nwrote results/figs/age_auroc_by_stage.png + results/age_auroc_by_stage.csv")


if __name__ == "__main__":
    main()
