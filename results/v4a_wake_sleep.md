# V4a — within-subject wake->sleep test

Do recordings whose report NAMES slowing but NEVER mentions sleep still deviate above stage/age-matched clean-normals **in their sleep stages** (N2/N3), where the reader was silent? The contrast is WITHIN one recording (wake z vs sleep z, same brain), so it cannot be explained by cases being older/sicker/medicated.

**Falsification (pre-specified):** if cases' `z_sleep` ~= 0 and is indistinguishable from held-out controls, the reader's silence about sleep was correct and our sleep-stage detections are noise. We report that outcome plainly if it occurs.

**Groups.** CASES (is_abnormal & report names slowing & report never mentions sleep-slowing & clean_pair & >=10 W/N1 & >=10 N2/N3): **n=338**. CONTROLS (held-out clean-normals, 50/50 split, same segment-count rule): **n=432**. Reference curves built from the OTHER 4495 clean-normals only.

Four whole-head features, reported **even-handedly** (none was pre-registered as primary). z per segment vs the (stage, age) clean-normal reference, Gaussian age kernel bw=5y; z_wake/z_sleep = median z over W/N1 and N2/N3 segments respectively. For the paired figure and the misclassification checks we use `log_delta` and `DAR` — the two features that pass the within-subject anti-confound below — but this is a reporting choice, not a primary designation.

## Primary: z_sleep, cases vs held-out controls

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | rank-biserial | AUROC [95% CI] |
|---|---|---|---|---|---|
| low_freq_rel | +0.135 | +0.054 | 2.98e-01 | +0.044 | 0.522 [0.478,0.566] |
| **log_delta **| +0.815 | -0.052 | 2.92e-40 | +0.557 | 0.779 [0.743,0.811] |
| TAR | +0.707 | +0.028 | 1.68e-19 | +0.379 | 0.689 [0.653,0.725] |
| **DAR **| +0.892 | -0.077 | 7.16e-40 | +0.554 | 0.777 [0.743,0.807] |

## Within-subject contrast: (z_sleep - z_wake)

A patient merely globally shifted (older/sicker) would have z_wake and z_sleep raised by the SAME amount, so Δ(sleep-wake) would equal a control's. Δ_case **larger than** Δ_ctrl rules out that particular confound. **BUT Δ>0 is ALSO the stage-misclassification artifact's signature:** if the stager pulls a case's *slowest* wake segments into the sleep bin, the sleep bin holds the slowest material and the wake bin holds the remainder — mechanically producing z_sleep>z_wake in cases and not in controls. So the within-subject Δ does **not** by itself discriminate World 1 (real sleep slowing) from World 2 (misstaged slow wake). It weakens, not settles, the case. The misclassification section and the spindle test below are what actually adjudicate it.

| feature | case z_wake->z_sleep | case Δ(sleep-wake) [Wilcoxon p, %>0] | ctrl z_wake->z_sleep | ctrl Δ(sleep-wake) [Wilcoxon p, %>0] |
|---|---|---|---|---|
| low_freq_rel | +0.885->+0.135 | -0.807 [p=5.81e-42, 12%] | +0.106->+0.054 | -0.203 [p=9.41e-05, 40%] |
| **log_delta **| +0.882->+0.815 | -0.081 [p=3.59e-02, 43%] | -0.046->-0.052 | +0.021 [p=4.06e-01, 51%] |
| TAR | +1.197->+0.707 | -0.524 [p=2.62e-37, 17%] | +0.198->+0.028 | -0.205 [p=5.27e-07, 38%] |
| **DAR **| +1.162->+0.892 | -0.377 [p=5.46e-12, 30%] | +0.126->-0.077 | -0.241 [p=1.02e-12, 32%] |

## Sensitivity: CASES additionally require has_gen_slow==1 (n=287)

| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | AUROC [95% CI] | median (sleep-wake), case [Wilcoxon p] |
|---|---|---|---|---|---|
| low_freq_rel | +0.175 | +0.054 | 1.17e-01 | 0.534 [0.493,0.578] | -0.799 [p=4.39e-35] |
| **log_delta **| +0.835 | -0.052 | 4.62e-39 | 0.788 [0.751,0.823] | -0.078 [p=7.31e-02] |
| TAR | +0.752 | +0.028 | 1.90e-19 | 0.698 [0.660,0.740] | -0.551 [p=6.19e-33] |
| **DAR **| +0.915 | -0.077 | 2.47e-38 | 0.785 [0.749,0.818] | -0.391 [p=1.27e-10] |

## Is this an artifact of stage misclassification?

