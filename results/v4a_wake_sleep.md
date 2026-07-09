# V4a — within-subject wake->sleep test

Do recordings whose report NAMES slowing but NEVER mentions sleep still deviate above stage/age-matched clean-normals **in their sleep stages** (N2/N3), where the reader was silent? The contrast is WITHIN one recording (wake z vs sleep z, same brain), so it cannot be explained by cases being older/sicker/medicated.

**Falsification (pre-specified):** if cases' `z_sleep` ~= 0 and is indistinguishable from held-out controls, the reader's silence about sleep was correct and our sleep-stage detections are noise. We report that outcome plainly if it occurs.

**Groups.** CASES (is_abnormal & report names slowing & report never mentions sleep-slowing & clean_pair & >=10 W/N1 & >=10 N2/N3): **n=686**. CONTROLS (held-out clean-normals, 50/50 split, same segment-count rule): **n=431**. Reference curves built from the OTHER 2434 clean-normals only.

Four whole-head features. z per segment vs the (stage, age) clean-normal reference, Gaussian age kernel bw=5y; z_wake/z_sleep = median z over W/N1 and N2/N3 segments respectively. **Primary sleep-stage feature = log_delta** (pre-specified from scripts/84: absolute/ratio bands are the sleep detectors; the relative composite `low_freq_rel` is a weak, ceiling-bounded detector and is reported but not primary — see the verdict).

## Primary: z_sleep, cases vs held-out controls

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | rank-biserial | AUROC [95% CI] |
|---|---|---|---|---|---|
| low_freq_rel | +0.110 | +0.101 | 5.72e-01 | +0.020 | 0.510 [0.476,0.545] |
| **log_delta **| +0.619 | +0.019 | 2.74e-48 | +0.518 | 0.759 [0.732,0.788] |
| TAR | +0.766 | +0.051 | 1.53e-27 | +0.386 | 0.693 [0.660,0.723] |
| DAR | +0.976 | -0.025 | 1.19e-57 | +0.568 | 0.784 [0.759,0.809] |

## Within-subject contrast: (z_sleep - z_wake)

A patient who is merely globally shifted (older/sicker) would have z_wake and z_sleep raised by the SAME amount, so their Δ(sleep-wake) would equal a control's. The anti-confound signal is therefore Δ_case **larger than** Δ_ctrl: cases gaining EXTRA deviation specifically in sleep.

| feature | case z_wake->z_sleep | case Δ(sleep-wake) [Wilcoxon p, %>0] | ctrl z_wake->z_sleep | ctrl Δ(sleep-wake) [Wilcoxon p, %>0] |
|---|---|---|---|---|
| low_freq_rel | +0.058->+0.110 | -0.262 [p=1.56e-04, 45%] | +0.172->+0.101 | -0.250 [p=2.31e-04, 37%] |
| **log_delta **| +0.238->+0.619 | +0.473 [p=3.01e-41, 67%] | +0.085->+0.019 | -0.019 [p=5.79e-02, 47%] |
| TAR | +0.645->+0.766 | -0.291 [p=1.62e-12, 36%] | +0.219->+0.051 | -0.228 [p=2.00e-08, 39%] |
| DAR | +0.642->+0.976 | +0.152 [p=2.88e-11, 54%] | +0.169->-0.025 | -0.307 [p=1.36e-16, 31%] |

## Sensitivity: CASES additionally require has_gen_slow==1 (n=683)

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | AUROC [95% CI] | median (sleep-wake), case [Wilcoxon p] |
|---|---|---|---|---|---|
| low_freq_rel | +0.116 | +0.101 | 5.35e-01 | 0.511 [0.478,0.547] | -0.266 [p=1.45e-04] |
| **log_delta **| +0.624 | +0.019 | 2.02e-48 | 0.760 [0.732,0.785] | +0.475 [p=2.97e-41] |
| TAR | +0.769 | +0.051 | 8.68e-28 | 0.694 [0.663,0.722] | -0.289 [p=3.07e-12] |
| DAR | +0.979 | -0.025 | 9.54e-58 | 0.785 [0.758,0.810] | +0.156 [p=2.87e-11] |

## Verdict

**Pre-specified falsification:** cases' sleep z ~= 0 and indistinguishable from held-out controls on every feature -> the reader's silence about sleep was correct and our sleep detections are noise.

**The falsification is NOT met.** Group-level: **3 of 4** features (log_delta, TAR, DAR) place cases' z_sleep clearly above controls'. Within-subject anti-confound: **2 of 4** (log_delta, DAR) ALSO show a larger wake->sleep gap in cases than controls, so their sleep excess is not a global shift. TAR separates at the group level but its within-subject gap matches controls' (Δ -0.291 case vs -0.228 ctrl) — a global wake+sleep carry-over, not a sleep-specific gain.

**HYPOTHESIS SURVIVES.** On the primary sleep feature **log_delta**: cases' median z_sleep = +0.619 vs controls' +0.019 (MWU p=2.74e-48, AUROC 0.759 [0.732,0.788]). The within-subject test is the decisive one: cases GAIN deviation going wake->sleep (Δ = +0.473, Wilcoxon p=3.01e-41, 67% positive) while held-out controls do NOT (Δ = -0.019). A pure global shift (cases just older/sicker) would give Δ ~= 0 in both groups; instead the sleep excess appears in the SAME brains the reader called slow in wake. `DAR` gives the highest sleep separation (AUROC 0.784); `TAR` (0.693) agrees.

**The one null, reported loudly:** `low_freq_rel` ((delta+theta)/total) does NOT separate (z_sleep +0.110 vs +0.101, AUROC 0.510, MWU p=5.72e-01). This is NOT a sleep-specific failure: `low_freq_rel` barely separates in WAKE either (case z_wake +0.058), because it is a bounded relative measure that saturates near its ceiling in N2/N3 (clean-normal N3 median 0.63 against a hard cap of 1.0), leaving no headroom for excess sleep delta. Absolute log-delta power and delta/alpha ratio, which are unbounded above, carry the signal. This matches the standing finding that relative low-frequency power is a weak detector and TAR/DAR should be used.

**Interpretation.** Recordings the reader called slow in WAKE, whose reports never mention sleep, still sit above stage/age-matched normals in N2/N3 on every dynamic-range slowing measure, and the excess is *larger* in sleep than in wake within the same recording. This is World 1 (we add value): the reader's silence about sleep understated real deviation, not because sleep slowing was absent but because the judgment is hard and rarely attempted. It is not World 2 (false positives): the within-subject design and the held-out clean-normal reference (controls ~0 in sleep) rule out an older/sicker-cohort artifact.

**Residual caveats.** (1) The operationalization is `report never says a sleep word in a slowing clause`; we cannot exclude that a reader intended a wake-slowing sentence to cover sleep too. (2) `DAR` controls drift to about -0.3 in sleep (alpha collapses in N2/N3), a mild stage-calibration quirk; `log_delta` controls stay ~0 across stages, which is why it is the primary. (3) Cases are abnormal for some reason and slowing may travel with it; the within-subject contrast addresses the cohort confound but not the possibility that the *unnamed* deviation is a different abnormality than the named wake slowing.

