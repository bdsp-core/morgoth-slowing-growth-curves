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

## Status (v2, updated live)

**Done & committed**
- v1 stage-pooled: features, age×sex growth curves, discrimination (log_delta/theta/TAR AUC 0.73–0.75),
  scoring, report phrases. Gallery (artifact) + PDF.
- **Sleep staging** (morgoth2 `ss_hm_1.pth` on MPS) — validated (W60/N1/N2/N3/REM sane). normal+focal
  staged; general in progress.
- **Stage-specific curves** — normal delta rises W<N1<N2<N3 (validated physiology). figures/stage_curves/.
- **Stage-aware descriptive scoring** — prevalence, persistence (runs/episodes), stage-accentuation,
  only-in-sleep; normals prevalence≈0 (calibrated). results/example_reports_v2.md.
- **Reproducible Python feature extractor** (features/extract.py) from raw EEG — validated vs JJ
  (per-band log-power r=0.89–0.95); io/raw.py handles v5+v7.3 raw.
- **Per-channel (18) + homologous-pair (8) features** for focal localization (recording.py).
- Docs: report_architecture (3-tier Morgoth gate), coverage_by_stage (+ expansion via
  bdsp-opendata-repository, labeled long EEGs, not PSG), sleep_staging, data_dictionary, phase0.
- Morgoth run instructions for collaborator (in ../tele-eeg-publishing).

**Running in background**
- Morgoth **gate heads** NORMAL.pth + SLOWING.pth over all groups (→ data/derived/gate_*), after
  general staging finishes (orchestrator).
- **Full Python recompute** of all features from raw (→ *_py parquets), per-channel + pairs.

**Remaining (assemble when jobs done)**
- Aggregate gate window-probs → per-recording P(abnormal), P(slowing), P(focal), P(generalized).
- Feature selection: distill gate prob → our features (LASSO/GBM+SHAP, stability, dedup) → keep-list.
- Final **gated report generator**: Morgoth gate decides whether/what; our features (region+side+band+
  prevalence+persistence+stage) describe. Verbal examples.
- Re-run curves/discrimination/stage/descriptive on the Python (*_py) features; refresh gallery/PDF.
- Regional/focal localization in the v2 descriptions (needs per-channel *_py features).

## Status log (updated as I go)
- [x] A features (recording_features/asymmetry/segment_features.parquet)
- [x] B curves (growth_curves.parquet + figures/curves/*.png; delta developmental trajectory validated)
- [x] C QC (normal z centered on 0; curves physiologically sane)
- [x] D scoring (scores.parquet, topography, example_reports.md)
- [x] E discrimination (results/discrimination.md; log_delta/log_theta/TAR top, AUC~0.73-0.75 adj)
- [x] F write-up (results/RESULTS.md)
- [~] STAGING (stretch): FEASIBLE, reverse-engineered end-to-end (docs/sleep_staging.md). Raw on S3
  (matches 1:1, NORMAL downloading), model = SLEEPPSG.pth (base_patch200_200, 5-class), exact Mac/MPS
  command found, pilot reached model-load. Blocked only by env isolation (pyhealth pins pandas<2 vs
  analysis stack) → needs a dedicated venv. Clean pickup; not shipped autonomously to avoid a broken
  env + unvalidated stages overnight.
