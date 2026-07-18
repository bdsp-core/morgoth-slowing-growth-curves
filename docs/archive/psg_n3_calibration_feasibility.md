# Feasibility: PSG data to fill the adult-N3 norm gap (with EEG↔PSG calibration)

**Verdict: feasible and high-value.** PSG (overnight sleep) is the gold standard for deep sleep and
covers N3 densely at exactly the adult ages where our routine-EEG N3 norm dies (>~36). The
[SleepEEGBasedBrainAge](https://github.com/bdsp-core/SleepEEGBasedBrainAge) pipeline (Sun et al.,
*Neurobiol Aging* 2019 — Westover lab) already computes the right quantities; the one real challenge is
the montage/reference difference, which Brandon's proposed simple calibration handles.

## Why the fit is good (evidence from the repo)
- **Same feature framework**: multitaper PSD → band powers (absolute **and** relative) + inter-band
  ratios, resampled to **200 Hz** (identical to our morgoth pipeline; ours 0.5–~30 Hz vs their 0.5–20).
- **The features are literally our slowing features, already per-stage including N3.** Their model
  feature list has `delta_bandpower_mean_C_N3`, `delta_theta_mean_C_N3` (= our DTR), `delta_alpha_mean_C_N3`
  (= our DAR), per central channel, per stage (N1/N2/N3). So PSG N3 δ-power / DAR / DTR / rel-δ map
  directly onto the curves we fit.
- **Minimal-montage model exists** (`brain_age_model_c`): works from central channels only — SHHS is
  just C3-A2 / C4-A1. So we don't need a full 10-20 montage from PSG.
- **Datasets span the gap**: SHHS/MrOS/MESA (older adults, community) + WSC/STAGES (wider ages) — all on
  BDSP — give tens of thousands of healthy N3 nights, heaviest at 60–90 (our worst EEG bins: 16 and 15).

## The one real problem: montage / reference
- PSG central EEG = **C3-A2 / C4-A1** (referential to contralateral mastoid).
- Our norms = **18 bipolar double-banana**; central region = F3-C3 / C3-P3, whole_head = all 18.
- Referential vs bipolar changes absolute power a lot, **but relative power and ratios (rel_δ, DAR, DTR)
  are far more montage-robust** — so calibrate on those, on the **central region both modalities share**
  (define the adult-N3 norm on central, not whole_head).

## Calibration (Brandon's approach, made concrete)
Standard domain-shift / batch-effect correction:
1. **Define healthy PSG** to match our clean-normal (per-dataset metadata: low AHI / no apnea, no
   sleep disorder, no CNS-active meds). [needs the dataset metadata — not hard-coded in the repo's step1]
2. **Overlap set** = ages present in BOTH (routine-EEG ~18–75 ∩ PSG) × the stages where **EEG norms are
   well-powered** (W, N1, N2, REM), central region, per feature (rel_δ, DAR, DTR; optionally log-δ).
3. **Fit a simple per-feature transform** f: PSG→EEG on the overlap (age-matched, per stage) — mean+SD
   alignment (z-match) or quantile mapping; a single f per feature, pooled across the overlap stages.
4. **Validate stage-independence** (the crux assumption): fit f on {W,N1,N2}, test that it reproduces the
   **REM** EEG norm from PSG REM (a held-out overlap stage). Good transfer → trust f for N3.
5. **Apply f to PSG N3** central features → EEG-equivalent N3 → fit the adult-N3 growth curve; report it
   as *calibrated-from-PSG* with the validation metrics.

## What we can / cannot claim
- **Can**: a much denser, lifespan-spanning adult-N3 norm; a transform validated on non-N3 stages;
  mutual cross-check against the same-modality EEG N3 fill (below) where they overlap in age.
- **Cannot**: directly validate N3 itself (there is no adult-EEG-N3 ground truth — that's the gap). The
  N3 curve rests on the assumption that the montage correction is **stage-independent** (testable on
  W/N1/N2/REM, not on N3). Frame it honestly as a calibrated estimate with that caveat.
- Residual population confound (community sleep cohorts vs clinical EEG) beyond montage — mitigated by
  age-matching + the normative (deviation-from-normal) framing, but state it.

## Relationship to the EEG expansion pilot (running now)
These are complementary, not competing:
- **EEG long-normal expansion** (fleet pilot, `fleet/manifest_pilot.jsonl`) fills N3 from the **same
  modality** → **no calibration**, the cleanest fill; but the oldest bins (75+) may still be thinner.
- **PSG-calibrated** adds effectively unlimited healthy N3 across the adult lifespan, strongest exactly
  at 60–90.
- **Best outcome**: do both. Where the two N3 curves overlap in age, agreement is strong mutual
  validation of both the EEG fill and the PSG calibration.

## Next steps if we proceed
1. Pull one PSG cohort's central features + hypnograms + metadata (SHHS is the natural first — big,
   older, already in the repo's example path) via BDSP S3.
2. Compute per-(subject, stage) central rel_δ/DAR/DTR with **our** extractor (or reuse their step2) so
   the pipeline is identical to the EEG side.
3. Fit + validate the transform (steps 2–4 above) on the overlap; if REM transfers, build the N3 curve.
4. Overlay against the EEG-expansion N3 curve as the cross-check.
