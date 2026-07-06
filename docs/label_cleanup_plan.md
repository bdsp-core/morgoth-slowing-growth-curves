# Unified label cleanup plan (from raw reports) — 2026-07-05

Supersedes the scattered label logic in scripts 18/20/52. Produces **one unified label file for the
entire cohort** (12,379 recordings, all MGB = S0001 MGH + S0002 BWH), re-derived from the raw reports +
structured findings, with provenance. Gates everything downstream (clean-normal reference → growth
curves → report-label panels → normative-deviation strata).

## Sources (confirmed, local)
- **Raw report text** (side/region/band/qualifiers): `data/reports_raw/MGB_EEGs_And_Reports.csv`
  (1.09 GB, downloaded from Box `I0001-MGB/.../EEGs_And_Reports.csv`; **PHI, gitignored**). `SiteID`
  column carries S0001/S0002, `BDSPPatientID` matches cohort pid after stripping the site prefix + `.0`.
  Join on (pid, date) covers 99.4% of the cohort.
- **Structured findings** (class flags): `data/findings/S0001_*_findings.csv`, `data/findings/S0002_*`.
  Identical 53-col schema; `normal / abnormal / foc slowing / gen slowing` cells are
  `report|verified|annotation|combos|empty`. **Present = any non-empty cell** (fixes the old
  `.contains("report")` under-count). No structured location/band — those are text-only.

## Unified schema — `data/derived/labels_unified.csv` (one row per recording)
```
Identity     bdsp_id, site(MGH|BWH), pid, eeg_datetime, age, sex
Report link  has_report, report_note_name, n_report_chars
Class        is_normal, is_abnormal, has_focal_slow, has_gen_slow   (0/1, non-exclusive)
             group ∈ {normal, abnormal, no_report}          ← analysis split
             report_stratum ∈ {N, A0, Ag, Af}               ← normative-deviation strata
Focal        focal_band ∈ {delta,theta,mixed,unspec}
             focal_side ∈ {left,right,bilateral,unspec}
             focal_region ∈ {temporal,frontal,central,parietal,occipital,unspec}
Generalized  gen_band ∈ {delta,theta,mixed,unspec}
             gen_topography ∈ {anterior,posterior,unspec}
             gen_state ∈ {wake,sleep,unspec}
             gen_class ∈ {pathologic,physiologic,indeterminate}
Provenance   label_source ∈ {finding_flag,report_text,both}, focal_trigger, gen_trigger
```
Plus `labels_unified_evidence.jsonl` — per-recording trigger-phrase spans for audit.

**Region vocabulary is already decided (do NOT reinvent):** focal lobes
{temporal, frontal, central, parietal, occipital} with `frontotemporal→temporal`,
`frontocentral→frontal` (config/channels_regions.yaml, scripts/18); side {left,right,bilateral}
as a separate axis; generalized {anterior, posterior} = FIRDA-like frontal vs OIRDA-like posterior
(scripts/42).

## Class reconciliation
- clean-normal = `is_normal & ~is_abnormal & ~has_focal_slow & ~has_gen_slow` (contamination fix, kept).
- A **normal impression is ground-truth normal** (Brandon's rule) — overrides a stray gen-slowing flag.
- `is_*` = union of the structured finding flag and the report-text mention, with the source recorded.

## Generalized phys vs path (the open problem) — rules + 1,000 labels + classifier
Gen-slowing flag fires in 56% of findings rows — over-inclusive because it sweeps drowsy/HV/sleep
slowing. Approach: a rule-based prior + a text classifier trained on 1,000 hand-labels for the middle.
- **Pathologic cues:** slowing *of the background*; excessive/excess *for age*; disorganized / poor
  organization; encephalopath*; dysfunction; abnormally slow background; co-occurring
  seizures/GPD/LPD/LRDA/GRDA.
- **Physiologic cues:** generalized slowing scoped *only* to drowsiness/asleep/hyperventilation/
  state-dependent, **and** otherwise-normal study.
- **Labeling tool exists:** `scripts/56_build_report_labeler.py` → `results/report_labeler.html`
  (buttons N / Pathologic / Physiologic / Unsure, trigger highlights, CSV export). Repoint it at
  `data/reports_raw/` + the new stratified selection; Brandon labels ~1,000; train a text classifier
  (rule features + n-grams) → fills `gen_class`. Ultimate arbiter for analysis remains the
  stage-matched normative deviation (normative_deviation_plan.md).

## Pipeline (new `scripts/60_build_unified_labels.py`, retires 18/20/52)
1. Assemble reports + findings; join to cohort on (pid, date). No report → `group=no_report`, excluded.
2. Class reconciliation (above).
3. Rewritten per-clause extractors: band/side/region (carry v2 forward) + anterior/posterior topography
   + wake/sleep state scoping + gen phys/path cues; every field records its trigger span.
4. Emit `labels_unified.csv` + `labels_unified_evidence.jsonl`.
5. **Two summaries:**
   - **Diff vs old** (`results/label_diff.md`): recordings that changed group (normal↔abnormal),
     clean-normal count Δ, focal side flips, regions newly resolved, gen phys/path split, band changes.
   - **Coverage** (`results/label_coverage.md`): of 12,379 — % with report, % with each label resolved,
     sparse age×region×band cells flagged.
6. Downstream (gated on approval): clean-normal → refit curves → rerun report-label panels (40–46,18)
   + normative-deviation strata.

## STATUS — 2026-07-05 (built)
- Reports downloaded; `scripts/61` labeling set (1000, 20 batches); LLM-labeled via 20 subagents
  (`data/derived/gen_labels_llm.csv`: 585 path / 172 normal / 159 phys / 82 unsure); Brandon
  spot-checked the 145 hardest (disagreements + unsure) → **15/15 agreement**, labels validated.
- `scripts/62` classifier: TF-IDF+logreg, 5-fold CV **AUROC 0.960, macro-F1 0.883** (beats rule-cue
  0.937/0.857); interpretable n-grams; scores the whole universe. `models/gen_classifier.joblib`.
- `scripts/60` **unified labels built** → `data/derived/labels_unified.parquet` + `results/labels_unified.csv`
  (+ evidence jsonl), with `results/label_coverage.md` and `results/label_diff.md`.

Key outcomes (whole cohort 12,379): clean-normal **2517 → 5073** (≈doubled; the norms reference);
generalized slowing split **physiologic 5297 / pathologic 4128** (56% was physiologic over-flagging);
truncated-`abnormal` impression artifact caught (trust structured flags over corrupted 'normal ... due to').
Focal side/region/band unchanged (same validated v2 extractors). 792 (6%) have no matching report → excluded.

## Remaining
1. Wire `clean_normal`/labels_unified into the reference build → refit growth curves → rerun
   one-vs-normal + normative-deviation strata (N/A0/Ag/Af) + report-label panels (40–46,18).
2. Recover some of the 792 no_report via fuzzy date match (optional).
3. Focal `unsure`/no-gen-slowing handling already correct (gen_class='none' when no gen slowing).
```
```
