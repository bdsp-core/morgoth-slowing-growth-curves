# Validation plan — what it takes to support "equal or greater value than a clinical neurophysiologist"

The normative foundation and detection are established (Figures 1–2), and detection survives the
report-pairing audit. **Severity grading is a null result** (V1). The remaining work is what licenses the
*comparative* claim. Five items, in priority order. See `docs/methods_audit.md` for what is verified,
what is assumed, and what is broken.

---

## V1. Recalibrate severity and prevalence — **DONE, and it is a NULL result**

**What we did.** Fixed five real defects: (1) `peak_z` was a *maximum* over hundreds of segments (max 19.4 =
artifact) -> robust p90; (2) the adjective extractor returned the first word in *table order* anywhere in the
slowing context, ignoring negation -> clause-scoped, negation-aware, modifier *nearest* to "slow";
(3) focal severity was scored on a whole-head statistic -> scored in the max-deviation region;
(4) scoring ran over *all* segments, though abnormal recordings are only 44.5% wake, so the score was
confounded with how much the patient slept -> restricted to W/N1 (required building abnormal segment stages,
`scripts/87`); (5) 17.2% of recordings carried a report **broadcast from a sibling study** of the same
patient -> restricted to cleanly-paired recordings (`scripts/88`).

**Result.** Severity **rho = 0.050 (p = 0.17, n = 753)**. Null. Prevalence vs the reader's frequency word:
rho = 0.077 (p = 3.3e-6, n = 3,626) — significant, clinically negligible.

**It is not a search failure.** `scripts/89_severity_axis_sweep.py` swept **168 combinations** (7 features x
4 statistics x {raw, z} x {generalized, focal, all}). Largest |rho| anywhere = **0.179**, which fails
Bonferroni (0.05/168 = 3.0e-4; best p = 6.8e-4) and has the **wrong sign**. Raw ~= z (0.159 vs 0.179), so it
is not a normalization artifact.

**Explanation, now measured (V2).** The adjective is attached to a judgement of **low reliability**: an
independent panel of 18 electroencephalographers agrees on slowing at Fleiss κ 0.373 (focal) / 0.450
(generalized), and a reader re-reading the *same* EEG reproduces their own call at κ 0.563 / 0.642. Band
agreement is worse (κ 0.09-0.38). A measurement cannot correlate strongly with a rating that noisy.

*(Retracted: an earlier version of this document hypothesised that clinicians grade diffuse slowing by
posterior dominant rhythm frequency. MBW: wrong. PDR grading and slowing grading are separate tasks, reported
separately. PDR is out of scope and must not be used to infer slowing.)*

**Consequence for the paper.** We claim detection (AUROC 0.85-0.88) and dose-response across report strata
(rho 0.50-0.55). We **do not** claim severity grading. Manuscript SS3.4b and SS5 now say so explicitly.

---

## V2. The human ceiling — **DATA LOCATED AND MEASURED** (2026-07-09)

Two Box datasets supply it. Full exploration, numbers, and plan: **`docs/human_ceiling_plan.md`**.

- **OccasionNoise** — 100 EEGs (EDF, 20ch, 200 Hz, ~50 min; age/sex in the EDF patient field), **18 experts**,
  recording-level votes for focal/generalized x epileptiform/non-epileptiform, **plus a Part I / Part II
  re-read by 15 raters** (within-rater test-retest), plus a signed-report category per EEG.
- **MoE** — 1,000 + 962 events, 18 experts, **band-resolved** focal/gen slowing. Rounds are *disjoint event
  batches* (zero shared event ids), so no within-rater estimate here. Rater coverage 7-1,000 events.

**The ceiling, measured.** Slowing is the least reliable thing experts judge:

| axis | Fleiss κ (between) | expert-vs-consensus balanced acc | within-rater κ (re-read) |
|---|---|---|---|
| Focal **epileptiform** | 0.585 | — | 0.716 |
| **Focal slowing** | **0.373** | **0.801** (se .703, sp .899) | **0.563** |
| Generalized **epileptiform** | 0.739 | — | 0.832 |
| **Generalized slowing** | **0.450** | **0.809** (se .735, sp .884) | **0.642** |

Band agreement is worse still (MoE pairwise Cohen κ): focal-delta 0.352, **focal-theta 0.087**,
gen-delta 0.323, gen-theta 0.317. And on EEGs whose **signed report** said focal non-epileptiform, only
**50.8%** of experts marked focal slowing (generalized: 64.4%).

**Consequences.**
1. Our detection AUROC (0.848 W / 0.875 N1) must be restated as agreement **against a ceiling of ~0.80
   balanced accuracy**, measured on the same data. Phase A of the ceiling plan does exactly this: run our
   unchanged pipeline on the 100 EDFs as a true **external test set**, and overlay each expert as an operating
   point on our ROC.
