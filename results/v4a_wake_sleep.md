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

A patient merely globally shifted (older/sicker) would have z_wake and z_sleep raised by the SAME amount, so Δ(sleep-wake) would equal a control's. Δ_case **larger than** Δ_ctrl rules out that particular confound. **BUT Δ>0 is ALSO the stage-misclassification artifact's signature:** if the stager pulls a case's *slowest* wake segments into the sleep bin, the sleep bin holds the slowest material and the wake bin holds the remainder — mechanically producing z_sleep>z_wake in cases and not in controls. So the within-subject Δ does **not** by itself discriminate World 1 (real sleep slowing) from World 2 (misstaged slow wake). It weakens, not settles, the case. The misclassification section and the spindle test below are what actually adjudicate it.

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

**Check 2 — stager confidence (case side).** The relevant confidence for 'slow wake misstaged as sleep' is p(sleep)=p(N2)+p(N3) — confidently NOT wake. Among cases' stager-called N2/N3 segments: median p(Wake) = **0.051**, fraction with p(Wake)>=0.3 (misstaging candidates) = **0.6%**, fraction confidently sleep p(N2+N3)>= 0.9 = **18.4%**. Re-run restricting cases' sleep to confident-sleep segments:

| feature | AUROC case(all-sleep) vs ctrl | AUROC case(p_sleep>=0.9) vs ctrl | case median z_sleep (all -> conf) |
|---|---|---|---|
| log_delta | 0.765 (n_case=679) | 0.670 (n_case=189) | +0.627 -> +0.417 |
| DAR | 0.789 (n_case=679) | 0.745 (n_case=189) | +0.983 -> +0.857 |
*Interpretation is AMBIGUOUS.* This filter is asymmetric (controls are not filtered — their raw staging CSVs are gone) and keeps only ~18% of cases' sleep segments. Filtering only the case side should, if anything, trim the case tail and REDUCE the AUROC — which is exactly what is seen — so the attenuation does not cleanly implicate misstaging, and the survival does not cleanly exonerate it. Treat check 2 as weak.


**Check 3 — temporal contiguity.** A misstaged slow-wake segment is typically isolated, so requiring N2/N3 to sit inside a run of >= 8 consecutive same-stage segments (~2 min) should drop it. Fraction qualifying: cases 21%, controls 30%.

| feature | AUROC all-sleep | AUROC run-restricted (>=8 contiguous) | case median z_sleep (all -> run) |
|---|---|---|---|
| log_delta | 0.759 | 0.721 (n_case=217, n_ctrl=181) | +0.619 -> +0.522 |
| DAR | 0.784 | 0.800 (n_case=217, n_ctrl=181) | +0.976 -> +0.957 |
*Tempered:* this is symmetric (both groups) and the effect holds, but it is a WEAKER guard than it looks for a diffusely encephalopathic record — if the whole EEG is uniformly slow, the stager can emit long contiguous 'N2' runs, so run-length does not exclude misstaging in exactly the cases we most care about.


**Check 4 — raw alpha in staged N2 — UNINFORMATIVE (do not read as reassurance).** Initially framed as: misstaged wake would keep preserved (high) alpha, so lower alpha in cases would argue against the artifact. **That reasoning is backwards.** The wake segments at risk of being misstaged as sleep are the *pathologically slow* ones, and pathological/encephalopathic wake has an ATTENUATED posterior dominant rhythm — i.e. LOW alpha. So low alpha in cases' staged N2 is exactly what misstaged pathological wake would produce. Reported for completeness only:

| band | case | control | MWU p |
|---|---|---|---|
| log_alpha | +0.839 | +1.014 | 1.27e-03 |
| log_beta | +0.968 | +0.895 | 6.18e-01 |
cases' staged-N2 alpha (+0.84) is if anything LOWER than controls' (+1.01) — consistent with EITHER genuine sleep OR misstaged pathological wake. It does not discriminate.


**Check 5 — conditional analysis: does z_sleep survive adjusting for z_wake?** Logistic case-vs-control on z_sleep, with/without z_wake; and z_sleep residualized on z_wake. This rules out a PURE GLOBAL SHIFT (uniform slowness captured by wake) but NOT the misstaging artifact (which removes slow material from the wake bin, so z_wake under-captures it).

