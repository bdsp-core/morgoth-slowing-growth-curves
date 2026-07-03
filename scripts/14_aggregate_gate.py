"""Aggregate Morgoth gate window-predictions -> per-recording probabilities.

The orchestrator runs the window-level heads (NORMAL.pth, SLOWING.pth) over each raw recording,
writing per-window CSVs. We aggregate to one probability per recording (mean of the abnormal/slowing
probability across windows) as the gate. (The official EEG-level aggregators can replace this later.)

Outputs: data/derived/gate_probs.parquet (bdsp_id, label, p_abnormal, p_slowing)
Run: after the gate orchestrator finishes.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from morgoth_slowing.io import segments as seg_io

DER = Path("data/derived")
GROUPS = {"normal": "normal", "focal": "focal_slow", "general": "general_slow"}


def prob_column(df):
    """Pick the abnormal/slowing probability column from a window CSV."""
    if "pred" in df.columns:                       # NORMAL/SLOWING window: single prob column
        return df["pred"].astype(float)
    # multi-class: use 1 - class_0 (class_0 = normal/none) as abnormal prob
    probs = [c for c in df.columns if c.startswith("class_") and c.endswith("_prob")]
    if probs:
        return 1.0 - df[sorted(probs)[0]].astype(float)
    return df.iloc[:, -1].astype(float)


def aggregate(tag):
    rows = {}
    for grp in GROUPS:
        d = DER / tag / grp
        for csv in d.glob("sub-*.csv") if d.exists() else []:
            try:
                bid = seg_io.parse_filename(csv)["bdsp_id"]
                rows[bid] = float(np.nanmean(prob_column(pd.read_csv(csv))))
            except Exception:
                pass
    return rows


def main():
    pab = aggregate("gate_NORMAL")     # P(abnormal)
    psl = aggregate("gate_SLOWING")    # P(slowing)
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "label"]].drop_duplicates("bdsp_id")
    df = meta.copy()
    df["p_abnormal"] = df.bdsp_id.map(pab)
    df["p_slowing"] = df.bdsp_id.map(psl)
    df.to_parquet(DER / "gate_probs.parquet")
    print("recordings with gate probs:", df.p_slowing.notna().sum(), "/", len(df))
    for lab in ["normal", "focal_slow", "general_slow"]:
        g = df[df.label == lab]
        print(f"  {lab}: P(abnormal) med {g.p_abnormal.median():.3f} | P(slowing) med {g.p_slowing.median():.3f}")


if __name__ == "__main__":
    main()