**The circularity to rule out.** The sleep stager reads the same EEG we score and keys sleep depth on slow-wave content. A pathologically slow WAKE segment in a CASE can be misstaged as N2/N3, then compared against true-sleep norms — inflating z_sleep with no true sleep slowing. Controls (clean-normals) have little slow wake to misstage, so this would reproduce the whole result artifactually. Four checks. NOTE a data limitation: the abnormal group's per-segment stager probabilities survive in the scratchpad (332 case recordings), but the normal group's raw staging CSVs are no longer on disk, so confidence-based filtering (check 2) can purify the CASE side (the side the artifact is about) but cannot symmetrically re-filter controls. The contiguity check (check 3) uses stage labels only and IS symmetric.

**Check 1 — sleep fraction.** More staged sleep in cases would be direct (though not decisive: abnormal patients may be genuinely drowsier/encephalopathic) evidence of misstaging.

- median N2/N3 fraction: cases **0.524** vs controls **0.451** (Mann-Whitney p=9.93e-07). Cases have MORE staged sleep — suggestive, see caveat.

**Check 2 — stager confidence (case side).** The relevant confidence for 'slow wake misstaged as sleep' is p(sleep)=p(N2)+p(N3) — confidently NOT wake. Among cases' stager-called N2/N3 segments: median p(Wake) = **0.064**, fraction with p(Wake)>=0.3 (misstaging candidates) = **0.8%**, fraction confidently sleep p(N2+N3)>= 0.9 = **9.9%**. Re-run restricting cases' sleep to confident-sleep segments:

| feature | AUROC case(all-sleep) vs ctrl | AUROC case(p_sleep>=0.9) vs ctrl | case median z_sleep (all -> conf) |
|---|---|---|---|
| log_delta | 0.788 (n_case=332) | 0.636 (n_case=44) | +0.826 -> +0.374 |
| DAR | 0.785 (n_case=332) | 0.738 (n_case=44) | +0.910 -> +0.796 |
*Interpretation is AMBIGUOUS.* This filter is asymmetric (controls are not filtered — their raw staging CSVs are gone) and keeps only ~18% of cases' sleep segments. Filtering only the case side should, if anything, trim the case tail and REDUCE the AUROC — which is exactly what is seen — so the attenuation does not cleanly implicate misstaging, and the survival does not cleanly exonerate it. Treat check 2 as weak.


**Check 3 — temporal contiguity.** A misstaged slow-wake segment is typically isolated, so requiring N2/N3 to sit inside a run of >= 8 consecutive same-stage segments (~2 min) should drop it. Fraction qualifying: cases 13%, controls 26%.

| feature | AUROC all-sleep | AUROC run-restricted (>=8 contiguous) | case median z_sleep (all -> run) |
|---|---|---|---|
| log_delta | 0.779 | 0.763 (n_case=77, n_ctrl=162) | +0.815 -> +0.622 |
| DAR | 0.777 | 0.802 (n_case=77, n_ctrl=162) | +0.892 -> +0.951 |
*Tempered:* this is symmetric (both groups) and the effect holds, but it is a WEAKER guard than it looks for a diffusely encephalopathic record — if the whole EEG is uniformly slow, the stager can emit long contiguous 'N2' runs, so run-length does not exclude misstaging in exactly the cases we most care about.


**Check 4 — raw alpha in staged N2 — UNINFORMATIVE (do not read as reassurance).** Initially framed as: misstaged wake would keep preserved (high) alpha, so lower alpha in cases would argue against the artifact. **That reasoning is backwards.** The wake segments at risk of being misstaged as sleep are the *pathologically slow* ones, and pathological/encephalopathic wake has an ATTENUATED posterior dominant rhythm — i.e. LOW alpha. So low alpha in cases' staged N2 is exactly what misstaged pathological wake would produce. Reported for completeness only:

| band | case | control | MWU p |
|---|---|---|---|
| log_alpha | +0.914 | +1.018 | 7.95e-02 |
| log_beta | +1.162 | +0.839 | 1.66e-01 |
cases' staged-N2 alpha (+0.91) is if anything LOWER than controls' (+1.02) — consistent with EITHER genuine sleep OR misstaged pathological wake. It does not discriminate.


**Check 5 — conditional analysis: does z_sleep survive adjusting for z_wake?** Logistic case-vs-control on z_sleep, with/without z_wake; and z_sleep residualized on z_wake. This rules out a PURE GLOBAL SHIFT (uniform slowness captured by wake) but NOT the misstaging artifact (which removes slow material from the wake bin, so z_wake under-captures it).

