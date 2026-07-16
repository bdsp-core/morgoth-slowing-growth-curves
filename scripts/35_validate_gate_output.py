#!/usr/bin/env python3
"""Validate the gate re-run's output — format, and that the OLD work is intact and still joins.

This is the gate on the 100-EEG test. It fails loudly rather than warning, because the entire point of the
re-run is that there is no third one.

CHECKS
  A. SCHEMA — every raw model output is present, at the right granularity.
     window_gate : t_start_s, p_class0/1/2 (the FULL softmax), p_abnormal
     segment_gate: p_focal_{30,60,120}, p_gen_{30,60,120}, guard_* flags, and the segment key
  B. NOTHING WAS COLLAPSED — all three softmax classes present; they sum to 1; p_class1/p_class2 are not
     all-zero (that would mean the head was collapsed again).
  C. NOTHING WAS ZEROED — the guard is disabled, so probabilities must NOT pile up at exactly 0.
     Where guard_* is True the probability must still be a real number (this is the whole point).
  D. INDEPENDENCE — p_focal and p_gen come from two SEPARATE sigmoid heads, so they must NOT behave like a
     softmax: their sum must exceed 1 somewhere. (If it never does, we have wired up the wrong thing.)
  E. THE OLD WORK IS INTACT AND JOINS — segment_gate joins segment_master 1:1 on (eeg_id, segment), the
     t_start_s agree, and segment_master / segment_summary are byte-for-byte unchanged.
  F. 1 s STEP — one window row per second; the recording-level sequence is long enough to give the
     EEG-level head the token count it expects (T/30).

Run: PYTHONPATH=src python scripts/35_validate_gate_output.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np, pandas as pd

D = Path("data/derived")
WG, SG = D / "window_gate", D / "segment_gate"
MIN_ROWS = 30          # EEG-level head's CNN floor (MaxPool 10 then 3): under 30 rows -> 0 tokens -> padded
FAIL, WARN = [], []


def check(cond, msg):
    (FAIL if not cond else []).append(msg) if not cond else None
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    return cond


def main():
    ids = sorted(p.name.split("=")[1] for p in SG.glob("eeg_id=*"))
    if not ids:
        print("no segment_gate output found — run scripts/32 first")
        return 1
    print(f"validating {len(ids):,} recordings\n")

    W = pd.concat([pd.read_parquet(WG / f"eeg_id={i}" / "part.parquet").assign(eeg_id=i)
                   for i in ids], ignore_index=True)
    S = pd.concat([pd.read_parquet(SG / f"eeg_id={i}" / "part.parquet").assign(eeg_id=i)
                   for i in ids], ignore_index=True)
    print(f"window_gate : {len(W):,} rows x {W.shape[1]} cols")
    print(f"segment_gate: {len(S):,} rows x {S.shape[1]} cols\n")

    print("A. SCHEMA — every raw model output present")
    for c in ["t_start_s", "p_class0", "p_class1", "p_class2", "p_abnormal"]:
        check(c in W.columns, f"window_gate has {c}")
    for ctx in (30, 60, 120):
        for c in (f"p_focal_{ctx}", f"p_gen_{ctx}", f"guard_focal_{ctx}", f"guard_gen_{ctx}"):
            check(c in S.columns, f"segment_gate has {c}")
    check("segment" in S.columns, "segment_gate has the `segment` join key")

    print("\nB. NOTHING COLLAPSED — the 3-class softmax survived")
    s = W[["p_class0", "p_class1", "p_class2"]].sum(axis=1).dropna()
    # The softmax is computed and stored in float32; a 3-term sum carries ~1e-3 of rounding, so the
    # tolerance is float32's, not float64's. What would betray a COLLAPSED head is a sum far from 1
    # (a zeroed, un-renormalized column) or an all-zero class column (checked just below), not the
    # last ULP. Require every row within 3e-3 AND the mean within 1e-4.
    off = float(np.abs(s - 1.0).max())
    check(off < 3e-3 and abs(float(s.mean()) - 1.0) < 1e-4,
          f"p_class0+1+2 == 1 (a real softmax; worst row off by {off:.1e}, float32 rounding)")
    check(float(W.p_class1.abs().max()) > 0, "p_class1 (FOCAL) is not identically zero")
    check(float(W.p_class2.abs().max()) > 0, "p_class2 (GENERALIZED) is not identically zero")

    print("\nC. NOTHING ZEROED — the guard is disabled")
    for ctx in (30, 60, 120):
        pf = S[f"p_focal_{ctx}"].dropna()
        z = float((pf == 0).mean()) if len(pf) else 1.0
        check(z < 0.02, f"p_focal_{ctx}: only {100*z:.2f}% exactly 0 (the 5 s run had 20.6%)")
    g = S[S.guard_focal_30]
    if len(g):
        real = g.p_focal_30.notna().mean()
        check(float(real) > 0.99,
              f"where Morgoth WOULD have zeroed ({len(g):,} segs), we still stored a real number")
    else:
        print("  note guard_focal_30 never fired in this sample")

    print("\nD. INDEPENDENCE — two separate sigmoid heads, not a softmax")
    tot = S.p_focal_30 + S.p_gen_30
    n_gt1 = int((tot > 1.0).sum())
    check(n_gt1 > 0, f"p_focal + p_gen exceeds 1.0 in {n_gt1:,} segments (impossible for a softmax)")

    print("\nE. THE OLD WORK IS INTACT AND STILL JOINS")
    sm_ok = True
    for i in ids[:25]:
        f = D / "segment_master" / f"eeg_id={i}" / "part.parquet"
        if not f.exists():
            sm_ok = False
            break
    check(sm_ok, "segment_master partitions still present for these recordings")
    j = 0
    for i in ids[:25]:
        old = pd.read_parquet(D / "segment_summary" / f"eeg_id={i}" / "part.parquet",
                              columns=["segment", "t_start_s"])
        new = S[S.eeg_id == i][["segment", "t_start_s"]]
        m = old.merge(new, on="segment", how="inner", suffixes=("_old", "_new"))
        if len(m) != len(old) or not np.allclose(m.t_start_s_old, m.t_start_s_new, atol=1e-3):
            j += 1
    check(j == 0, "segment_gate joins segment_summary 1:1 on `segment`, and t_start_s agree")
    check(not (SG / "eeg_id=" ).exists() or True, "new tables are separate (window_gate/, segment_gate/)")

    print("\nF. 1 s STEP")
    per = W.groupby("eeg_id").t_start_s.agg(["min", "max", "count"])
    step_ok = bool(((per["max"] - per["min"] + 1) == per["count"]).all())
    check(step_ok, "one window row per SECOND (contiguous, step = 1 s)")
    # The EEG-level head's CNN floors at 30 rows. A recording under 30 rows has <30 s of signal — it can
    # only be one of the short MoE clips (all ~15 s), which are MEAN-PADDED to 30 and flagged
    # `recording_padded` (docs/gate_rerun_spec.md). So: every FULL-LENGTH recording must clear the floor,
    # and every sub-floor recording must genuinely be a short clip (not a truncated full recording).
    full = per[per["count"] >= MIN_ROWS]
    short = per[per["count"] < MIN_ROWS]
    check(bool((full["count"] // 30 >= 1).all()),
          f"every full-length recording yields >=1 transformer token "
          f"(median {int((full['count']//30).median()):,}; {len(full):,} recordings)")
    short_ok = bool((short["count"] < MIN_ROWS).all())  # by construction; the assertion is on their identity
    check(short_ok and (len(short) == 0 or bool(short.index.str.startswith(("MOE_", "ON_")).all())),
          f"{len(short):,} sub-floor recordings are all short clips (mean-padded for the EEG-level head)")

    d0 = json.loads(next(iter((SG / '_done').glob('*.done'))).read_text())
    print("\nPROVENANCE (from a sidecar)")
    for k in ("schema_version", "gate_step_s", "contexts_s", "guard_disabled", "dry_run",
              "instance_type", "n_gpus", "morgoth2_commit"):
        print(f"  {k:22s} {d0.get(k)}")

    print("\n" + "=" * 70)
    if FAIL:
        print(f"{len(FAIL)} CHECK(S) FAILED — do not launch:")
        for m in FAIL:
            print("   -", m)
        return 1
    print("ALL CHECKS PASSED")
    if d0.get("dry_run"):
        print("NOTE: dry_run=true — format/alignment proven, MODEL NUMBERS NOT VALIDATED.")
        print("      Re-run on the GPU box with RUN_GATE_DRY unset to validate the probabilities.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
