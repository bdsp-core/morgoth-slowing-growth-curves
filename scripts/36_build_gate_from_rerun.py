#!/usr/bin/env python3
"""Rebuild the recording-level GATE from the gate re-run's `_done` sidecars.

WHY. The old data/derived/gate_eeg_level.parquet was produced at a 5 s window step with Morgoth's
short-circuit guard ENABLED, so 20.6% of p_focal was spuriously set to exactly 0 (the guard zeroes a head
whose class column never clears 1/3 — EEG_level_head.py:579,677). The gate re-run recomputed the SAME two
EEG-level heads at a 1 s step with the guard DISABLED, on a real forward pass, and stored the raw sigmoids in
each recording's `_done` sidecar as p_focal_recording / p_generalized_recording. This reads those and writes a
drop-in replacement with the identical (eeg_id, p_focal, p_generalized) schema scripts/116 consumes, plus the
re-run provenance (would-the-guard-have-fired, padded-short-clip) so nothing is hidden.

ADDITIVE: writes gate_eeg_level_rerun.parquet; does NOT touch the old gate_eeg_level.parquet.

Run: python3 scripts/36_build_gate_from_rerun.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

DONE = Path("data/derived/gate_rerun_done")
OUT = Path("data/derived/gate_eeg_level_rerun.parquet")
OLD = Path("data/derived/gate_eeg_level.parquet")


def main():
    files = sorted(DONE.glob("*.done"))
    if not files:
        raise SystemExit(f"no sidecars in {DONE} — run the S3 sync first")
    rows, skipped = [], 0
    for f in files:
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            skipped += 1                          # a terminal marker ('no_v6_outputs', 'sha_mismatch')
            continue
        if "p_focal_recording" not in d:
            skipped += 1
            continue
        rows.append({
            "eeg_id": d["eeg_id"],
            "p_focal": float(d["p_focal_recording"]),
            "p_generalized": float(d["p_generalized_recording"]),
            "guard_would_fire_focal": bool(d.get("guard_would_fire_focal_recording", False)),
            "guard_would_fire_gen": bool(d.get("guard_would_fire_gen_recording", False)),
            "recording_padded": bool(d.get("recording_padded", False)),
            "n_windows": int(d.get("n_windows", 0)),
            "gate_step_s": int(d.get("gate_step_s", -1)),
        })
    G = pd.DataFrame(rows).drop_duplicates("eeg_id").reset_index(drop=True)
    assert (G.gate_step_s == 1).all(), "every sidecar must be the 1 s re-run"
    G.to_parquet(OUT, index=False)

    zf = (G.p_focal == 0).mean()
    zg = (G.p_generalized == 0).mean()
    print(f"wrote {OUT}  ({len(G):,} recordings, {skipped:,} terminal-marker sidecars skipped)")
    print(f"  p_focal       : exactly-0 {100*zf:.2f}%   range [{G.p_focal.min():.3f}, {G.p_focal.max():.3f}]")
    print(f"  p_generalized : exactly-0 {100*zg:.2f}%   range [{G.p_generalized.min():.3f}, {G.p_generalized.max():.3f}]")
    print(f"  padded short clips: {G.recording_padded.sum():,}   "
          f"guard WOULD have zeroed focal on {G.guard_would_fire_focal.sum():,} recordings")

    if OLD.exists():
        O = pd.read_parquet(OLD)[["eeg_id", "p_focal", "p_generalized"]].rename(
            columns={"p_focal": "p_focal_old", "p_generalized": "p_generalized_old"})
        m = G.merge(O, on="eeg_id", how="inner")
        print(f"\nOLD vs NEW on {len(m):,} shared recordings:")
        print(f"  old p_focal exactly-0: {100*(m.p_focal_old==0).mean():.1f}%  ->  "
              f"new: {100*(m.p_focal==0).mean():.1f}%")
        rescued = m[(m.p_focal_old == 0) & (m.p_focal > 0)]
        print(f"  recordings the guard had zeroed that now carry real focal signal: {len(rescued):,}")
        if len(rescued):
            print(f"    of those, new p_focal median {rescued.p_focal.median():.3f}, "
                  f"max {rescued.p_focal.max():.3f}; "
                  f"{(rescued.p_focal>=0.5).sum():,} now exceed 0.50")
        both = m[(m.p_focal_old > 0) & (m.p_focal > 0)]
        print(f"  where both are non-zero, corr(old,new) p_focal = {both.p_focal.corr(both.p_focal_old):.3f}, "
              f"p_gen = {m.p_generalized.corr(m.p_generalized_old):.3f}")


if __name__ == "__main__":
    main()
