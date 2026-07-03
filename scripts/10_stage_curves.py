"""Phase v2: stage-specific growth curves — how much slowing is normal in each sleep stage.

Merges per-segment stages into the segment features, takes each recording's per-stage median, fits
age x sex percentile curves per stage on NORMALS, and plots the stage medians together (W→N3 shows
the expected delta increase). Answers: is delta in N2/N3 abnormal, or just sleep?

Outputs: data/derived/stage_curves.parquet, figures/stage_curves/<feature>__<region>.png
Run: python scripts/10_stage_curves.py   (after scripts/09_map_stages.py)
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from morgoth_slowing.norms import growth

OUT = Path("data/derived"); FIG = Path("figures/stage_curves"); FIG.mkdir(parents=True, exist_ok=True)
FEATURES = ["rel_delta", "log_delta", "rel_theta", "DAR", "TAR"]
REGIONS = ["whole_head"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
STAGE_COLORS = {"W": "#2c7fb8", "N1": "#41ab5d", "N2": "#fe9929", "N3": "#cb181d", "REM": "#6a51a3"}
MIN_SEG = 3  # need >=3 segments in a stage to trust the recording's per-stage value


def per_recording_stage(seg, stages):
    seg = seg.merge(stages[["bdsp_id", "segment", "stage"]], on=["bdsp_id", "segment"], how="inner")
    g = seg.groupby(["bdsp_id", "region", "stage"])
    agg = g[FEATURES].median()
    agg["n_seg"] = g.size()
    return agg.reset_index()


def main():
    seg = pd.read_parquet(OUT / "segment_features.parquet",
                          columns=["bdsp_id", "region", "segment"] + FEATURES)
    seg = seg[seg.region.isin(REGIONS)]
    stages = pd.read_parquet(OUT / "segment_stages.parquet")
    rec = per_recording_stage(seg, stages)
    rec = rec[rec.n_seg >= MIN_SEG]
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "age", "sex", "label"]].drop_duplicates("bdsp_id")
    rec = rec.merge(meta, on="bdsp_id", how="left")
    rec = rec[rec.age.between(0, 120) & rec.sex.isin(["M", "F"])]
    rec.to_parquet(OUT / "stage_recording_features.parquet")

    ages = np.arange(0, 91, 1.0)
    curves = []
    for region in REGIONS:
        for feat in FEATURES:
            fig, ax = plt.subplots(figsize=(9, 5.5))
            for stage in STAGES:
                nrm = rec[(rec.region == region) & (rec.stage == stage) & (rec.label == "normal")]
                if len(nrm) < 50:
                    continue
                c = growth.fit_by_sex(nrm, feat, ages_grid=ages, bandwidth=6, min_eff_n=20)
                # pool sexes for the summary plot: average M/F medians
                med = c.groupby("age").p50.mean()
                lo = c.groupby("age").p10.mean(); hi = c.groupby("age").p90.mean()
                ax.plot(med.index, med.values, color=STAGE_COLORS[stage], lw=2, label=f"{stage} (n={nrm.bdsp_id.nunique()})")
                ax.fill_between(med.index, lo.values, hi.values, color=STAGE_COLORS[stage], alpha=0.08, lw=0)
                c["stage"] = stage; c["region"] = region; curves.append(c)
            ax.set_title(f"{feat} — {region}: normal median by sleep stage (10–90 band)")
            ax.set_xlabel("age (years)"); ax.set_ylabel(feat); ax.grid(alpha=0.2); ax.legend(fontsize=8, title="stage")
            fig.tight_layout(); fig.savefig(FIG / f"{feat}__{region}.png", dpi=110); plt.close(fig)
            print("plotted", feat, region)
    if curves:
        pd.concat(curves, ignore_index=True).to_parquet(OUT / "stage_curves.parquet")
    # summary: median rel_delta by stage (young vs old) to show the effect
    wh = rec[rec.region == "whole_head"]
    print("\nmedian rel_delta by stage (all normal ages):")
    print(wh[wh.label == "normal"].groupby("stage").rel_delta.median().round(3).to_string())


if __name__ == "__main__":
    main()