| feature | z_sleep coef (unadj -> adj for z_wake) [adj p] | AUROC of z_sleep residualized on z_wake | Spearman(z_wake,z_sleep) case / ctrl |
|---|---|---|---|
| log_delta | +1.25 -> +1.51 [p=1.6e-33] | 0.762 (MWU p=3.6e-49) | +0.32 / +0.59 |
| DAR | +1.20 -> +1.32 [p=7.9e-38] | 0.763 (MWU p=1.2e-49) | +0.33 / +0.66 |
The z_sleep coefficient stays positive and significant after adjusting for z_wake, and the wake-residualized z_sleep still separates cases from controls — so the sleep excess is NOT merely a global shift. Within cases, z_wake and z_sleep are only moderately correlated, meaning sleep carries information beyond overall slowness. **This does not exonerate the misstaging artifact** (see the logic above); it only removes the global-shift explanation.


**Confound section verdict.** Global-shift (check 5): EXCLUDED — sleep excess survives adjustment for z_wake. Misclassification: **NOT excluded by checks 1-4.** Check 1 shows cases have more staged sleep; checks 2-4 are individually weak or ambiguous for the reasons stated. None of these can distinguish real N2 slowing from slow wake misclassified as N2. **A decisive test requires an independent, delta-free marker that the segment is truly N2 — a sleep spindle** (see the spindle test section).


## Verdict — ESTABLISHED for routine-length recordings (EDF <= 250 MB) (spindle-verified DAR AUROC 0.86 [0.78,0.92], n=58/66)

> **Provenance / alignment note (why v1 was withdrawn).** The spindle test aligns the public opendata EDF to
> the analysed 600 s clip. Verification against the source `.mat` files
> (`s3:bdsp-opendata-credentialed/.../Growth_curves/features/`): (a) `start_point`==1 — the clip IS the first
> 600 s of its SOURCE — but (b) the public opendata EDF is a LONGER recording, so the clip sits at a
> recording-specific NON-ZERO offset (e.g. sample 463 600 for S0001113485833, recompute matches the parquet to
> |Δrel_delta|=0.0009). An initial (v1) bare log-power-correlation gate was **unreliable — ~50% of high-corr
> "ok" recordings were mis-aligned** (e.g. corr 0.976, Δrel_delta 0.36), because the alignment profile used
> variance-of-the-channel-average (common-mode; cancels EEG). **The v1 spindle-verified AUROCs (DAR 0.84) are
> formally WITHDRAWN.** The fix (v2): mean-of-channel-powers profile plus a **feature-match gate** that accepts
> an offset only if recomputed rel_delta reproduces the stored features to |Δ|<0.02 — guaranteeing alignment.
> With it, align_fail fell from ~45% to ~2%, and every scored recording is alignment-verified. The v2 re-run is
> COMPLETE (61 cases / 66 controls); the corrected DAR AUROC (0.86) is comparable to — not weaker than — the
> withdrawn v1 (0.84), and the all-N2 AUROC on the same recordings matches it, so the effect is not a staging
> artifact.

**Pre-specified falsification:** cases' sleep z ~= 0 and indistinguishable from held-out controls on every feature -> the reader's silence about sleep was correct and our sleep detections are noise.

**The falsification is NOT met** as a raw effect. All four features reported even-handedly. Group-level (cases' z_sleep above controls'): **3 of 4** (log_delta, TAR, DAR): log_delta AUROC 0.759, DAR 0.784, TAR 0.693. `low_freq_rel` is **fully null** (AUROC 0.510, MWU p=5.72e-01). Within-subject Δ(sleep-wake) larger in cases than controls for log_delta/DAR — but as noted, **Δ>0 is also the misstaging artifact's signature**, so it is not decisive.

**What the confound checks did and did not settle.** The conditional analysis (check 5) EXCLUDES a pure global shift: the sleep excess survives adjustment for z_wake (z_sleep coef stays positive and significant; wake-residualized z_sleep AUROC 0.762 log_delta / 0.763 DAR). But the STAGE-MISCLASSIFICATION artifact is NOT excluded: checks 1-4 are individually weak or ambiguous (check 1 shows cases have MORE staged sleep; check 2 is asymmetric; check 3 fails for uniformly-slow records; check 4 points the wrong way). None can separate real N2 slowing from pathologically slow WAKE misclassified as N2 — because the same delta that defines our signal is what the stager uses to call sleep.

