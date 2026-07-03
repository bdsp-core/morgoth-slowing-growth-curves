# Autonomous execution plan (v1, stage-agnostic)

Goal: from the pulled Growth_curves features + metadata (age/sex/label), produce v1 **growth curves**
and a **discrimination study** of which slowing features separate normal / focal / generalized —
everything reproducible from `metadata/cohort_metadata.csv` + `data/raw/` + these scripts.

**Hard blocker (out of scope for v1):** sleep-stage-specific norms. The Growth_curves set is unstaged
and staging needs raw EEG (not in open S3) + a GPU (see docs/sleep_staging.md). v1 is stage-agnostic;
the pipeline is wired so stages drop in later as a groupby key.

## Phases
- **A. Features** `scripts/03_compute_features.py` → `data/derived/recording_features.parquet`
  (recording × region: log band powers, rel powers, DAR/TAR/DTR; median over 43 segments) +
  `recording_asymmetry.parquet` (L/R log-ratios). Segment-level cached too for scoring.
- **B. Curves** `scripts/04_fit_reference_models.py` → age×sex percentile curves on `normal/`,
  `data/derived/growth_curves/*.parquet` + `figures/curves/*.png`.
- **C. QC** `notebooks/02_feature_qc.md`-style checks in `scripts/qc_checks.py` → `figures/qc/`.
- **D. Scoring** `scripts/05_score_patients.py` → per-recording burden/patient-z/topography/phrase →
  `data/derived/scores.parquet`.
- **E. Discrimination** `scripts/06_discrimination.py` → per-feature AUC (normal-vs-focal,
  normal-vs-generalized, focal-vs-generalized) + overlay figures → `results/discrimination.md`.
- **F. Write-up** `results/RESULTS.md` with ranked features, figures, example report sentences.

## Modeling choices
- Unit = recording (≈1/patient). Percentiles [3,10,25,50,75,90,97].
- Curves: quantile regression with natural-cubic-spline age basis, fit per sex; robust fallback =
  sliding-window empirical percentiles (window ~±5 yr, min n).
- Powers log-transformed; ratios computed from region-mean band powers.
- Age cleaned to [0,120]; drop the 18 implausible rows.
- Patient-level z: empirical percentile→z of burden vs the LOSO null from normals.

## Status log (updated as I go)
- [x] A features (recording_features/asymmetry/segment_features.parquet)
- [x] B curves (growth_curves.parquet + figures/curves/*.png; delta developmental trajectory validated)
- [x] C QC (normal z centered on 0; curves physiologically sane)
- [x] D scoring (scores.parquet, topography, example_reports.md)
- [x] E discrimination (results/discrimination.md; log_delta/log_theta/TAR top, AUC~0.73-0.75 adj)
- [x] F write-up (results/RESULTS.md)
- [~] STAGING (stretch): raw EEG downloading; torch+MPS ready; adapting morgoth2 infer next.
