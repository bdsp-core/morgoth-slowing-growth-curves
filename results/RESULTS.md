# Results

EEG slowing normative growth curves + Morgoth-gated report, on 12,379 recordings
(normal 4,916 / focal_slow 2,067 / general_slow 5,396). Everything reproducible from raw EEG in
Python. Pipeline: `03 features → 04 curves → 06 discrimination → 09 map-stages → 10 stage-curves →
11 descriptive → 13 recompute(py) → 14 gate → 15 feature-select → 16 gated report`.

## 0. Reproducible features (Python, from raw)
Original Growth_curves features were precomputed (MATLAB, code unavailable). `features/extract.py`
recomputes them from raw EEG (referential→18 bipolar→0.5 Hz HP + notch→15-s multitaper→31 features),
**validated vs JJ: per-band log-power r = 0.89–0.95** (docs/feature_extraction.md). All results below use
the Python-recomputed features (JJ's kept as `*_jj`). Caveat: absolute relative-power runs high (a
low-edge/total-band calibration TODO); z-based results are scale-invariant and unaffected.

## 1. Cohort — [Table 1](../README.md#table-1--cohort-characteristics)
Sex ~50/50 across groups; controls skew ~20 yr younger → **all scoring is age & sex conditioned.**

## 2. Growth curves validate against development
Absolute delta falls steeply through childhood to a plateau by ~30 (textbook); normal-referenced z is
centered on 0 for normals. `figures/curves/` (8 features × 5 regions).

## 3. Sleep-stage-specific norms (v2)
Cohort staged with morgoth2 `ss_hm_1.pth` (MPS; validated stage mix). Normal median relative delta
rises with sleep depth: **W≈N1 < N2 < N3** (REM intermediate) — so delta abnormal in wake is normal in
N2/N3, and every segment is scored against **its own stage's** normal curve (normal prevalence ≈ 0).
`figures/stage_curves/`. Coverage caveat (docs/coverage_by_stage.md): N3 sparse in adults; expandable
via long labeled EEGs in `bdsp-opendata-repository`.

## 4. Which features discriminate (age/sex-adjusted AUC)
log_delta / log_theta / **TAR (θ/α)** lead (AUC ~0.67–0.75). Feature selection
(results/feature_selection.md, L1 + RF + stability): **TAR dominates**, then log_theta/log_delta →
compact keep-list. Per-channel homologous asymmetry (`|asym_ch_T3-T5_delta|`) is a **top focal
discriminator** (AUC ~0.70) — validating the per-channel/homologous-pair features.

## 5. Morgoth detection gate (the "whether/what")
All Morgoth heads run on all 12,379 (window + EEG-level). Per-EEG probabilities →
`results/morgoth_slowing_probabilities.csv` (p_abnormal, p_focal_slowing, p_generalized_slowing;
keyed by `file_name = sub-<BDSPPatientID>_<StartTime>`; see docs/morgoth_gate_outputs.md). Sanity vs
labels (median): p_abnormal normal **0.10** vs focal/general **0.98–0.996**; p_focal highest in focal,
p_generalized highest in generalized. Slowing gate at P≥0.30 (Youden J=0.75): **gates in 79% focal /
86% generalized / 8.9% normal.**

## 6. Final gated report (the deliverable)
`scripts/16_gated_report.py` (results/example_reports_final.md): Morgoth gate decides whether to
report and focal-vs-generalized; our normative features add **region+side, band, prevalence,
persistence, and stage-dependence**. Examples:
> *Frequent mild left temporal delta slowing — present in 48% of segments; peak 2.1 SD above
> age/stage norms; longest run 3.8 min over 4 episodes.*
> *Frequent mild generalized delta slowing — present in 31%…; present only during sleep; accentuated
> in N1.*

## 7. Limitations / next
- **Feature↔Morgoth gaps:** some Morgoth-confident cases show flat spectral features ("peak ~0 SD") —
  Morgoth detects patterns our current features miss and/or the rel-power calibration; the report then
  reads weak. Next: calibrate rel-power, add morphology-aware features, distill Morgoth prob → features
  (scripts/15 with gate target).
- **N3/adult coverage** and **stage-specific abnormal power** are thin — expand from the repository
  (§coverage doc).
- **Regional stage-specific curves** (focal localization within stage) — recording-level localization
  is wired; per-region×stage curves are the next refinement.
