"""Phase v2: per-REGION x per-STAGE growth curves — focal localization WITHIN a sleep stage.

Extends scripts/10_stage_curves.py (whole_head only) to all 6 regions. Merges per-segment stages
into the segment features, takes each recording's per-(region,stage) median, fits age x sex
percentile curves per (region, stage) on NORMALS, and plots the 5 stage median curves together for
each region. Answers: given a stage, is the slowing focal (region-specific) or diffuse?

Outputs: data/derived/regional_stage_curves.parquet,
         figures/regional_stage_curves/rel_delta__<region>.png
Run: python scripts/21_regional_stage_curves.py   (after scripts/09_map_stages.py)
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from morgoth_slowing.norms import growth

OUT = Path("data/derived"); FIG = Path("figures/regional_stage_curves"); FIG.mkdir(parents=True, exist_ok=True)
FEATURES = ["rel_delta", "log_delta", "DAR", "TAR"]
REGIONS = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal", "midline", "whole_head"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
STAGE_COLORS = {"W": "#2c7fb8", "N1": "#41ab5d", "N2": "#fe9929", "N3": "#cb181d", "REM": "#6a51a3"}
PLOT_FEATURE = "rel_delta"
MIN_SEG = 3  # need >=3 segments in a (region,stage) cell to trust the recording's per-cell value


def per_recording_stage(seg, stages):
    """Per (recording, region, stage): median of each feature, plus segment count."""
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
    rec.to_parquet(OUT / "regional_stage_recording_features.parquet")

    ages = np.arange(0, 91, 1.0)
    pctl_cols = ["p3", "p10", "p25", "p50", "p75", "p90", "p97"]
    curves = []
    for region in REGIONS:
        for feat in FEATURES:
            for stage in STAGES:
                nrm = rec[(rec.region == region) & (rec.stage == stage) & (rec.label == "normal")]
                if len(nrm) < 50:
                    continue
                c = growth.fit_by_sex(nrm, feat, ages_grid=ages, bandwidth=6, min_eff_n=20)
                c["stage"] = stage; c["region"] = region
                curves.append(c)

        # figure: for the plot feature, overlay the 5 stage median curves for this region
        fig, ax = plt.subplots(figsize=(9, 5.5))
        for stage in STAGES:
            nrm = rec[(rec.region == region) & (rec.stage == stage) & (rec.label == "normal")]
            if len(nrm) < 50:
                continue
            c = growth.fit_by_sex(nrm, PLOT_FEATURE, ages_grid=ages, bandwidth=6, min_eff_n=20)
            # pool sexes for the summary plot: average M/F percentiles
            med = c.groupby("age").p50.mean()
            lo = c.groupby("age").p10.mean(); hi = c.groupby("age").p90.mean()
            ax.plot(med.index, med.values, color=STAGE_COLORS[stage], lw=2,
                    label=f"{stage} (n={nrm.bdsp_id.nunique()})")
            ax.fill_between(med.index, lo.values, hi.values, color=STAGE_COLORS[stage], alpha=0.08, lw=0)
        ax.set_title(f"{PLOT_FEATURE} — {region}: normal median by sleep stage (10–90 band)")
        ax.set_xlabel("age (years)"); ax.set_ylabel(PLOT_FEATURE); ax.grid(alpha=0.2)
        ax.legend(fontsize=8, title="stage")
        fig.tight_layout(); fig.savefig(FIG / f"{PLOT_FEATURE}__{region}.png", dpi=110); plt.close(fig)
        print("plotted", PLOT_FEATURE, region)

    if curves:
        tidy = pd.concat(curves, ignore_index=True)
        tidy = tidy[["feature", "region", "stage", "sex", "age", "n_eff"] + pctl_cols]
        tidy.to_parquet(OUT / "regional_stage_curves.parquet")
        print(f"\nwrote {OUT / 'regional_stage_curves.parquet'}: {len(tidy)} rows, "
              f"{tidy.groupby(['feature','region','stage','sex']).ngroups} (feature,region,stage,sex) cells")

    # sanity: normal median rel_delta by stage, per region (expect W < N2 < N3)
    print("\nnormal median rel_delta by stage, per region (expect W < N2 < N3):")
    for region in REGIONS:
        sub = rec[(rec.region == region) & (rec.label == "normal")]
        med = sub.groupby("stage").rel_delta.median().reindex(STAGES)
        print(f"  {region:15s} " + "  ".join(f"{s}={med[s]:.3f}" if pd.notna(med[s]) else f"{s}=NA"
                                             for s in STAGES))


if __name__ == "__main__":
    main()