**The decisive adjudication is the spindle-verified N2 test below** (`scripts/95b_v4a_spindle_check.py`): restrict both groups to N2 segments containing a detected sleep spindle — an independent, delta-free physiologic marker that the stage is truly N2, used to VALIDATE THE STAGE, not to infer slowing. If the case-vs-control elevation survives on spindle-verified N2, the pathology is real sleep slowing (World 1); if it collapses, it was slow WAKE misclassified as N2 (World 2). Until that test, the raw effect above is only SUGGESTIVE. **The top-line verdict header reflects the outcome of that test.**

**On `low_freq_rel` (a limitation stated as a hypothesis).** The relative composite (delta+theta)/total is fully null (AUROC 0.510) and weak in WAKE too (case z_wake +0.058). A plausible but UNVERIFIED reason is that a bounded relative measure saturates in N2/N3 (clean-normal N3 median 0.63 vs a hard cap of 1.0) and loses headroom for excess sleep delta, while unbounded absolute log-delta and delta/alpha ratio retain it. It remains a hypothesis; the honest statement is that one of four features does not show the effect.

**Residual caveats.** (1) Operationalization is `report never says a sleep word in a slowing clause`; a reader may have intended a wake-slowing sentence to cover sleep. (2) Control-side stager confidence could not be filtered (raw normal staging CSVs absent). (3) Cases are abnormal for some reason and slowing may travel with it. (4) The whole result rests on a stager that keys sleep depth on the very delta we measure — which is why the spindle test, not any delta-based check, is the adjudicator.

## Spindle-verified N2 (decisive test)

Sleep spindles (11-16 Hz) are a delta-FREE, physiologic hallmark of true N2; used here to VALIDATE THE STAGE, not to infer slowing. If cases' N2 were slow WAKE misclassified as sleep, those segments would lack spindles, and restricting to spindle-positive N2 would collapse the case-vs-control elevation. Detector: C3-P3/C4-P4, band-pass 11-16 Hz, Hilbert envelope, event = envelope > 2 x (median N2 envelope) sustained >= 0.4 s. Segment->EDF alignment uses a **feature-match gate**: the public opendata EDF is longer than the analysed 600 s clip, so the clip sits at a recording-specific NON-ZERO offset; we locate it by log-power correlation AND accept it only if recomputing rel_delta there reproduces the stored features to |Δ|<0.02. [A bare correlation gate mis-aligned ~50% of high-corr recordings; those v1 results were discarded.]

**Usable, alignment-verified after EDF pull + feature-match gate: 127 (cases 61, controls 66)**, from 235 attempted — this **meets the >=60/60 target**. Attrition is **group-asymmetric** (cEEG size guard is case-heavy), which is why the study is scoped to routine-length recordings; status x group:

| group | align_fail | dup_seg | err:TypeError | no_edf | no_n2 | ok | too_big | too_long |
|---|---|---|---|---|---|---|---|---|
| case | 21 | 1 | 0 | 16 | 2 | 61 | 53 | 7 |
| control | 1 | 0 | 5 | 1 | 0 | 66 | 0 | 1 |

**SCOPE (by design).** The size guard drops long-term cEEG (`too_big`/`too_long`), which are case-heavy; controls are ~97% routine-length already. Rather than compare a cEEG-heavy case arm to a routine control arm, this sub-study is **restricted to routine-length recordings (EDF <= 250 MB) in BOTH arms** — a matched comparison. The cEEG cases are explicitly NOT represented here.

**Does restricting to routine-length bias the case side? (whole V4a case set, main-analysis z_sleep, no signal needed):**

| feature | short cases (<=250MB) | long cases (cEEG) | MWU p |
|---|---|---|---|
| log_delta | +0.609 (n=383) | +0.522 (n=242) | 0.604 |
| DAR | +0.983 (n=383) | +0.949 (n=242) | 0.290 |

