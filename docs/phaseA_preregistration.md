# Phase A / B pre-registration — our normative model vs the expert panel

**Written 2026-07-09, BEFORE our model has been scored against any OccasionNoise or MoE expert label.**

Why this document exists: twice this week I proposed a reframing immediately after a null result (the severity
null in V1, then the "we see what the reader misses" story). That is how a null gets laundered into a finding.
The predictions below are fixed now. Whatever comes out, this file is not edited — results go in
`results/occasion_model_vs_experts.md`, and disagreements with these predictions get reported as such.

---

## What is already known (no model involved)

From `results/occasion_human_ceiling.md` and `results/moe_human_ceiling.md`:

- Expert-vs-consensus balanced accuracy: **0.801** focal slowing, **0.809** generalized slowing.
- Between-rater Fleiss κ: **0.373** focal slowing, **0.450** generalized slowing (vs 0.585 / 0.739 for
  epileptiform discharges — slowing is the least reliable thing experts judge).
- Within-rater (same expert, re-read): κ **0.563** focal, **0.642** generalized.
- MoE band agreement between experts, conditional on both calling slowing: exact band-set match **0.541**
  (focal), **0.266** (generalized); δ-vs-θ **0.576** / **0.434**.
- Morgoth vs expert majority: AUROC **0.923** focal, **0.895** generalized; but its thresholded operating
  point is bal-acc **0.714** / **0.667** — high specificity, poor sensitivity.

---

## Phase A — our stage-matched deviation score vs the expert majority

**Method, fixed in advance.** Run the *unchanged* pipeline on the 100 OccasionNoise EDFs: MNE read (pyedflib
rejects the de-identified `startdate`), channel rename T7→T3, T8→T4, P7→T5, P8→T6, drop EKG; bipolar
double-banana; artifact rejection; 15-s segments; multitaper; `features_31`; **sleep staging with the same
stager used to build the norms**; each segment z-scored against **its own stage's** age-matched normal curve.
Age and sex come from the EDF patient field. No refitting, no threshold tuning on these data.

Two scorings, both reported:
1. **W/N1 restricted**, routine (alert) reference — our primary, vigilance-matched design.
2. **All stages**, each segment against its own stage's norm — because the experts read the entire study.

Primary features per the existing results: **TAR** (W) and **log_delta** (N1) for generalized; regional
max-deviation and homologous asymmetry for focal.

### Predictions (falsifiable)

- **P1.** Generalized slowing, our AUROC vs expert majority: **0.85–0.93**. Rationale: 0.875 against report
  labels in-cohort, and the expert majority should be a *cleaner* target than a single reader's report, which
  argues for the upper half of that range. **Fails if < 0.80.**
- **P2.** Focal slowing, our AUROC: **0.70–0.85**, i.e. clearly worse than generalized. Rationale: our focal
  discrimination has always been weaker (TAR L_temporal 0.704) and localization is our weakest axis.
  **Fails if focal ≥ generalized.**
- **P3.** Our ROC will pass **above the mean expert operating point** (bal-acc 0.801 / 0.809) for generalized
  slowing. **Fails if the mean expert point lies above our curve.**
- **P4.** Our AUROC will **exceed Morgoth's thresholded balanced accuracy** (0.714 / 0.667) but **not exceed
  Morgoth's AUROC** (0.923 / 0.895) for focal slowing. Morgoth is an expert-calibrated foundation model with
  full morphological access; we are six spectral features. **Fails if we beat Morgoth's AUROC on focal.**
- **P5.** The **W/N1-restricted** score will beat the **all-stage** score for generalized slowing. This is the
  paper's central methodological claim, tested on external data for the first time. **Fails if all-stage ≥
  W/N1.** *(Caveat that cuts against us: the experts read the whole study including sleep, so an all-stage
  score is arguably better matched to their target. If P5 fails, that is the honest reading, not a bug.)*

**Interpretation fixed in advance.** If P1 and P3 hold, the claim we may make is: *"our stage-matched
deviation score agrees with the expert consensus as well as an individual expert does, on an external test set,
with no refitting."* We may **not** claim superiority to experts from AUROC alone — an AUROC compares a ranking
to a binary vote and is a different quantity from an expert's balanced accuracy at their own operating point.
Any superiority claim requires choosing our threshold **without** these data.

---

## Phase B — the consensus proportion as a graded target

The fraction of the 18 experts who marked slowing is a **graded, human, quantitative** target. It is not an
adjective, and it is available for every EEG.

- **P6.** Our deviation z will correlate with the consensus proportion for generalized slowing at Spearman
  **ρ ≥ 0.45**. **Fails if ρ < 0.30.**
- **P7.** This correlation will **exceed** the severity correlation we obtained against the report adjective
  (ρ = 0.050, n.s.; `results/severity_prevalence_recalibrated.md`). **Fails if ρ ≤ 0.15.**

