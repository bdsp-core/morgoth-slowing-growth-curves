# Paper outline

**Working title:** *Normative growth curves for EEG slowing across the lifespan and sleep–wake states:
deviation-from-normal scoring that recapitulates expert report language*

**Target:** clinical neurophysiology / digital-medicine venue (e.g., Clinical Neurophysiology, Brain
Communications, npj Digital Medicine). Companion open-source package + published label set.

## Abstract (structured)
- **Background:** clinicians judge EEG slowing against age/state-dependent norms that rest on small,
  historical, largely qualitative studies; existing quantitative lifespan EEG work characterizes
  *normal* values, not *deviation from normal*, and rarely stage-specific.
- **Methods:** 12,379 routine clinical EEGs (~12k patients, infancy→>90 yr); reproducible Python
  qEEG features (band powers, DAR/TAR, homologous asymmetry); deep-learning sleep staging; age×sex×
  stage percentile "growth curves"; deviation scoring (z, burden, prevalence, persistence,
  stage-accentuation); focal/generalized via an expert-calibrated foundation model (Morgoth) gate;
  automatic report-sentence generation; validation against the free-text clinical reports.
- **Results:** developmental/aging trajectories reproduced; stage-dependence quantified
  (δ rises W<N2<N3); discriminative features identified (δ/θ power, TAR, homologous asymmetry);
  generated descriptions agree with expert reports (region 0.91, side 0.78, band 0.74); deviation
  features track the expert-calibrated detector (r≈0.7).
- **Conclusions:** first large-scale, lifespan- and stage-resolved, deviation-from-normal EEG-slowing
  norms that produce validated, report-ready descriptions; open package + labels.

## 1. Introduction
- Clinical problem: slowing (focal vs generalized) is a core EEG abnormality; interpretation is
  age- and state-dependent and largely qualitative/expert-dependent.
- **Literature review** (see docs/literature_review.md → this section): (a) lifespan normative qEEG
  (normal values), (b) classic small-sample age-norm references clinicians rely on, (c) qEEG
  abnormality quantification (van Putten et al., DAR/TAR, ICU qEEG), (d) automated EEG
  interpretation/report generation. **Gap:** none combine large N + lifespan + sleep-stage-specific +
  *deviation-from-normal* + validated expert-style description.
- Contributions (bulleted): reproducible lifespan×sex×stage norms; deviation scoring; Morgoth-gated
  focal/generalized; report-sentence generation validated vs reports; open package + published labels.

## 2. Methods
2.1 **Cohort & data** — routine clinical EEGs (MGB sites S0001/S0002), inclusion, demographics
   (Table 1), labels (report-derived normal/abnormal, focal/generalized; provenance to source notes).
2.2 **Reproducible feature extraction** — referential→bipolar, multitaper PSD, band/ratio/asymmetry,
   per-channel + homologous pairs; validation vs prior features (r 0.89–0.95); calibration (delta
   1–4 Hz).
2.3 **Sleep staging** — morgoth2 stager; validation of stage distributions; segment→stage mapping.
2.4 **Normative growth curves** — age×sex (×stage) percentile curves (kernel-weighted quantiles);
   subject-level validation; coverage & min-n guards.
2.5 **Deviation scoring** — segment z vs age/sex/stage norm; prevalence, conditional severity,
   burden, persistence (runs/episodes), stage-accentuation, homologous asymmetry; patient-level
   empirical-percentile z.
2.6 **Topography & the Morgoth gate** — 3-tier gate (normal→slowing→focal/generalized); features add
   region/side/band/quantitative detail.
2.7 **Report generation** — table→sentence templating (ACNS-style prevalence, severity words).
2.8 **Validation & statistics** — vs Morgoth (calibration to experts); vs report flags (AUC); vs
   report text (region/side/band agreement); discrimination AUCs; feature selection.

## 3. Results
3.1 Cohort & coverage (Table 1; age×sex×stage coverage matrix; N3/adult gap).
3.2 Growth curves reproduce development & aging (Fig: δ decline; validation z≈0 in normals).
3.3 Sleep-stage-specific norms (Fig: δ W<N1<N2<N3; per-region).
3.4 Which features discriminate (Table/Fig: adjusted AUCs; δ/θ power, TAR, homologous asymmetry;
   feature selection → parsimonious set).
3.5 Deviation features vs expert-calibrated Morgoth (r≈0.7; distillation R²).
3.6 Agreement with clinical reports (Table: region 0.91 / side 0.78 / band 0.74; report-flag AUCs).
3.7 Example generated reports (Box: focal & generalized exemplars with stage-dependence).

## 4. Discussion
- What's new vs the literature (deviation-from-normal; lifespan+stage; scale; validated description).
- Clinical implications: objective, reproducible second read; report drafting; where features agree
  vs where morphology (still) matters (band was the weak axis; morphology-feature roadmap).
- Relationship to Morgoth (detection vs description; gate + describe design).

## 5. Limitations
- Absolute rel-power calibration; band determination still hardest axis; morphology not yet modeled
  (docs/morphology_features.md roadmap); N3/adult & abnormal-with-sleep coverage; single health
  system; report text as imperfect ground truth; routine (short) EEG for sleep.

## 6. Conclusion
- Lifespan, stage-resolved, deviation-based EEG-slowing norms with validated report generation; open
  package + labels for reproducibility and extension.

## Figures / Tables (planned)
- **T1** cohort characteristics; **T2** literature comparison (from lit review); **T3** feature
  discrimination AUCs; **T4** agreement with reports.
- **F1** developmental δ growth curve + overlays; **F2** stage-specific curves; **F3** discrimination
  bar; **F4** report-agreement / example sentences; **F5** pipeline schematic (gate + describe).

## Data/code availability
GitHub `bdsp-core/morgoth-slowing-growth-curves`; published per-recording labels (Morgoth probs,
report-derived + report-text-extracted band/side/region) with provenance to source notes; growth-curve
tables. Raw EEG & report text via BDSP credentialed access.