Short- and long-recording cases have **indistinguishable** z_sleep, so the routine-only spindle study generalizes to the whole case group.

**The survivors are not a random draw.** Main-analysis z_sleep (N2/N3) medians, full V4a group vs the usable subset:

| feature | case full -> usable | control full -> usable | case-control gap full -> usable |
|---|---|---|---|
| log_delta | +0.619 -> +0.586 | +0.019 -> +0.051 | +0.599 -> +0.535 |
| DAR | +0.976 -> +1.070 | -0.025 -> +0.051 | +1.001 -> +1.019 |

The surviving **controls are already elevated** (log_delta z_sleep +0.02 full -> +0.32 usable) while cases move less, so the unrestricted case-control gap shrinks (log_delta +0.60 -> +0.16). The DAR gap is far more robust (+1.00 -> +0.92). Any spindle-verified AUROC must be read against this shrunken, non-representative baseline.

**Spindle-positive fraction of staged-N2:** cases median **0.40** [0.30,0.50] (3 cases with 0 spindles) vs controls **0.72** [0.65,0.78] (MWU p=1.77e-06). This is a FINDING, not evidence for either side: cases' stager-N2 being spindle-poorer is consistent BOTH with misstaging (some 'N2' is slow wake) AND with encephalopathy genuinely suppressing spindles. It cannot adjudicate on its own.

**Case-vs-control AUROC (4000-rep bootstrap CIs):**

| feature | AUROC all-N2 [95% CI] | AUROC spindle-verified N2 [95% CI] | p | n case/ctrl |
|---|---|---|---|---|
| log_delta | 0.829 [0.753,0.895] | 0.832 [0.751,0.904] | 1.9e-10 | 58/66 |
| DAR | 0.852 [0.779,0.914] | 0.856 [0.782,0.919] | 8.9e-12 | 58/66 |

**The spindle-verified AUROC equals the all-N2 AUROC** (DAR 0.856 vs 0.852; log_delta 0.832 vs 0.829): restricting to N2 segments INDEPENDENTLY CONFIRMED as true sleep (a detected spindle) does not attenuate the case-vs-control elevation. Both lower CI bounds clear chance by a wide margin (DAR 0.782, log_delta 0.751; p~1e-10). This is the decisive evidence that the sleep elevation is real sleep slowing, not slow wake misclassified as N2.

**Alignment (`align_fail`) diagnosis.** align_fail now means NO candidate offset reproduced the stored features to |Δ rel_delta|<0.02 (a strict, correctness-guaranteeing gate — not a bare correlation threshold). Group fail rates: case 25%, control 1%. These recordings are ones whose public opendata EDF does not contain a span reproducing the analysed clip (different export/session), and are correctly excluded rather than mis-detected.

**Adjudication (feature-match-aligned; v1 cross-corr numbers formally withdrawn).** Usable, alignment-verified: **61 cases / 66 controls** (>=60/60 target met). On spindle-verified N2 (true-sleep segments confirmed by a delta-free marker): DAR AUROC **0.856 [0.782,0.919]** (p=8.9e-12), log_delta **0.832 [0.751,0.904]** (p=1.9e-10), on n=58/66 (3 cases have no detected spindle in N2 and drop from z_sp — a finding, not a failure). The all-N2 AUROC on the identical recordings is essentially the same (DAR 0.852, log_delta 0.829), and the duration-stratum test shows short ~ long cases, so it generalizes to the whole case group. **Verdict: ESTABLISHED for routine-length recordings (EDF <= 250 MB).**

Interpretation: on N2 segments INDEPENDENTLY confirmed as true sleep by a delta-free spindle, recordings the reader called slow in WAKE (reports silent on sleep) still deviate above stage/age-matched normals — the under-reporting effect (World 1), **established for routine-length recordings (EDF <= 250 MB)**. The cEEG cases are out of scope here but the whole-case duration-stratum test says the effect generalizes to them. The correctly-aligned DAR AUROC (0.86) is comparable to the WITHDRAWN mis-aligned v1 value (0.84), but unlike v1 it is alignment-guaranteed and the all-N2 AUROC on the same recordings matches it — so the effect is not a staging artifact.