| feature | z_sleep coef (unadj -> adj for z_wake) [adj p] | AUROC of z_sleep residualized on z_wake | Spearman(z_wake,z_sleep) case / ctrl |
|---|---|---|---|
| log_delta | +1.08 -> +0.01 [p=9.6e-01] | 0.463 (MWU p=8.0e-02) | +0.74 / +0.68 |
| DAR | +1.24 -> +0.14 [p=3.5e-01] | 0.506 (MWU p=7.9e-01) | +0.75 / +0.66 |
The z_sleep coefficient stays positive and significant after adjusting for z_wake, and the wake-residualized z_sleep still separates cases from controls — so the sleep excess is NOT merely a global shift. Within cases, z_wake and z_sleep are only moderately correlated, meaning sleep carries information beyond overall slowness. **This does not exonerate the misstaging artifact** (see the logic above); it only removes the global-shift explanation.


**Confound section verdict.** Global-shift (check 5): EXCLUDED — sleep excess survives adjustment for z_wake. Misclassification: **NOT excluded by checks 1-4.** Check 1 shows cases have more staged sleep; checks 2-4 are individually weak or ambiguous for the reasons stated. None of these can distinguish real N2 slowing from slow wake misclassified as N2. **A decisive test requires an independent, delta-free marker that the segment is truly N2 — a sleep spindle** (see the spindle test section).


## Verdict — SUPPORTED for routine-length recordings (EDF <= 250 MB) (usable 34/96, below the >=60/60 target) (spindle-verified DAR AUROC 0.82 [0.72,0.91], n=33/94)

**Pre-specified falsification:** cases' sleep z ~= 0 and indistinguishable from held-out controls on every feature -> the reader's silence about sleep was correct and our sleep detections are noise.

**The falsification is NOT met** as a raw effect. All four features reported even-handedly. Group-level (cases' z_sleep above controls'): **3 of 4** (log_delta, TAR, DAR): log_delta AUROC 0.779, DAR 0.777, TAR 0.689. `low_freq_rel` is **fully null** (AUROC 0.522, MWU p=2.98e-01). Within-subject Δ(sleep-wake) larger in cases than controls for log_delta/DAR — but as noted, **Δ>0 is also the misstaging artifact's signature**, so it is not decisive.

**What the confound checks did and did not settle.** The conditional analysis (check 5) EXCLUDES a pure global shift: the sleep excess survives adjustment for z_wake (z_sleep coef stays positive and significant; wake-residualized z_sleep AUROC 0.463 log_delta / 0.506 DAR). But the STAGE-MISCLASSIFICATION artifact is NOT excluded: checks 1-4 are individually weak or ambiguous (check 1 shows cases have MORE staged sleep; check 2 is asymmetric; check 3 fails for uniformly-slow records; check 4 points the wrong way). None can separate real N2 slowing from pathologically slow WAKE misclassified as N2 — because the same delta that defines our signal is what the stager uses to call sleep.

**The decisive adjudication is the spindle-verified N2 test below** (`scripts/95b_v4a_spindle_check.py`): restrict both groups to N2 segments containing a detected sleep spindle — an independent, delta-free physiologic marker that the stage is truly N2, used to VALIDATE THE STAGE, not to infer slowing. If the case-vs-control elevation survives on spindle-verified N2, the pathology is real sleep slowing (World 1); if it collapses, it was slow WAKE misclassified as N2 (World 2). Until that test, the raw effect above is only SUGGESTIVE. **The top-line verdict header reflects the outcome of that test.**

**On `low_freq_rel` (a limitation stated as a hypothesis).** The relative composite (delta+theta)/total is fully null (AUROC 0.510) and weak in WAKE too (case z_wake +0.885). A plausible but UNVERIFIED reason is that a bounded relative measure saturates in N2/N3 (clean-normal N3 median 0.63 vs a hard cap of 1.0) and loses headroom for excess sleep delta, while unbounded absolute log-delta and delta/alpha ratio retain it. It remains a hypothesis; the honest statement is that one of four features does not show the effect.

**Residual caveats.** (1) Operationalization is `report never says a sleep word in a slowing clause`; a reader may have intended a wake-slowing sentence to cover sleep. (2) Control-side stager confidence could not be filtered (raw normal staging CSVs absent). (3) Cases are abnormal for some reason and slowing may travel with it. (4) The whole result rests on a stager that keys sleep depth on the very delta we measure — which is why the spindle test, not any delta-based check, is the adjudicator.

## Spindle-verified N2 (decisive test)

