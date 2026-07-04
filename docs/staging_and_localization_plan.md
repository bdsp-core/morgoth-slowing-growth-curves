# Plan: fix the two oversights (stage coverage + region localization)

Both are **our own data-collection gaps**, not external limits — we control the ingestion, so we fix
them by collecting the right data.

## Oversight #1 — sleep staging was only run on the normative controls
**Symptom:** the original cohort's staged subset is 98.5% normal (74 focal, 0 generalized), so a
stage-stratified abnormal-vs-normal AUROC can't be computed on it.
**Root cause:** the original pipeline staged only the normal recordings used to build the norms; the
abnormal recordings (from FOCALSLOWING/GENSLOWING) were never staged.
**Fix — stage the abnormals we already have.** Their raw signal is on S3:
`morgoth1/.../FOCALSLOWING/segments_raw/` (2,067) + `GENSLOWING/segments_raw/` (5,396) — 10-min,
200 Hz, 20-ch `.mat` clips, already in the stager's input format. Steps:
1. `scripts/36_stage_original_abnormals.py`: pull each `segments_raw/*.mat`, run `ss_hm_1`, save
   per-window stages → `data/derived/original_abnormal_stages/<rid>.csv` (resumable via markers).
   ~7.5k clips × ~2–4 s each ≈ a few GPU-hours on the pilot box.
3. Map stages → the existing per-segment features (`segment_features.parquet`) for those recordings →
   now the full cohort has staged focal + gen.
4. Re-run `scripts/34` → the stage-stratified AUROC (Wake/N1/N2/N3/REM) becomes real, thousands per
   label. Fleet later stages every new recording too.
**Target:** ≥ several hundred staged focal AND gen across age bands → powered stage curves.

## Oversight #2 — region localization only evaluable/decent for temporal
**Symptom:** region "accuracy" 0.92 is a majority-class artifact (temporal ~92%); our system predicts
temporal/bilateral by default; frontal/parietal/occipital F1 ≈ 0; left/right F1 0.35/0.24.
**Two root causes, two fixes:**
- **(a) Evaluation set too thin off-temporal.** Deliberately assemble a **region-stratified eval set**:
  from `report_extracted_labels.csv` we have abnormals per region (frontal 698, central 266, occipital
  68, parietal 66). Ingest/stage a balanced sample across regions (target ~60–100 each of frontal,
  central, parietal, occipital + temporal) so every region has enough n to score.
- **(b) Our region predictor defaults to temporal.** Replace the text-default with a **data-driven
  region call**: assign the predicted region = the region with the largest age/sex-adjusted slowing
  deviation (we already compute per-region deviations + homologous L/R asymmetry). Re-evaluate with the
  per-region confusion matrix. This turns localization from "defaults to temporal" into an actual
  topographic prediction we can score.
**Target:** per-region recall/F1 reported on ≥ ~60 recordings per region; L/R from the asymmetry sign.

## Sequencing
1. (now) Launch `scripts/36` to stage the original abnormals (fixes #1 at scale).  ← highest value
2. Improve the region predictor (max-deviation region) + region-stratified eval (fixes #2).
3. Re-run stage-stratified AUROC + region confusion on the newly-staged/located data → dashboards.
4. Fleet run generalizes both to the full wave.
