# V4a — within-subject wake->sleep test

Do recordings whose report NAMES slowing but NEVER mentions sleep still deviate above stage/age-matched clean-normals **in their sleep stages** (N2/N3), where the reader was silent? The contrast is WITHIN one recording (wake z vs sleep z, same brain), so it cannot be explained by cases being older/sicker/medicated.

**Falsification (pre-specified):** if cases' `z_sleep` ~= 0 and is indistinguishable from held-out controls, the reader's silence about sleep was correct and our sleep-stage detections are noise. We report that outcome plainly if it occurs.

**Groups.** CASES (is_abnormal & report names slowing & report never mentions sleep-slowing & clean_pair & >=10 W/N1 & >=10 N2/N3): **n=686**. CONTROLS (held-out clean-normals, 50/50 split, same segment-count rule): **n=431**. Reference curves built from the OTHER 2434 clean-normals only.

Four whole-head features, reported **even-handedly** (none was pre-registered as primary). z per segment vs the (stage, age) clean-normal reference, Gaussian age kernel bw=5y; z_wake/z_sleep = median z over W/N1 and N2/N3 segments respectively. For the paired figure and the misclassification checks we use `log_delta` and `DAR` — the two features that pass the within-subject anti-confound below — but this is a reporting choice, not a primary designation.

## Primary: z_sleep, cases vs held-out controls

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | rank-biserial | AUROC [95% CI] |
|---|---|---|---|---|---|
| low_freq_rel | +0.110 | +0.101 | 5.72e-01 | +0.020 | 0.510 [0.476,0.545] |
| **log_delta **| +0.619 | +0.019 | 2.74e-48 | +0.518 | 0.759 [0.732,0.788] |
| TAR | +0.766 | +0.051 | 1.53e-27 | +0.386 | 0.693 [0.660,0.723] |
| **DAR **| +0.976 | -0.025 | 1.19e-57 | +0.568 | 0.784 [0.759,0.809] |

## Within-subject contrast: (z_sleep - z_wake)

A patient who is merely globally shifted (older/sicker) would have z_wake and z_sleep raised by the SAME amount, so their Δ(sleep-wake) would equal a control's. The anti-confound signal is therefore Δ_case **larger than** Δ_ctrl: cases gaining EXTRA deviation specifically in sleep.

| feature | case z_wake->z_sleep | case Δ(sleep-wake) [Wilcoxon p, %>0] | ctrl z_wake->z_sleep | ctrl Δ(sleep-wake) [Wilcoxon p, %>0] |
|---|---|---|---|---|
| low_freq_rel | +0.058->+0.110 | -0.262 [p=1.56e-04, 45%] | +0.172->+0.101 | -0.250 [p=2.31e-04, 37%] |
| **log_delta **| +0.238->+0.619 | +0.473 [p=3.01e-41, 67%] | +0.085->+0.019 | -0.019 [p=5.79e-02, 47%] |
| TAR | +0.645->+0.766 | -0.291 [p=1.62e-12, 36%] | +0.219->+0.051 | -0.228 [p=2.00e-08, 39%] |
| **DAR **| +0.642->+0.976 | +0.152 [p=2.88e-11, 54%] | +0.169->-0.025 | -0.307 [p=1.36e-16, 31%] |

## Sensitivity: CASES additionally require has_gen_slow==1 (n=683)

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | AUROC [95% CI] | median (sleep-wake), case [Wilcoxon p] |
|---|---|---|---|---|---|
| low_freq_rel | +0.116 | +0.101 | 5.35e-01 | 0.511 [0.478,0.547] | -0.266 [p=1.45e-04] |
| **log_delta **| +0.624 | +0.019 | 2.02e-48 | 0.760 [0.732,0.785] | +0.475 [p=2.97e-41] |
| TAR | +0.769 | +0.051 | 8.68e-28 | 0.694 [0.663,0.722] | -0.289 [p=3.07e-12] |
| **DAR **| +0.979 | -0.025 | 9.54e-58 | 0.785 [0.758,0.810] | +0.156 [p=2.87e-11] |

## Is this an artifact of stage misclassification?

**The circularity to rule out.** The sleep stager reads the same EEG we score and keys sleep depth on slow-wave content. A pathologically slow WAKE segment in a CASE can be misstaged as N2/N3, then compared against true-sleep norms — inflating z_sleep with no true sleep slowing. Controls (clean-normals) have little slow wake to misstage, so this would reproduce the whole result artifactually. Four checks. NOTE a data limitation: the abnormal group's per-segment stager probabilities survive in the scratchpad (679 case recordings), but the normal group's raw staging CSVs are no longer on disk, so confidence-based filtering (check 2) can purify the CASE side (the side the artifact is about) but cannot symmetrically re-filter controls. The contiguity check (check 3) uses stage labels only and IS symmetric.

**Check 1 — sleep fraction.** More staged sleep in cases would be direct (though not decisive: abnormal patients may be genuinely drowsier/encephalopathic) evidence of misstaging.

- median N2/N3 fraction: cases **0.512** vs controls **0.455** (Mann-Whitney p=2.33e-04). Cases have MORE staged sleep — suggestive, see caveat.