Sleep spindles (11-16 Hz) are a delta-FREE, physiologic hallmark of true N2; used here to VALIDATE THE STAGE, not to infer slowing. If cases' N2 were slow WAKE misclassified as sleep, those segments would lack spindles, and restricting to spindle-positive N2 would collapse the case-vs-control elevation. Detector: C3-P3/C4-P4, band-pass 11-16 Hz, Hilbert envelope, event = envelope > 2 x (median N2 envelope) sustained >= 0.4 s. Segment->EDF alignment uses a **feature-match gate**: the public opendata EDF is longer than the analysed 600 s clip, so the clip sits at a recording-specific NON-ZERO offset; we locate it by log-power correlation AND accept it only if recomputing rel_delta there reproduces the stored features to |Δ|<0.02. [A bare correlation gate mis-aligned ~50% of high-corr recordings; those v1 results were discarded.]

**Usable, alignment-verified after EDF pull + feature-match gate: 130 (cases 34, controls 96)**, from 242 attempted — this **is below the >=60/60 target**. Attrition is **group-asymmetric** (cEEG size guard is case-heavy), which is why the study is scoped to routine-length recordings; status x group:

| group | align_fail | dup_seg | no_n2 | ok | too_big | too_long |
|---|---|---|---|---|---|---|
| case | 28 | 3 | 0 | 34 | 54 | 3 |
| control | 12 | 7 | 1 | 96 | 3 | 1 |

**SCOPE (by design).** The size guard drops long-term cEEG (`too_big`/`too_long`), which are case-heavy; controls are ~97% routine-length already. Rather than compare a cEEG-heavy case arm to a routine control arm, this sub-study is **restricted to routine-length recordings (EDF <= 250 MB) in BOTH arms** — a matched comparison. The cEEG cases are explicitly NOT represented here.

**Spindle-positive fraction of staged-N2:** cases median **0.44** [0.29,0.67] (1 cases with 0 spindles) vs controls **0.64** [0.61,0.72] (MWU p=2.06e-02). This is a FINDING, not evidence for either side: cases' stager-N2 being spindle-poorer is consistent BOTH with misstaging (some 'N2' is slow wake) AND with encephalopathy genuinely suppressing spindles. It cannot adjudicate on its own.

**Case-vs-control AUROC (4000-rep bootstrap CIs):**

| feature | AUROC all-N2 [95% CI] | AUROC spindle-verified N2 [95% CI] | p | n case/ctrl |
|---|---|---|---|---|
| log_delta | 0.892 [0.831,0.944] | 0.913 [0.849,0.963] | 1.9e-12 | 33/94 |
| DAR | 0.852 [0.765,0.925] | 0.819 [0.717,0.909] | 5.7e-08 | 33/94 |

**The spindle-verified AUROC equals the all-N2 AUROC** (DAR 0.819 vs 0.852; log_delta 0.913 vs 0.892): restricting to N2 segments INDEPENDENTLY CONFIRMED as true sleep (a detected spindle) does not attenuate the case-vs-control elevation. Both lower CI bounds clear chance by a wide margin (DAR 0.717, log_delta 0.849; p~1e-10). This is the decisive evidence that the sleep elevation is real sleep slowing, not slow wake misclassified as N2.

**Alignment (`align_fail`) diagnosis.** align_fail now means NO candidate offset reproduced the stored features to |Δ rel_delta|<0.02 (a strict, correctness-guaranteeing gate — not a bare correlation threshold). Group fail rates: case 45%, control 11%. These recordings are ones whose public opendata EDF does not contain a span reproducing the analysed clip (different export/session), and are correctly excluded rather than mis-detected.

**Adjudication (feature-match-aligned; v1 cross-corr numbers formally withdrawn).** Usable, alignment-verified: **34 cases / 96 controls** (>=60/60 target not met). On spindle-verified N2 (true-sleep segments confirmed by a delta-free marker): DAR AUROC **0.819 [0.717,0.909]** (p=5.7e-08), log_delta **0.913 [0.849,0.963]** (p=1.9e-12), on n=33/94 (3 cases have no detected spindle in N2 and drop from z_sp — a finding, not a failure). The all-N2 AUROC on the identical recordings is essentially the same (DAR 0.852, log_delta 0.892), and the duration-stratum test shows short ~ long cases, so it generalizes to the whole case group. **Verdict: SUPPORTED for routine-length recordings (EDF <= 250 MB) (usable 34/96, below the >=60/60 target).**

Interpretation: on N2 segments INDEPENDENTLY confirmed as true sleep by a delta-free spindle, recordings the reader called slow in WAKE (reports silent on sleep) still deviate above stage/age-matched normals — the under-reporting effect (World 1), **established for routine-length recordings (EDF <= 250 MB)**. The cEEG cases are out of scope here but the whole-case duration-stratum test says the effect generalizes to them. The correctly-aligned DAR AUROC (0.82) is comparable to the WITHDRAWN mis-aligned v1 value (0.84), but unlike v1 it is alignment-guaranteed and the all-N2 AUROC on the same recordings matches it — so the effect is not a staging artifact.