2. The V1 **severity null is partly a ceiling effect** — experts agree on band at κ ≈ 0.09-0.35 and do not
   reproduce their own slowing call (κ 0.56-0.64). This must be argued with these numbers, not asserted.
3. **New graded target:** the *consensus proportion* (fraction of 18 experts who saw slowing) is a human,
   quantitative measure of **conspicuity**. Testing our z against it may honestly recover a severity-like axis.
   Pre-register the prediction first (see the standing risk in V4).
4. `bwestove` is one of the MoE raters. Disclose, and exclude that rater from validating this system.

---

## V3. Blinded head-to-head — the actual demonstration

Component metrics (AUROC, per-axis agreement) never demonstrate *value*. The definitive test:

1. Sample N ≈ 150–200 recordings gated in by Morgoth (stratified: focal / generalized; wake-only /
   sleep-accentuated; a range of deviation magnitudes), plus a set of report-normal controls.
2. For each, prepare **two descriptions**: (a) the slowing sentence(s) from the original clinical report,
   (b) our generated sentence. Strip all identifying formatting; randomize order; blind the raters to source.
3. Independent neurophysiologists (≥2, not the original readers) rate each description on: **accuracy**,
   **completeness**, **localization correctness**, **usefulness for management**, and give a forced-choice
   preference (A / B / equivalent), while viewing the raw EEG.
4. Primary endpoint: **non-inferiority** of the generated description on a preference/utility scale.
   Secondary: where our description is *preferred* (hypothesis: sleep-accentuated and quantitatively graded
   cases) and where it fails (hypothesis: rare posterior foci, morphology-dependent band calls).

This converts "same value or more" from an assertion into a measured result.

---

## V4. The "adds-value" analyses — what they mean, in plain terms

**First, correct a bad framing.** An earlier draft of this section said that perfectly reproducing the clinical
report would make us "a slower, more expensive neurophysiologist." That is backwards. A system that reproduced
the report perfectly would be **enormously valuable**: automatic, near-instant, free at the margin, perfectly
consistent, and available at 3 a.m. in a hospital with no neurophysiologist on staff. Automation at scale *is*
a primary clinical value proposition, and the paper should say so plainly.

The real difficulty is **measurement**, not value:

1. **The report is a noisy standard, so agreement with it is bounded by its own reliability.** Published
   inter-rater kappa for background abnormality/slowing is roughly 0.4–0.6. Our band agreement of 0.74 is
   therefore uninterpretable in isolation: it could be *at* the human ceiling (a major result) or far below it
   (a weak one). We cannot tell, because we have never measured the ceiling. That is what V2 (MOE) is for, and
   why "equal value" is currently not merely unproven but **unfalsifiable**.

2. **Agreement metrics actively penalize being right.** If we correctly flag N2 slowing that the reader never
   attempted to assess, an agreement metric scores it as our false positive. Optimizing agreement therefore
   trains a model to *inherit the reader's blind spots*. Agreement alone cannot distinguish a better instrument
   from a better mimic.

So the paper needs two distinct kinds of evidence: **(i)** agreement with the report, referenced to the human
ceiling (V2, V3); and **(ii)** evidence that our *disagreements* are right rather than wrong (V4a, V4b).
Neither V4a nor V4b requires new labels.

### The problem V4a and V4b solve

When our model calls a recording abnormal and the report calls it normal, there are two possible worlds and no
gold standard to tell them apart:

- **World 1 (we add value):** the slowing is really there, and the reader did not mention it.
- **World 2 (we are broken):** the slowing is not there, and we are producing false positives.

Every "we detect what reports under-report" claim in the literature quietly assumes World 1. V4a and V4b are
designed to *distinguish* them.

**A standing risk to guard against.** We arrived at the "we see what the reader misses" framing in the same
week we discovered that we cannot reproduce the reader's severity grade (V1). Those two facts must be kept
apart. The under-reporting hypothesis has to earn its keep with a **pre-specified, falsifiable** prediction —
V4a's sleep-stage z, which can come out at zero — and must not become a consolation story for a null result.
If V4a fails, the honest conclusion is that we are a good detector with an uncalibrated description, and we
say exactly that.

---

**V4a — the within-subject wake→sleep test.** *(now runnable for the first time)*

*The clinical premise.* Deciding "is there too much delta in N2?" by eye is genuinely hard, because N2 and N3
are **supposed** to be full of delta. There is no memorized normal value for it. Readers therefore comment on
wake slowing and stay largely silent about sleep slowing — not because sleep slowing is absent, but because
the judgment is unreliable and rarely attempted.

*The design.* Take recordings whose report names slowing **without ever mentioning sleep**, and which contain
scored sleep. For each one, compute the deviation z separately in W and in N2/N3, each against its own
**stage- and age-matched** normal curve. If the pathology really is present in sleep and merely unnamed, these
recordings should sit **above** clean-normals of the same age *in the sleep stages too*, despite the report
saying nothing about sleep.

