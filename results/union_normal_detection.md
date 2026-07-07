# Union-as-normal: does the broad/conservative normal hurt abnormal detection?

Premise (verified): both cohorts are clinician-read normal — routine clean_normal is 100% report-normal;
overnight is report-normal by impression (0% flag abnormal; ~91% concordant with strict labeling). The
findings flags are reliable (foc_slowing 99% true-positive, not negation-contaminated). So the
clinician-defined "normal" genuinely spans both cohorts, wider than either alone.

Test (scripts/79): build the normal age-adjusted reference three ways and compare abnormal-vs-normal AUROC
(whole-head rel_delta z; positives = cohort pathologic generalized slowing; negatives = HELD-OUT routine
normals, kept out of every reference for fairness).

| stage | n+ | AUROC union | AUROC routine-only | AUROC overnight-only |
|-------|----|-------------|--------------------|----------------------|
| W   | 52 | 0.555 | 0.540 | 0.556 |
| N1  | 35 | 0.458 | 0.438 | 0.464 |
| N2  | 34 | 0.454 | 0.392 | 0.467 |
| N3  | 11 | 0.732 | 0.781 | 0.722 |
| REM | 26 | 0.506 | 0.455 | 0.513 |

**Result:** union AUROC is statistically indistinguishable from routine-only (overlapping 95% CIs) and
slightly higher in most stages (a larger reference gives a more stable norm). Even in wake — where the
union widens the band most (drowsy overnight wake) — detection is unchanged. **The conservative broad
normal costs no measurable detection power -> using the union of both report-normal cohorts as the
normative standard is justified.**

Caveats: valid for delta-based features (pipeline-consistent). TAR/DAR should not be pooled across sources
until the cohort is recomputed through extract.py (alpha-band mismatch; see results/pipeline_control.md).
Absolute AUROCs are low (whole-head rel_delta is the weak detector, few positives) — this is a relative
union-vs-single comparison, which is what is valid.
