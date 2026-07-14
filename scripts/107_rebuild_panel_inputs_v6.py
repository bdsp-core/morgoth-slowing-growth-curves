#!/usr/bin/env python3
"""Rebuild the panel inputs that scripts 103/104/105 need — from the v6 run, not the legacy tables.

BACKGROUND. Scripts 103 (sparse slowing score), 104 (its external validation on the occasion-noise panel)
and 105 (the two-stage gate-then-quantify figure) all failed after the legacy derived tables were
quarantined. Their manuscript figures (`sparse_score.png`, `sparse_score_external.png`,
`two_stage_gate_and_quantify.png`) were therefore stale or missing outright.

The clean-room rule is "no reuse of legacy DERIVED tables". It is not "no reuse of inputs". So:

  RESTORED AS-IS (genuine inputs, no model or feature output in them):
    excluded_bdsp_ids.parquet    350 curated patient exclusions (bdsp_id, n_recordings, reason)
    occasion_expert_votes.parquet  1,604 RAW human rater votes — the ground truth the ceiling is measured
                                   against. Rebuilding these is not possible and not desirable.

  REBUILT FROM v6 (these ARE derived, so the legacy copies are discarded):
    occasion_features.parquet      panel spectral features <- v6 channel_stage_features (the 100 panel
                                   recordings went through the same fleet run as everything else).
                                   Only `age`/`sex` are carried over from the legacy table: the panel EDFs
                                   are de-identified (`ON_*`) and carry no demographics anywhere else in
                                   the repo. These panel ages are WHOLE YEARS — the only age source that
                                   exists for them — and are marked as such.
    occasion_morgoth_preds.parquet Morgoth's panel predictions <- panel_v6_scores.parquet (v6 gate):
                                   axis FN <- p_focal, axis GN <- p_generalized.

Run: PYTHONPATH=src python scripts/107_rebuild_panel_inputs_v6.py
"""
from pathlib import Path
import numpy as np, pandas as pd

Q = Path("data/derived/_legacy_quarantine")
D = Path("data/derived")
STAGES_KEEP = None   # keep every stage; 103/104/105 filter themselves


def main():
    # ---------------------------------------------------------------- restore genuine inputs
    for f in ["excluded_bdsp_ids.parquet", "occasion_expert_votes.parquet"]:
        d = pd.read_parquet(Q / f)
        d.to_parquet(D / f, index=False)
        print(f"restored (input)  {f:32s} {d.shape}")

    # ---------------------------------------------------------------- panel demographics (age/sex only)
    legacy = pd.read_parquet(Q / "occasion_features.parquet")
    demo = legacy[["fid", "age", "sex"]].drop_duplicates("fid")
    demo["fid"] = demo.fid.astype(int)
    print(f"\npanel demographics from legacy: {len(demo)} recordings, "
          f"age known {demo.age.notna().sum()} (WHOLE YEARS — only source that exists for ON_* EDFs)")

    # ---------------------------------------------------------------- v6 panel features
    csf = pd.read_parquet(D / "channel_stage_features.parquet")
    panel = csf[csf.bdsp_id.astype(str).str.startswith("ON_")].copy()
    panel["fid"] = panel.bdsp_id.astype(str).str.split("_").str[1].astype(int)
    panel = panel.drop(columns=[c for c in ("age", "sex", "clean_normal", "clean_pair", "is_abnormal",
                                            "patient_id", "src", "bdsp_id") if c in panel.columns])
    panel = panel.merge(demo, on="fid", how="left")
    n_leg = len(legacy)
    occ = panel.rename(columns={"fid": "fid"})
    occ.to_parquet(D / "occasion_features.parquet", index=False)
    print(f"rebuilt  (v6)     occasion_features.parquet        {occ.shape}   "
          f"[legacy was {n_leg} rows] | recordings={occ.fid.nunique()} | age known "
          f"{int(occ.age.notna().sum()):,}/{len(occ):,}")

    # ---------------------------------------------------------------- v6 Morgoth panel predictions
    pv = pd.read_parquet(D / "panel_v6_scores.parquet")
    rows = []
    for axis, col in [("FN", "p_focal"), ("GN", "p_generalized")]:
        s = pv[["fid", col]].rename(columns={col: "M_pred"}).copy()
        s["axis"] = axis
        s["M_pred_class"] = (s.M_pred >= 0.5).astype(int)
        rows.append(s)
    mp = pd.concat(rows, ignore_index=True)[["fid", "axis", "M_pred", "M_pred_class"]]
    mp["fid"] = mp.fid.astype(int)
    mp.to_parquet(D / "occasion_morgoth_preds.parquet", index=False)
    print(f"rebuilt  (v6)     occasion_morgoth_preds.parquet   {mp.shape}   "
          f"[FN<-p_focal, GN<-p_generalized from the v6 gate]")
    print(f"   M_pred range: FN {mp[mp.axis=='FN'].M_pred.min():.3f}–{mp[mp.axis=='FN'].M_pred.max():.3f} | "
          f"GN {mp[mp.axis=='GN'].M_pred.min():.3f}–{mp[mp.axis=='GN'].M_pred.max():.3f}")


if __name__ == "__main__":
    main()
