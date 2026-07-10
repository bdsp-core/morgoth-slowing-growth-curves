# N1 anomaly — why is alpha attenuation reversed in abnormal N1?

## Raw band power by stage and group (mean log-power; higher alpha = more alpha)

| stage | group | n_seg | log_alpha | log_delta | log_theta | log_beta |
|---|---|---|---|---|---|---|
| W | normal | 114,024 | +1.456 | +2.681 | +1.019 | +1.487 |
| W | focal | 73,636 | -5.000 | -3.519 | -4.859 | -4.769 |
| W | generalized | 23,536 | -7.912 | -6.270 | -7.587 | -7.457 |
| N1 | normal | 30,127 | +1.123 | +2.187 | +1.139 | +1.353 |
| N1 | focal | 24,652 | +1.374 | +3.153 | +1.892 | +1.663 |
| N1 | generalized | 12,691 | +1.330 | +3.616 | +2.270 | +1.768 |
| N2 | normal | 30,117 | +1.062 | +2.981 | +1.564 | +1.031 |
| N2 | focal | 31,889 | +1.043 | +3.368 | +1.679 | +1.087 |
| N2 | generalized | 16,175 | +0.868 | +3.349 | +1.580 | +0.955 |

Read the N1 alpha column against W: in NORMALS alpha should fall W→N1 (alpha drops out in true N1). If abnormal N1 alpha does NOT fall, its 'N1' is drowsy wake.

- normal: log_alpha W +1.456 → N1 +1.123  (drop +0.333)
- focal: log_alpha W -5.000 → N1 +1.374  (drop -6.374)
- generalized: log_alpha W -7.912 → N1 +1.330  (drop -9.243)

## H1 — is abnormal 'N1' really drowsy wake? (stager confidence)

abnormal N1 segments with probabilities: 46,113
- median p(Wake) on these 'N1' segments: **0.172** (if 'N1' were solid, this is low; high = wake bleed-through)
- z_alpha vs normal-N1, all abnormal 'N1': **+0.445** (positive = MORE alpha than normal N1 — the anomaly)
- z_alpha on LOW-confidence 'N1' (p_wake≥0.30, n=8786): **+0.691**
- z_alpha on HIGH-confidence 'N1' (p_wake<0.10, n=14320): **+0.182**

If the anomaly vanishes on high-confidence N1, it is a STAGING artifact (H1) and the fix is a confidence gate on N1 segments. If it persists, H1 is out.

## H2 — is the normal-N1 reference well powered?

normal N1 recordings: 3,176; segments 30,127

| ageband   |   n_recordings |
|:----------|---------------:|
| (0, 18]   |            684 |
| (18, 40]  |            850 |
| (40, 60]  |            742 |
| (60, 75]  |            584 |
| (75, 100] |            277 |

---

## Resolution (2026-07-10)

The "N1 anomaly" was **two separate problems**, neither of which was N1-physiology:

**1. Flat segments (the big one).** 22.8% of abnormal *wake* segments (31.7% of generalized) are flat — every
core band at the 1e-12 eps floor (ln ≈ −27.6), versus ~1% of normal wake, and it is wake-specific (N1/N2 ≈
0.1% in both groups). These are suppressed / disconnected / dead epochs that survived artifact rejection
(likely cEEG break/attenuation periods; abnormal recordings are disproportionately long-term cEEG). They are
flat across *all* bands (99–100%), so they are absence of signal, not slowing. **Fix: drop segments with all
core log-bands < −20.** This alone brought abnormal wake `log_alpha` from −4.7 (focal) / −7.7 (generalized)
back to +1.7 / +1.5, matching normals (+1.8).

**2. Alpha in sleep is confounded by sleep architecture.** After flat-exclusion the N1/N2 reversal *persisted*
(abnormal N1 alpha still above normal N1). Reason: alpha is the posterior dominant rhythm, prominent in wake,
normally attenuated in N1 and gone by N2. Encephalopathic patients have disrupted, lighter sleep that retains
wake-like alpha the stager still calls N1/N2 — so "alpha attenuation vs normal-for-stage" is negative for them
in sleep, which would falsely read as *less* slowing. **Fix: the alpha-attenuation axis is computed in WAKE
only** (and the amount direction is fit on wake, where all three axes apply). In N1–REM, slowing is delta and
theta excess.

**After both fixes:** calibration holds (clean-normals −0.06 SD, prevalence 0.045); every descriptor orders
normal < focal < generalized in every stage; N1 alpha attenuation is no longer emitted. The amount-direction
AUROC fell 0.811 → 0.770, because part of the old discrimination rode on flat/suppressed segments — removing
that is correct: suppression is not slowing (and is a candidate *separate* descriptor).

**Also note for artifact rejection:** `features/artifact.py::usable_mask` does not reject fully-flat segments.
Worth a guard upstream, but the field-level exclusion handles it for description.
