# Normative-deviation analysis plan: quantitative slowing vs the (biased) report reference

## Premise
Clinical EEG reports are our reference standard, but they are an **imperfect reference with a known,
directional bias**: neurophysiologists under-declare slowing that occurs *in sleep* (theta/delta are
normal sleep features and "how much is too much" is hard to judge by eye), and generalized slowing is
under-called relative to focal. Consequently a study with genuinely pathological sleep slowing is often
reported "normal overall." So we must not treat reports as truth — we (1) show we reproduce expert
determinations *where they are reliable*, and (2) use a population-normative, **stage-stratified** model
to detect what reports systematically miss.

## Two aims
- **Aim 1 — Concordance (criterion validity):** reproduce the determinations that *do* appear in reports.
- **Aim 2 — Normative detection (the thesis):** treat qEEG features from *report-normal* studies as the
  normative distribution across the lifespan and sleep stage; a study whose per-stage feature exceeds that
  normal band is flagged abnormal — including cases the reader missed, especially in sleep.

## The normative model (growth curves)
From **clean-normal** studies only (normal & not abnormal/focal/gen — the contamination fix already done):
percentile curves for each feature × **age × sex × sleep stage** (W/N1/N2/N3/REM). Any study's per-stage
feature is scored as a deviation (z / percentile) from the **stage-matched** normal. Key property: in sleep
the normal band is high and wide (physiologic delta), so only *excess beyond it* is flagged — the
population-calibrated threshold humans lack.

## Report strata (graded reference certainty)
- **N** — report-declared normal (clean normal) → builds the norms.
- **A0** — abnormal overall, no slowing feature named.
- **Ag** — abnormal + *generalized* slowing named (± band).
- **Af** — abnormal + *focal* slowing named (± side/region) ← most reliable.
- Orthogonal tag: **state where abnormality was noted** — wake / sleep / unspecified (from report text).

## Analyses
1. **Concordance where labels are reliable (Aim 1).** Deviation-score AUROC for **Af vs N** (per region/
   side/stage; focal is the trustworthy anchor) and **Ag vs N** per stage. Expectation: strong for Af in all
   stages; for Ag, strong in W/REM, weaker inside N2/N3 (physiologic delta) — quantifying the human-hard case.
2. **Dose-response (construct validity).** Deviation magnitude increases **N < A0 < Ag ≤ Af**. Monotonic
   gradient = the feature measures the same construct experts grade, even where they don't name it (A0).
3. **Sensitivity beyond the reader (Aim 2 — the novel claim).**
   - **(a) Wake→sleep within-subject:** among studies whose report flags abnormality **in wake only**,
     test whether our **sleep-stage** deviations are also elevated vs N. If yes → the abnormality is present
     in sleep and the feature detects it even though the reader didn't call it.
   - **(b) Missed-in-sleep tail:** among **report-normal** studies, quantify the tail with high sleep-stage
     deviation (candidate human-missed abnormals); characterize (age, stage, band, focal vs diffuse).
   - **(c) Discordance map:** where we flag abnormal but the report says normal — test enrichment in
     sleep-heavy studies (high N2/N3 fraction), the predicted failure mode of human reading.
4. **Convergent validity (indirect ground truth).** Deviation should correlate with *independent*
   abnormality markers available in the structured findings — **absent spindles / K-complexes**, abnormal
   PDR, and Morgoth's own gate probability — especially for the sleep cases (Brandon's spindle intuition:
   pathological sleep slowing tends to occur with degraded sleep architecture).

## What we can and cannot conclude
- We **can** show: concordance where reliable; a dose-response gradient; that wake-flagged abnormality
  predicts our sleep deviations; convergent validity with independent markers. Together these make the
  "excess" sleep detections *credible* rather than noise.
- We **cannot** prove a human-missed case is a true positive without an independent gold standard. So we
  frame excess detections as **candidate** abnormalities with convergent support, and propose the definitive
  test as future work: **blinded expert re-read** of high-deviation report-normal sleep studies (and/or
  linkage to clinical outcomes / final diagnoses).

## Paper mapping
- **Methods:** clean-normal normative model (age×sex×stage percentile curves); report strata N/A0/Ag/Af +
  wake/sleep tag; deviation scoring.
- **Results:** (1) concordance (Af, then Ag by stage) → (2) dose-response → (3) wake→sleep + missed-in-sleep
  tail + discordance map → (4) convergent validity.
- **Discussion:** EEG reports are an imperfect, *directionally biased* reference (sleep/generalized
  under-detection); population-normative, stage-aware qEEG is a complement that is *most* valuable exactly
  where human reading is weakest — generalized slowing in sleep. State the imperfect-gold-standard caveat and
  the proposed prospective validation.

## Enablers (status)
- Clean-normal reference — **done**. Per-stage 12k feature table — **rebuilding**. Report strata — derivable
  from findings (`abnormal`, `foc/gen slowing`, sleep-feature cols) + report text (slowing named, wake/sleep
  qualifiers). Per-stage concordance (analysis 1) — running (`scripts/54`). Remaining: strata builder + the
  wake→sleep / missed-tail / discordance / convergent-validity analyses.
