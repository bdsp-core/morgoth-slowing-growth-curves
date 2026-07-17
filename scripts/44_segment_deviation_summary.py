#!/usr/bin/env python3
"""SECTION 2d — summarize the per-segment deviation field (scripts/43 output).

Shows that every segment now carries a stage-appropriate deviation z, and that the field is (a) CALIBRATED
per stage — clean-normal segments centre near z=0 in every sleep stage — and (b) DISCRIMINATIVE — abnormal
recordings' segments are shifted positive. Uses whole-head deviation for the three most discriminating
UP-features (log_delta, log_TAR, log_DAR).

Reads a sample of data/derived/segment_deviation/ partitions (per-segment z) + recording_labels_sap.
Writes figures/story/s2_segment_deviation.png + results/story/s2_segment_deviation.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/44_segment_deviation_summary.py [--n 3000]
"""
from __future__ import annotations
import argparse, glob, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEV = "data/derived/segment_deviation"
STAGES = ["W", "N1", "N2", "N3", "REM"]
FEATS = [("z__whole_head__log_delta", "delta excess"),
         ("z__whole_head__log_TAR", "theta/alpha ratio"),
         ("z__whole_head__log_DAR", "delta/alpha ratio")]
FIG = Path("figures/story"); RES = Path("results/story")


def read_one(args):
    eid, cols = args
    f = f"{DEV}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        return None
    try:
        d = pd.read_parquet(f, columns=["stage"] + cols)
    except Exception:
        return None
    d["eeg_id"] = eid
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=3000); a = ap.parse_args()
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    have = [p.split("eeg_id=")[1].split("/")[0] for p in glob.glob(f"{DEV}/eeg_id=*")]
    lab = lab[lab.eeg_id.isin(have)]
    cn = lab[(lab.clean_normal == True)].eeg_id.tolist()                          # noqa: E712
    ab = lab[(lab.is_abnormal == True)].eeg_id.tolist()                           # noqa: E712
    rng = np.random.default_rng(0)
    cn = list(rng.choice(cn, min(a.n, len(cn)), replace=False))
    ab = list(rng.choice(ab, min(a.n, len(ab)), replace=False))
    cols = [c for c, _ in FEATS]
    print(f"reading {len(cn)} clean-normal + {len(ab)} abnormal recordings ...", flush=True)
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4))) as ex:
        cn_d = pd.concat([d for d in ex.map(read_one, [(i, cols) for i in cn]) if d is not None])
        ab_d = pd.concat([d for d in ex.map(read_one, [(i, cols) for i in ab]) if d is not None])

    md = ["# Section 2d — per-segment deviation field (stage-appropriate)\n",
          "Each segment carries a deviation z per feature × region, scored against its own (sleep-stage, "
          "age) normal. Below: whole-head median segment-z by sleep stage — clean-normal (should sit ~0, "
          "confirming per-stage calibration) vs abnormal (shifted positive).\n",
          "| feature | group | " + " | ".join(STAGES) + " |", "|---|---|" + "---|" * len(STAGES)]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
    for j, (col, label) in enumerate(FEATS):
        ax = axes[j]
        for grp, D, color in [("clean-normal", cn_d, "#2c7fb8"), ("abnormal", ab_d, "#c8443c")]:
            meds, q1s, q3s = [], [], []
            for st in STAGES:
                v = D[D.stage == st][col].replace([np.inf, -np.inf], np.nan).dropna()
                meds.append(v.median() if len(v) else np.nan)
                q1s.append(v.quantile(.25) if len(v) else np.nan)
                q3s.append(v.quantile(.75) if len(v) else np.nan)
            x = np.arange(len(STAGES)) + (0.12 if grp == "abnormal" else -0.12)
            ax.errorbar(x, meds, yerr=[np.array(meds) - np.array(q1s), np.array(q3s) - np.array(meds)],
                        fmt="o", color=color, capsize=3, label=grp, ms=6)
            md.append(f"| {label} | {grp} | " + " | ".join(f"{m:+.2f}" for m in meds) + " |")
        ax.axhline(0, ls="--", color="#888", lw=1)
        ax.set_xticks(range(len(STAGES))); ax.set_xticklabels(STAGES)
        ax.set_title(label, fontsize=10); ax.grid(alpha=.2)
        if j == 0:
            ax.set_ylabel("per-segment deviation z (median, IQR)")
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle("Per-segment deviation field is stage-calibrated (normals ~0) and discriminative "
                 "(abnormals shifted up) — whole head", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "s2_segment_deviation.png", dpi=150); plt.close(fig)
    (RES / "s2_segment_deviation.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s2_segment_deviation.png + results/story/s2_segment_deviation.md")


if __name__ == "__main__":
    main()
