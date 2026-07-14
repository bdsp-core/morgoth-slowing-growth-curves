#!/usr/bin/env python3
"""P6 — "readers under-report SLEEP slowing". Its evidence file (v4a_wake_sleep) was DELETED in the
results purge and never regenerated, so P6 has been sitting UNEVALUATED. This rebuilds it on v6.

THE CIRCULARITY TRAP, and how this avoids it. The naive test — "among report-normal recordings, how often
do we see slowing in sleep?" — is vacuous: the norms are fit ON the clean-normals, per stage, so by
construction ~5% of them exceed the 95th centile in EVERY stage. That number tells you nothing.

The non-circular test asks instead: **when slowing is visible only in sleep, do readers still report it?**
  Group WAKE  : our stage-matched z exceeds tau in W          (slowing is visible while awake)
  Group SLEEP-ONLY : z exceeds tau in N2/N3 but NOT in W      (slowing is visible only once asleep)
Then compare the REPORT's slowing rate between the groups. The report label is the OUTCOME here, not the
reference — so the normative fit cannot manufacture the effect.

  P6 CONFIRMED  if report-rate(SLEEP-ONLY) < report-rate(WAKE)  -- readers miss sleep-only slowing
  P6 FALSIFIED  if our sleep-slowing rate <= the report rate    (per the pre-registered wording)

Reads ONLY v6-derived tables (channel_stage_features + labels_unified, rebuilt from segment_master).
Run: PYTHONPATH=src python scripts/p6_sleep_underreporting.py
"""
from pathlib import Path
import numpy as np, pandas as pd

FEAT = "TAR"              # SAP's lead slowing feature (adapter keeps the legacy name; it IS log(theta/alpha))
TAU = 1.645               # 95th centile of the stage-matched normal distribution
REGION = "whole_head"


