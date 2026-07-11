"""End-to-end plumbing proof: read the canonical segment_master + recording_meta (eeg_id-keyed) and
produce one Table + one Figure — a stage-conditioned feature summary (the growth-curve input). Demonstrates
that analyses run off the clean-room canonical output, not legacy bdsp_id tables.

NOT a statistical result (pilot n is small) — it proves the flow: segment_master -> analysis -> Table/Figure.
Run: PYTHONPATH=src python scripts/32_segmaster_summary.py
"""
from __future__ import annotations
import glob
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SM = "data/derived/segment_master"
FEATURES = ["rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "Q_SLOWING", "SEF95"]
STAGES = ["W", "N1", "N2", "N3", "REM"]


def main():
    parts = glob.glob(f"{SM}/eeg_id=*/part.parquet")
    if not parts:
        raise SystemExit("no segment_master partitions — run scripts/31 first")
    sm = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    meta = pd.read_parquet("data/derived/recording_meta.parquet") if Path("data/derived/recording_meta.parquet").exists() else None
    wh = sm[(sm.region == "whole_head") & (~sm.artifact_flag)].copy()   # usable whole-head segments
    print(f"segment_master: {sm.eeg_id.nunique()} EEGs, {len(sm):,} rows; "
          f"usable whole-head segments: {len(wh):,}")

    # ---- Table: mean feature by stage (the stage-conditioning the norms will model) ----
    tbl = wh[wh.stage.isin(STAGES)].groupby("stage")[FEATURES].mean().reindex(STAGES).dropna(how="all")
    tbl.insert(0, "n_seg", wh[wh.stage.isin(STAGES)].groupby("stage").size().reindex(tbl.index))
    out = ["# Pilot segment_master summary (plumbing proof — analysis reads the canonical table)\n",
           f"Source: `{SM}` (eeg_id-keyed) — **{sm.eeg_id.nunique()} EEGs**, {len(sm):,} rows. "
           f"Usable whole-head segments: {len(wh):,}. *Pilot n is small; this proves the flow, not a result.*\n",
           "\n## Mean feature by sleep stage (whole_head, usable segments)\n",
           tbl.round(3).to_markdown() + "\n",
           "\n_Van Putten metrics (`Q_SLOWING`, `SEF95`) and our features (`rel_delta`, `DAR`, `TAR`) all "
           "present per segment; stage is the Morgoth per-segment call. This is exactly the input the "
           "GAMLSS norms consume (feature ~ age × stage × region)._\n"]
    Path("docs/pilot_segmaster_summary.md").write_text("\n".join(out))
    print("\n".join(out))

    # ---- Figure: DAR + Q_SLOWING by stage (stage dependence — why vigilance matching matters) ----
    ws = wh[wh.stage.isin(STAGES)]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for a, feat in zip(ax, ["DAR", "Q_SLOWING"]):
        data = [ws[ws.stage == s][feat].dropna().values for s in STAGES]
        present = [(s, d) for s, d in zip(STAGES, data) if len(d)]
        a.boxplot([d for _, d in present], tick_labels=[s for s, _ in present], showfliers=False)
        a.set_title(f"{feat} by sleep stage (pilot, whole_head)", fontsize=10, fontweight="bold")
        a.set_ylabel(feat)
    fig.suptitle(f"segment_master -> analysis -> figure  |  {sm.eeg_id.nunique()} pilot EEGs "
                 f"(plumbing proof, not a result)", fontsize=11)
    Path("figures/pilot").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig("figures/pilot/segmaster_by_stage.png", dpi=140)
    print("wrote docs/pilot_segmaster_summary.md + figures/pilot/segmaster_by_stage.png")


if __name__ == "__main__":
    main()
