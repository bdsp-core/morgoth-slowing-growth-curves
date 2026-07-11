# Plan: symmetry-augmented, band-conditioned localization

Refines two ideas (Brandon) into a concrete build. Applies to the internal **decisions** (gate →
lateralize → localize); the reader-facing **description** is deliberately decoupled (see §3).

## 1. Left↔right flip augmentation → antisymmetric models  [VALIDATED]
Because our lateralization features are **signed homologous asymmetries**, a left/right mirror is exactly
`X → −X`, `label L↔R`. Consequences:
- **Doubles the data** and **perfectly balances L/R**, so the model can't exploit the ~3:1 left prior.
- The left prior lives entirely in the **intercept**; dropping it makes the linear model **antisymmetric**
  by construction — the analytic equivalent of infinite flip augmentation.
- **Result (focal lateralizer):** right-side recall 0.52 → **0.88**, balanced acc 0.71 → **0.84**, AUROC
  unchanged (0.867); flip-consistency `|p(L|x)+p(L|−x)−1| = 0.000` (`results/flip_augment.md`,
  `scripts/43`). The consistency check doubles as the **sign-convention audit** — passed.
- **Adopt:** train all L/R models antisymmetric (no intercept) on flip-augmented features; use test-time
  augmentation (average x and −x). Broaden the same mirror aug to the **detectors** (flip is
  label-preserving for normal/generalized and swaps sides for focal/lobe) to regularize away any spurious
  L/R prior everywhere — free extra data.

## 2. Band-conditioned models with multi-band inputs
Route by the **dominant band** of the detected slowing (δ / θ / mixed, from the band call); each route is
its own small **lateralizer + lobe-localizer**, but every route takes **all bands' features as input**
(δ and θ asymmetries/powers) — band-*specific behavior*, band-*agnostic inputs*. Rationale: face validity
(a δ-slowing case is lateralized by a "δ model," not by θ features alone) with the small multi-band
performance gain we measured (band-matched diagonal best; both-bands ≈ best).

**Data-power tension + fix.** Per-route counts (focal-lateralized): δ 169, mixed 317, **θ 41** — θ is
starved, and full fragmentation wastes power. So:
- δ and mixed: their own antisymmetric multi-band models (≈338 / 634 after flip-aug).
- θ: **partial pooling** — a single shared antisymmetric multi-band model with a **dominant-band
  indicator + band×feature interactions**, so θ borrows strength from δ/mixed while still behaving
  band-specifically. (Preferred overall: one conditioned-shared model = full power + band-specific +
  antisymmetric; keep separate δ/mixed models only if they beat it out-of-fold.)
- Same design for the **lobe localizer** (focal only; temporal reliable, others confidence-flagged) and
  for the **generalized anterior↔posterior** axis (not L/R — no flip aug; FIRDA vs OIRDA).

## 3. Reader-facing description is decoupled from the ML
None of the above is surfaced. The report states **how abnormal the key features are**, band-matched to
the call — e.g., *"left temporal delta 3.1 SD above age/stage-matched norm; L>R temporal delta asymmetry
2.6 SD; present in 42% of awake segments."* The ML only decides **whether/what/where**; the deviation
magnitudes (z vs age×sex×stage norms) are the description. Guarantee: the deviations we quote are for the
band(s) we called dominant.

## 4. Build + evaluation protocol
1. `features/asymmetry`: add a `mirror()` helper (channel-swap map / negate signed asyms) — one source of
   truth for augmentation.
2. Lateralizer: antisymmetric multi-band LR, flip-augmented; band-conditioned (shared+interactions).
   Eval by dominant-band stratum with **grouped CV** (a recording and its mirror never split across
   folds); report AUROC + balanced acc + per-side recall + flip-consistency.
3. Lobe localizer (focal-gated) and generalized A-P: same conditioning; report macro-F1 (localization)
   and AUROC (A-P), honest per-class.
4. Report generator: wire gate → band → matched-band deviation description; keep ML internal.
5. Data: region/band-stratified collection to lift θ-focal and posterior-lobe n (the real bottleneck).

## 5b. Age (Brandon's question) — verified
- **Detection & regional deviation are age-normed** (age×sex×stage growth-curve z; per-channel
  age-band-adjusted deviations). **Lateralizer is NOT age-stratified and does not need to be**: signed
  within-subject asymmetry is intrinsically age/sex-controlled, and lateralization AUROC is flat across
  the lifespan (0.81 ≤18y → 0.89 ≥76y). No age-conditioning added.
- **Empirical age-dependent left predominance:** left-fraction of focal-lateralized cases rises 0.65→0.77
  with age (benign temporal slowing of the elderly). We symmetrize it away for the model but REPORT it
  (manuscript Discussion + citations Inui 2001 etc.).

## 6. Targeted theta-focal collection (Brandon's point 1) — search done
Searched all 217,415 reports (`EEGs_And_Reports.csv`, free text + focalSlowing flag): focal + theta +
temporal + lateralized = **48,214 recordings / 9,106 patients; 31,016 / 6,679 NEW** (not in cohort) ->
`results/candidate_focal_theta_temporal.csv`. This is the band/region-stratified ingestion manifest that
lifts the theta-focal (n=41) and posterior-lobe bottlenecks; feed it to the fleet worker. Same query
pattern (flag + text on band/region/side) generates posterior-lobe and other targeted cohorts.
