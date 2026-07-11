"""End-to-end plumbing proof for the NEW canonical schema: read segment_master (per channel) + derive the
6 regions + join segment_summary + recording_meta (all eeg_id-keyed) and produce one Table + one Figure —
a stage-conditioned feature summary (the growth-curve input). Proves analyses run off the clean-room
canonical output, not legacy bdsp_id tables, AND that region derivation / summary join / ledger all work.

NOT a statistical result (pilot n is small) — it proves the flow. Also validates the schema invariants.
Run: PYTHONPATH=src python scripts/32_segmaster_summary.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from morgoth_slowing.io import canonical as C

FEATURES = ["rel_delta", "rel_theta", "rel_alpha", "log_DAR", "log_TAR"]     # per channel -> region-averaged
STAGES = ["W", "N1", "N2", "N3", "REM"]


def main():
    sm = C.load_segment_master()
    C.validate_schema(sm)                                        # per-(segment, channel) invariants
    ss = C.load_segment_summary(); C.validate_summary(ss)        # per-segment invariants
    meta = C.load_recording_meta() if Path("data/derived/recording_meta.parquet").exists() else None

    reg = C.to_regions(C.usable(sm))                             # derive 6 regions from channels (non-artifact)
    wh = reg[reg.region == "whole_head"].copy()
    n_eeg = sm.eeg_id.nunique()
    print(f"segment_master: {n_eeg} EEGs, {len(sm):,} rows ({sm.channel.nunique()} channels); "
          f"segment_summary rows: {len(ss):,}; usable whole-head segments: {len(wh):,}")

    # ---- Table: mean feature by stage (whole-head region, derived) + gate/Q_SLOWING from summary ----
    tbl = wh[wh.stage.isin(STAGES)].groupby("stage")[FEATURES].mean().reindex(STAGES).dropna(how="all")
    su = ss[~ss.artifact_flag]
    qt = su[su.stage.isin(STAGES)].groupby("stage")[["Q_SLOWING", "p_slowing"]].mean().reindex(tbl.index)
    tbl = tbl.join(qt)
    tbl.insert(0, "n_seg", su[su.stage.isin(STAGES)].groupby("stage").size().reindex(tbl.index))
    out = ["# Pilot segment_master summary (plumbing proof — new per-channel schema)\n",
           f"Source: `segment_master` (per eeg_id×segment×channel) + `segment_summary` — **{n_eeg} EEGs**, "
           f"{len(sm):,} channel-rows. Regions DERIVED via `canonical.to_regions`. "
           f"*Pilot n is small; this proves the flow, not a result.*\n",
           "\n## Mean feature by sleep stage (whole_head region, usable segments)\n",
           tbl.round(3).to_markdown() + "\n",
           "\n_`rel_*`/`log_DAR`/`log_TAR` are region-averaged from the 18 channels; `Q_SLOWING`/`p_slowing` "
           "come from `segment_summary`. This is exactly the input GAMLSS norms consume (feature ~ age × "
           "stage × region), now with channel-level detail retained upstream._\n"]
    if meta is not None:
        inc = int(meta.included.sum()) if "included" in meta else 0
        out.append(f"\n## Ledger (recording_meta): {len(meta)} intended EEGs | included {inc} | "
                   f"excluded {len(meta) - inc}. Exclusion reasons: "
                   f"{dict(meta[~meta.get('included', True)].get('exclusion_reason', pd.Series()).value_counts().head(6)) if 'included' in meta else 'n/a'}\n")
    Path("docs/pilot_segmaster_summary.md").write_text("\n".join(out))
    print("\n".join(out))

    # ---- Figure: log_DAR (region) + Q_SLOWING (summary) by stage ----
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ws = wh[wh.stage.isin(STAGES)]
    for a, (feat, src) in zip(ax, [("log_DAR", ws), ("Q_SLOWING", su[su.stage.isin(STAGES)])]):
        data = [src[src.stage == s][feat].dropna().values for s in STAGES]
        present = [(s, d) for s, d in zip(STAGES, data) if len(d)]
        a.boxplot([d for _, d in present], tick_labels=[s for s, _ in present], showfliers=False)
        a.set_title(f"{feat} by sleep stage (pilot)", fontsize=10, fontweight="bold"); a.set_ylabel(feat)
    fig.suptitle(f"segment_master (per-channel) -> regions -> figure  |  {n_eeg} pilot EEGs "
                 f"(plumbing proof, not a result)", fontsize=11)
    Path("figures/pilot").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig("figures/pilot/segmaster_by_stage.png", dpi=140)
    print("wrote docs/pilot_segmaster_summary.md + figures/pilot/segmaster_by_stage.png")


if __name__ == "__main__":
    main()