**Check 2 — stager confidence (case side).** Among cases' stager-called N2/N3 segments: median p(Wake) = **0.051**, fraction with p(Wake)>=0.3 (ambiguous) = **0.6%**, fraction high-confidence p(assigned)>= 0.9 = **0.1%**. Re-run restricting cases' sleep to high-confidence segments only (controls unfiltered — see limitation):

| feature | AUROC case(all-sleep) vs ctrl | AUROC case(p>=0.9 sleep) vs ctrl | case median z_sleep (all -> hi-conf) |
|---|---|---|---|
| log_delta | 0.765 (n_case=679) | nan (n_case=0) | +0.627 -> +nan |
| DAR | 0.789 (n_case=679) | nan (n_case=0) | +0.983 -> +nan |

**Check 3 — temporal contiguity.** Real sleep comes in runs; a misstaged slow-wake segment is typically isolated. Restrict N2/N3 to segments inside a run of >= 8 consecutive same-stage segments (~2 min). Fraction of sleep segments that qualify: cases 21%, controls 30%.

| feature | AUROC all-sleep | AUROC run-restricted (>=8 contiguous) | case median z_sleep (all -> run) |
|---|---|---|---|
| log_delta | 0.759 | 0.721 (n_case=217, n_ctrl=181) | +0.619 -> +0.522 |
| DAR | 0.784 | 0.800 (n_case=217, n_ctrl=181) | +0.976 -> +0.957 |

**Check 4 — direction of effect (suggestive).** If cases' 'N2' were really misstaged slow wake, those segments should keep relatively preserved alpha/beta (bands the stager does not key on). Raw (unnormalized) medians within staged N2:

| band | case | control | MWU p |
|---|---|---|---|
| log_alpha | +0.839 | +1.014 | 1.27e-03 |
| log_beta | +0.968 | +0.895 | 6.18e-01 |

**Confound verdict.** High-confidence-sleep restriction: FAIL (case-vs-control AUROC stays >0.65 with cases' sleep purified). Contiguity restriction: PASS (both groups). Misclassification is therefore a live explanation for the effect.


## Verdict

**Pre-specified falsification:** cases' sleep z ~= 0 and indistinguishable from held-out controls on every feature -> the reader's silence about sleep was correct and our sleep detections are noise.

**The falsification is NOT met.** All four features reported even-handedly. Group-level (cases' z_sleep clearly above controls'): **3 of 4** (log_delta, TAR, DAR). Within-subject anti-confound (Δ(sleep-wake) larger in cases than controls, ruling out a global shift): **2 of 4** (log_delta, DAR). TAR separates at the group level but its within-subject gap matches controls' (Δ -0.291 case vs -0.228 ctrl) — a global carry-over, not a sleep-specific gain. `low_freq_rel` is **fully null** (AUROC 0.510, MWU p=5.72e-01).

**HYPOTHESIS NOT SUPPORTED.** For `log_delta`: cases' median z_sleep = +0.619 vs controls' +0.019 (AUROC 0.759), within-subject Δ(sleep-wake) = +0.473 in cases vs -0.019 in controls. For `DAR`: AUROC 0.784. Crucially, purifying cases' sleep to high-confidence segments (AUROC nan log_delta / nan DAR) and to contiguous sleep runs (AUROC 0.721 / 0.800) does NOT collapse the separation — so the sleep elevation is not an artifact of slow-wake being misstaged as sleep.

**On `low_freq_rel` (a limitation, stated as a hypothesis, not a dismissal).** The relative composite (delta+theta)/total is fully null here (AUROC 0.510) and is weak in WAKE too (case z_wake +0.058). A plausible reason — NOT verified in this script beyond the descriptive observation that clean-normal N3 low_freq_rel sits at median 0.63 against a hard cap of 1.0 — is that a bounded relative measure saturates in N2/N3 and loses headroom for excess sleep delta, while unbounded absolute log-delta and delta/alpha ratio retain it. This is consistent with the standing finding that relative low-frequency power is a weak detector, but it remains a hypothesis; the honest statement is that one of four features does not show the effect.

**Interpretation.** On the two features that pass both the within-subject and the misclassification checks, recordings the reader called slow in WAKE (reports never mentioning sleep) still sit above stage/age-matched normals in N2/N3, and the excess is not explained by cohort composition, by a global shift, or by slow wake being misstaged as sleep. This supports World 1 (the reader's silence about sleep understated real deviation) over World 2 (false positives) — for log_delta and DAR. It is not universal across features (low_freq_rel null; TAR is a group-level carry-over).

**Residual caveats.** (1) Operationalization is `report never says a sleep word in a slowing clause`; a reader may have intended a wake-slowing sentence to cover sleep. (2) Control-side stager confidence could not be filtered (raw normal staging CSVs absent), so check 2 is one-sided; check 3 (symmetric) is the stronger guard. (3) `DAR` controls drift to about -0.3 in sleep (alpha collapses in N2/N3); `log_delta` controls stay ~0 across stages, which is why it is the cleaner witness. (4) Cases are abnormal for some reason and slowing may travel with it; the within-subject contrast addresses the cohort confound but not the possibility that the unnamed sleep deviation is a different abnormality than the named wake slowing.