*Why it is convincing.* The comparison lives **inside one recording**. We are not comparing sick people to
healthy people, so it cannot be explained away by the patients being older, sicker, or medicated. We are
asking whether the same brain the reader called slow in wake also deviates in sleep, where the reader was
silent. **What would falsify it:** if sleep z ≈ 0, the reader's silence was correct, and our sleep-stage
detections are noise. That is a real risk of failure, which is what makes the test worth running.

*Newly possible:* this needs sleep stages for **abnormal** recordings, which did not exist until
`scripts/87_build_abnormal_stages.py` (313,446 segment-stages over 7,408 abnormal recordings).

---

**V4b — convergent validity for the "excess" detections.**

*The design.* Take report-**normal** recordings that we score in the **top decile** of sleep-stage deviation --
our putative missed abnormalities. Ask whether they also look abnormal on evidence we **did not use to select
them**: Morgoth's p(abnormal); the judgement of the independent expert panel where such recordings exist; and
enrichment for downstream clinical outcomes if linkable.

**Not PDR, and not spindles/K-complexes.** An earlier version proposed those as convergent markers. They are
*separate findings*, graded and reported separately from slowing; using them to infer slowing is a category
error (MBW). They are also report-derived here, hence contaminated by the broadcast defect (V5).

*The logic.* No single marker is a gold standard. But if a group chosen purely for high sleep delta *also*
turns out to have slower PDR and fewer spindles and higher p(abnormal), that **concordance across
independently-derived measurements** is what makes "we found something real" credible. If instead they look
exactly like normals on all of them, our excess detections are model noise and we should say so.

*Two caveats that must be stated when this is run.*
1. **Morgoth is report-calibrated**, so it partially inherits the same reader blind spots and is not a fully
   independent witness. It is supporting evidence, not proof.
2. **PDR / spindle / K-complex flags in `data/findings/` are derived from report text**, which is subject to
   the broadcast defect in V5 and to the very under-reporting we are trying to demonstrate. Using them as
   "independent" evidence is close to circular. **These markers must be measured from the signal**, not read
   off the report. (Measuring PDR from the signal is separately needed for V1.)

---

**V4c — dose-response across report strata.** ✅ **Done** (Figure 3): median z rises monotonically
**−0.11 → +0.43 → +1.49** across clean-normal → abnormal-with-no-slowing-named → abnormal-with-slowing-named
(Spearman ρ = 0.50–0.55).

The middle stratum is the point. Recordings the reader called abnormal *without naming slowing* already
deviate by ≈ +0.4 SD. That is the first quantitative hint of World 1: slowing that was present but unstated.
It is a hint, not proof, because those recordings are abnormal for *some* reason and slowing may travel with
it. V4a and V4b are what convert the hint into evidence.

---

Together, V4a–c support the claim that the system is **a stage-aware normative complement that is most
valuable exactly where expert reading is weakest** — on top of, not instead of, the value of automating the
read at all. Reproducing the report is worth a great deal; the point is that agreement with the report cannot
by itself *measure* whether we have done so, nor credit us when we are right and the reader is not. Note the honest tension with V1: we cannot
grade severity the way a reader does, and we are simultaneously claiming to see what the reader misses. Both
can be true — a thermometer does not reproduce "feels feverish," and is still worth having — but the paper
must say so plainly rather than let the reader assume we do both.

---

## V5. Report-to-recording pairing — repair is heuristic (NEW, from the 2026-07-09 audit)

`EEGs_And_Reports.csv` is an EEG x report join made at the **patient** level: one report is stamped onto a
mean of 2.9 EEGs (max **170**) of that patient. Our `(bdsp_id, date)` join therefore selected the right *row*
with, 17.2% of the time, the wrong *text*. `scripts/88_report_pairing_audit.py` assigns each report to the
EEG nearest it in time and writes `clean_pair` to `data/derived/report_pairing.parquet`.

**This is a heuristic.** `|time_diff|` for unambiguously-owned reports has median 14.2 h, p90 203 h — it is an
order-to-study offset, not a study timestamp. **Ask BDSP for a true report<->study key.** Until then:
- filter on `clean_pair` for anything derived from report text;
- detection is insensitive to it (all AUROCs within bootstrap CI, `results/detection_pairing_sensitivity.md`);
- see `docs/methods_audit.md` for the full verified/assumed/broken accounting.

Two further defects found in the same audit: `bdsp_id` is a **patient-at-site key, not a recording key**
(352 patients have >=2 recordings, collapsed by `drop_duplicates("bdsp_id")` and by the date-stripped feature
tables); and per-stage "best feature" AUROCs are selected and reported on the same data (needs nested CV).

---

## Also outstanding
- Figure 5 pipeline schematic — artist brief written (`docs/figure5_pipeline_schematic_brief.md`).
- Region localization is weak (macro-F1 0.23; temporal 0.54, posterior <0.1). Either narrow the claim to
  **side + temporal**, or run region-stratified collection.
- Table 1 — done (`results/table1.md`).