**What this would and would not mean — fixed in advance.** The consensus proportion measures **conspicuity**:
how many trained readers notice the slowing. It is *not* a measure of how severe the underlying pathology is.
If P6 and P7 hold, the honest claim is that our score tracks *how apparent slowing is to experts*, recovering a
graded human-referenced axis that the report adjective failed to provide — **not** that we have validated a
severity scale. The V1 severity null stands regardless of the outcome here, and §3.4b of the manuscript is not
to be softened on the basis of Phase B.

If P6 fails, the conclusion is that our score does not track human-perceived slowing magnitude at all, and the
paper claims detection only.

---

## Analysis integrity

- One rater in MoE (`bwestove`) is an author. Excluded from any consensus used to validate this system;
  reported as a sensitivity.
- Rater identities are anonymized (`R01…Rnn`) in every artifact; usernames are never committed.
- OccasionNoise is **enriched by design** (20/20/20/20/16/4). AUROC and κ are prevalence-robust; PPV, NPV and
  accuracy are not, and will not be reported.
- Consensus is not truth. All statements are "agreement with consensus," never "accuracy." For sleep slowing
  we have argued experts systematically under-call (V4a); a majority can be wrong together.
- **Stager provenance risk.** The exact stager checkpoint used to build our norms (`ss_hm_1.pth`) lived in the
  now-deleted fleet bucket. If a substitute is used, it must first be validated by re-staging recordings whose
  fleet stages we still hold and demonstrating agreement; the agreement figure is reported alongside Phase A.
  If agreement is poor, Phase A is invalid and must wait for the original checkpoint.

---

## AMENDMENT — 2026-07-09, after two corrections from MBW

**Disclosure of what was known when this amendment was written.** Predictions P1–P7 above were fixed before
any expert label was touched. This amendment was written **after** running `scripts/92` on *Morgoth's*
predictions (which ship with OccasionNoise), i.e. after seeing the achievable AUROC and the expert κ
distribution on this task — but **before** our own normative score has been computed on a single one of these
EEGs. P8–P10 are therefore weaker evidence than P1–P7 and are labelled as such.

### Correction 1 — an earlier claim of mine was simply wrong

I wrote: *"We cannot plausibly be better than two experts agree with each other."* **False.** If each expert is
(latent truth + noise), two experts compound two error sources while an accurate algorithm carries one.
Classical test theory: the correlation of two parallel noisy measures equals the reliability, whereas the
correlation of a *perfect* measure with a noisy one equals √reliability. An algorithm at the latent truth
should score **κ_ae ≈ √κ_ee**. Expert errors are correlated (shared training, shared blind spots such as
under-calling sleep slowing), which inflates κ_ee and makes √κ_ee a **conservative** target.

This is already demonstrated: recalibrated Morgoth reaches κ_ae = 0.471 vs κ_ee = 0.403 on focal slowing
(Δ = +0.068, 95% CI +0.014 to +0.136). `results/ea_irr_and_recalibration.md`.

**The residual, legitimate concern is different and survives:** our reported band agreement of 0.74 was
computed against *report text*, with *our own extractor*, on a single report per recording. That number may be
measuring how well we parse the report's band word. The fix is not to distrust 0.74 for being high — it is to
recompute band agreement against the **MoE per-expert band labels**, where there is no text extractor in the
loop.

- **P8 (weak).** Our stage-matched score, thresholded leave-one-out, will reach κ_ae ≥ the median κ_ee for
  generalized slowing (0.450–0.500). **Fails if κ_ae < κ_ee − 0.05.**
- **P9 (weak).** Neither Morgoth nor our score will reach the attenuation benchmark √κ_ee (0.635 focal,
  0.707 generalized), i.e. neither is at the latent truth. **Fails if either exceeds it.**

### Correction 2 — expert agreement is not the truth criterion for a measurement

"Relative delta in wake is at the 95th percentile for this age" is a **measurement**, true or false
independent of whether any expert noticed it. Norms make it so. Expert agreement therefore validates
**concordance and communication**, not correctness, and it cannot be the criterion by which the *description*
axis is judged.

Consequence, fixed now: agreement analyses are reported as **concordance with human perception**, and the
description's validity rests on measurement properties instead — test–retest of our own score, dose–response,
and convergent validity (V4b). **This does not resurrect V1.** The severity null stands exactly as written:
we do not reproduce the reader's adjective. What changes is only the interpretation of *why that was ever the
target*, and §3.4b is not softened.

### Correction 3 — evaluate the system we can build, not its default settings

Morgoth's shipped threshold gives near-perfect specificity and poor sensitivity. Recalibration is part of
building the system, so it is done and reported, with every threshold fitted leave-one-out:

| | shipped | LOO Platt @0.5 | LOO Youden | avg expert |
|---|---|---|---|---|
| focal slowing (bal-acc) | 0.714 | 0.780 | **0.845** | 0.815 |
| generalized slowing (bal-acc) | 0.667 | 0.747 | **0.814** | 0.808 |

- **P10 (weak).** Applying the same LOO recalibration to our normative score will raise its balanced accuracy
  by ≥ 0.05 over a naive z > 2 cut. **Fails if the gain is < 0.02.**

Recalibration cannot change AUROC. Any comparison to experts at an operating point must state which threshold
was used and how it was chosen; a threshold chosen on the evaluation data is reported as optimistic.
