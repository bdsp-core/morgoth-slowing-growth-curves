# V4a — within-subject wake->sleep test

Do recordings whose report NAMES slowing but NEVER mentions sleep still deviate above stage/age-matched clean-normals **in their sleep stages** (N2/N3), where the reader was silent? The contrast is WITHIN one recording (wake z vs sleep z, same brain), so it cannot be explained by cases being older/sicker/medicated.

**Falsification (pre-specified):** if cases' `z_sleep` ~= 0 and is indistinguishable from held-out controls, the reader's silence about sleep was correct and our sleep-stage detections are noise. We report that outcome plainly if it occurs.

**Groups.** CASES (is_abnormal & report names slowing & report never mentions sleep-slowing & clean_pair & >=10 W/N1 & >=10 N2/N3): **n=686**. CONTROLS (held-out clean-normals, 50/50 split, same segment-count rule): **n=431**. Reference curves built from the OTHER 2434 clean-normals only.

Primary feature **low_freq_rel** ((delta+theta)/total). Region whole_head. z per segment vs the (stage, age) clean-normal reference, Gaussian age kernel bw=5y; z_wake/z_sleep = median z over W/N1 and N2/N3 segments respectively.

## Primary: z_sleep, cases vs held-out controls

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | rank-biserial | AUROC [95% CI] |
|---|---|---|---|---|---|
| **low_freq_rel **| +0.110 | +0.101 | 5.72e-01 | +0.020 | 0.510 [0.476,0.545] |
| log_delta | +0.619 | +0.019 | 2.74e-48 | +0.518 | 0.759 [0.732,0.788] |
| TAR | +0.766 | +0.051 | 1.53e-27 | +0.386 | 0.693 [0.660,0.723] |
| DAR | +0.976 | -0.025 | 1.19e-57 | +0.568 | 0.784 [0.759,0.809] |

## Within-subject contrast: (z_sleep - z_wake)

If cases were merely globally shifted, controls would show the same sleep-minus-wake gap. The crucial comparison is that the gap is present in cases and ~0 in controls.

| feature | median z_wake / z_sleep (case) | median (sleep-wake), case [Wilcoxon p, %>0] | median (sleep-wake), ctrl [Wilcoxon p, %>0] |
|---|---|---|---|
| **low_freq_rel **| +0.058 / +0.110 | -0.262 [p=1.56e-04, 45%] (n=686) | -0.250 [p=2.31e-04, 37%] (n=431) |
| log_delta | +0.238 / +0.619 | +0.473 [p=3.01e-41, 67%] (n=686) | -0.019 [p=5.79e-02, 47%] (n=431) |
| TAR | +0.645 / +0.766 | -0.291 [p=1.62e-12, 36%] (n=686) | -0.228 [p=2.00e-08, 39%] (n=431) |
| DAR | +0.642 / +0.976 | +0.152 [p=2.88e-11, 54%] (n=686) | -0.307 [p=1.36e-16, 31%] (n=431) |

## Sensitivity: CASES additionally require has_gen_slow==1 (n=683)

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | AUROC [95% CI] | median (sleep-wake), case [Wilcoxon p] |
|---|---|---|---|---|---|
| **low_freq_rel **| +0.116 | +0.101 | 5.35e-01 | 0.511 [0.478,0.547] | -0.266 [p=1.45e-04] |
| log_delta | +0.624 | +0.019 | 2.02e-48 | 0.760 [0.732,0.785] | +0.475 [p=2.97e-41] |
| TAR | +0.769 | +0.051 | 8.68e-28 | 0.694 [0.663,0.722] | -0.289 [p=3.07e-12] |
| DAR | +0.979 | -0.025 | 9.54e-58 | 0.785 [0.758,0.810] | +0.156 [p=2.87e-11] |

## Verdict

Pre-specified survival criterion (primary feature low_freq_rel): cases' median z_sleep > 0, > controls', MWU p<0.05, AUROC>0.5.

**HYPOTHESIS FAILS / NULL.** Cases' median z_sleep = +0.110 vs controls' +0.101 (MWU p=5.72e-01, AUROC 0.510). Within-subject sleep-minus-wake gap in cases = -0.262 (Wilcoxon p=1.56e-04), vs -0.250 in controls.

Interpretation (HONEST NULL, not spun): cases do not deviate above controls in sleep. Under the pre-specified criterion the reader's silence about sleep was correct and our sleep-stage detections in this stratum are not distinguishable from noise. We are a good WAKE detector with an uncalibrated sleep description, and we say exactly that.