def grid_z(age_ref, v_ref, age_q, v_q, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    ok = np.isfinite(age_ref) & np.isfinite(v_ref); ar, vr = age_ref[ok], v_ref[ok]
    if len(ar) < 20:
        return np.full(len(v_q), np.nan)
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((ar - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * vr).sum() / sw; mu[j] = m
        sd[j] = np.sqrt(max((w * (vr - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (v_q - np.interp(age_q, grid[good], mu[good], np.nan, np.nan)) / \
           np.interp(age_q, grid[good], sd[good], np.nan, np.nan)


def main():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    # CORRECTED SAP labels (label_rederive_sap.py) — NOT labels_unified, which carries the
    # original buggy report flags that swept physiologic drowsy slowing into the positive class.
    lu = pd.read_parquet("data/derived/recording_labels_sap.parquet").rename(columns={"eeg_id": "bdsp_id"})
    key = "bdsp_id" if "bdsp_id" in d.columns else "eeg_id"
    d = d[(d.region == REGION) & d[FEAT].notna()]
    # drop the manifest-derived label/age columns carried on the feature table — they are the ORIGINAL
    # (buggy) flags. Everything label-ish must come from the corrected SAP table.
    d = d.drop(columns=[c for c in ("clean_normal", "clean_pair", "age", "is_abnormal", "sex", "patient_id")
                        if c in d.columns])
    lu = lu.drop_duplicates("bdsp_id").set_index("bdsp_id")

    # stage-matched, age-conditioned z, referenced to CLEAN-NORMALS IN THAT STAGE
    zs = {}
    for stage in ["W", "N2", "N3"]:
        s = d[d.stage == stage].merge(
            lu[["age", "clean_normal", "slowing_positive", "clean_pair"]], left_on=key, right_index=True, how="inner")
        if s.empty:
            continue
        ref = s[s.clean_normal == True]                                   # noqa: E712
        s = s.assign(z=grid_z(ref.age.values.astype(float), ref[FEAT].values.astype(float),
                              s.age.values.astype(float), s[FEAT].values.astype(float)))
        zs[stage] = s.set_index(key)[["z", "slowing_positive", "clean_pair", "age"]]
        print(f"  stage {stage:2}: {len(s):,} recordings ({int((s.clean_normal == True).sum()):,} normal ref)")

    W = zs.get("W"); SL = None
    sleep = [zs[k] for k in ("N2", "N3") if k in zs]
    if sleep:
        SL = pd.concat(sleep).groupby(level=0).z.max().rename("z_sleep")   # slowing in EITHER sleep stage
    if W is None or SL is None:
        print("insufficient stage coverage"); return

    df = W[["z", "slowing_positive", "clean_pair"]].rename(columns={"z": "z_wake"}).join(SL, how="inner")
    df = df[df.clean_pair == True]                                        # SAP §3.3 report-broadcast guard
    df["reported_slowing"] = df.slowing_positive.astype(bool)

    wake_pos = df[df.z_wake > TAU]
    sleep_only = df[(df.z_sleep > TAU) & (df.z_wake <= TAU)]
    neither = df[(df.z_sleep <= TAU) & (df.z_wake <= TAU)]

    r_wake = wake_pos.reported_slowing.mean()
    r_sleep_only = sleep_only.reported_slowing.mean()
    r_neither = neither.reported_slowing.mean()

    print(f"\nclean_pair recordings with both W and sleep coverage: {len(df):,}")
    print(f"\n  slowing visible in WAKE            : n={len(wake_pos):5,}  report names slowing in "
          f"{r_wake:.1%}")
    print(f"  slowing visible ONLY IN SLEEP      : n={len(sleep_only):5,}  report names slowing in "
          f"{r_sleep_only:.1%}   <-- the test")
    print(f"  slowing visible in NEITHER (base)  : n={len(neither):5,}  report names slowing in "
          f"{r_neither:.1%}")

    # our detection rate in sleep vs the report's overall rate (the pre-registered wording)
    our_sleep_rate = (df.z_sleep > TAU).mean()
    report_rate = df.reported_slowing.mean()
    print(f"\n  our SLEEP-slowing detection rate   : {our_sleep_rate:.1%}")
    print(f"  the REPORT's slowing rate          : {report_rate:.1%}")

    confirmed = (r_sleep_only < r_wake) and (our_sleep_rate > report_rate)
    verdict = "CONFIRMED" if confirmed else "FALSIFIED"
    print(f"\nP6 -> {verdict}")
    print(f"   readers name slowing in {r_wake:.1%} of recordings where it is visible awake, but only "
          f"{r_sleep_only:.1%} when it is visible ONLY in sleep")

    Path("results").mkdir(exist_ok=True)
    Path("results/p6_sleep_underreporting.md").write_text(
        "# P6 — do readers under-report SLEEP slowing? (SAP §10; rebuilt on v6)\n\n"
        "The evidence file for this prediction (`v4a_wake_sleep`) was deleted in the results purge and had "
        "not been regenerated, leaving P6 unevaluated. Rebuilt here from v6 fleet output only.\n\n"
        "**Avoiding the circularity trap.** Asking 'how much sleep slowing do we see in report-normals?' is "
        "vacuous — the norms are fit on the clean-normals *per stage*, so ~5% of them exceed the 95th centile "
        "in every stage by construction. Instead we ask: **when slowing is visible only once the patient is "
        "asleep, do readers still name it?** The report label is the OUTCOME, not the reference, so the "
        "normative fit cannot manufacture the effect.\n\n"
        f"Stage-matched age-conditioned z on `{FEAT}` (whole-head), τ = {TAU} (95th centile), "
        f"`clean_pair` only (n = {len(df):,}).\n\n"
        "| group | n | report names slowing |\n|---|---|---|\n"
        f"| slowing visible in **wake** | {len(wake_pos):,} | **{r_wake:.1%}** |\n"
        f"| slowing visible **only in sleep** | {len(sleep_only):,} | **{r_sleep_only:.1%}** |\n"
        f"| visible in neither (base rate) | {len(neither):,} | {r_neither:.1%} |\n\n"
        f"Our sleep-slowing detection rate **{our_sleep_rate:.1%}** vs the report's slowing rate "
        f"**{report_rate:.1%}**.\n\n"
        f"**P6 → {verdict}.** Readers name slowing in {r_wake:.1%} of recordings where it is visible awake, "
        f"but only {r_sleep_only:.1%} when it is visible only in sleep.\n")
    print("\nwrote results/p6_sleep_underreporting.md")


if __name__ == "__main__":
    main()
