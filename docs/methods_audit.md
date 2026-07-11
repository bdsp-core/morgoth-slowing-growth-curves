# Methods audit — what is verified, what is assumed, what is broken

Written 2026-07-09 after discovering that the EEG↔report pairing was wrong. Every claim below is tagged:

- **[VERIFIED]** — checked against the data, with the check named.
- **[ASSUMED]** — relied upon but never checked. These are where the next bug lives.
- **[BROKEN]** / **[FIXED]** — known defect, and its current status.

---

## 1. Data sources

| # | Source | Grain | Used for |
|---|---|---|---|
| 1 | `s3:bdsp-opendata-repository/EEG/bids/.../*.edf` | one file per EEG session | raw signal |
| 2 | `EEGs_And_Reports.csv` (scratchpad only, never committed) | one row per EEG, **report joined at patient level** | free-text report, severity/frequency adjectives |
| 3 | `data/findings/S000*_EEG__reports_findings.csv` | one row per EEG (`StartTime(EEG)`) | diagnosis flags: `normal`, `abnormal`, `foc slowing`, `gen slowing` |
| 4 | `metadata/cohort_metadata.csv` | 12,379 recordings | our recording table |
| 5 | `data/derived/fractional_age.parquet` | one row per patient | fractional age at EEG (OMOP) |

---

## 2. Recording identity — a real weakness

`bdsp_id = SiteID + BDSPPatientID`. This identifies a **patient at a site, not a recording.**

- **[VERIFIED]** `cohort_metadata.csv`: 12,379 rows, **12,027 unique `bdsp_id`**, 12,024 unique patients.
  352 patients contributed ≥2 recordings.
- **[BROKEN]** `channel_stage_features.parquet` and `segment_features.parquet` are keyed on `bdsp_id` **with no
  date**, so those 352 patients' recordings are collapsed into one row. `scripts/82_build_uniform_v2.py`
  explicitly strips the date (`bdsp_id.str.split("_").str[0]`) to make the label join succeed.
- **[BROKEN]** Nearly every analysis calls `labels_unified.drop_duplicates("bdsp_id")`, which silently keeps
  the *first* recording's labels and discards the second's.
- **[FIXED 2026-07-09, MBW decision]** Those patients are **dropped**. `scripts/99_exclude_multirecording_patients.py`
  writes `data/derived/excluded_bdsp_ids.parquet`: **350 patients, 702 recordings (5.67%)**. Downstream
  analyses filter it out. The excluded patients skew *less* abnormal than those retained (33.1% vs 48.8%),
  so the exclusion does not enrich for pathology. Stated in Methods §2.1.

---

## 3. EEG ↔ report matching — this was wrong, and is now only *mostly* right

**What the file actually is.** `EEGs_And_Reports.csv` is an EEG × report cross-join performed **at the patient
level** upstream, before we ever received it.

- **[VERIFIED]** 217,227 distinct EEGs; each carries **at most one** `OrderID` (max = 1).
- **[VERIFIED]** Only **65,233 distinct reports**. **35.9% of `OrderID`s are stamped onto more than one EEG**
  (mean 2.89 EEGs per report, **max 170**).
- **[VERIFIED]** **53.4%** of `(patient, date)` rows carry report text **byte-identical** (md5) to another row
  for the same patient. Median report length 2,433 characters — this is not clinical copy-forward.

**How it was caught.** The reader's *own* severity adjective agreed across a patient's consecutive studies
**97% of the time (ρ = 0.95, n = 5,226 pairs)**. No clinical rating is that reliable. The text was xeroxed.

**What the original bug was, and what the "fix" actually fixed.**

1. *Original:* joined report to EEG on **patient only** → an arbitrary report per patient.
2. *First fix:* joined on **`(bdsp_id, date)`** → selects the row bearing this recording's own StartTime.
   This is necessary but **not sufficient**: the row is right, the *text inside it* may describe a different
   study of that patient.
3. *Current repair* (`scripts/88_report_pairing_audit.py`): a report belongs to the EEG **nearest it in time**.
   `clean_pair` = this EEG's `OrderID` is claimed by no other EEG, **or** this EEG is that report's
   nearest-in-time owner.
   - **[VERIFIED]** 10,255 / 12,379 recordings (**82.8%**) are cleanly paired.
   - **[VERIFIED]** 2,124 (**17.2%**) carry a **borrowed** report, or none at all.
   - Written to `data/derived/report_pairing.parquet` (`clean_pair` column). **Filter on it.**

**[ASSUMED] — the honest caveat.** The nearest-in-time rule is a **heuristic, not a guarantee.** For reports
owned by exactly one EEG, `|time_diff|` has median **14.2 h** and p90 **203 h** — this is an *order-to-study*
offset, and it is loose. A definitive mapping requires a true report↔study key from BDSP, which we do not
have. Until then, `clean_pair` should be read as "probably the right report," not "certainly."

---

## 4. Labels — partially contaminated, but detection survives

- **[VERIFIED]** Diagnosis flags come from source #3, keyed on `StartTime(EEG)`, and are **largely per-EEG**:
  only **34.5%** of multi-study patients have identical flag-vectors across their studies (a pure broadcast
  would be ~100%).
- **[VERIFIED]** But source #3 is *also* an EEG × report join: `DeidentifiedName(Reports)` is reused across up
  to **17** EEG dates (25.5% of reports).
- **[VERIFIED — flag-level test, 2026-07-09]** The flags **do ride the shared report**. EEG pairs that share a
  report identifier carry an **identical flag vector 95.2%** of the time (n = 66,817 pairs); same-patient pairs
  carrying *different* reports agree only **48.1%** (n = 196,710). If the flags had been derived per-EEG, the
  two rates would match. They do not. So where a report is shared, the flags on the non-owner EEG are the
  **owner's** flags. Contamination is therefore present in the labels, not only in the free text.
  *(Note: dropping the 350 multi-recording patients does NOT fix this. Our cohort now holds ≤1 recording per
  patient, but the report attached to that recording may still have been written about a different study of
  the same patient — a study that is not in our cohort at all.)*
- **[BROKEN → BOUNDED]** `scripts/60_build_unified_labels.py:123` defines
  `is_abnormal = (abn_flag | text_abnormal)` and `has_focal_slow = (foc_flag | foc_text)`, so contaminated
  **text** leaks into the labels through the `text_*` terms.
- **[VERIFIED] Sensitivity test** (`results/detection_pairing_sensitivity.md`): re-running the primary
  detection analysis on cleanly-paired recordings only moves every AUROC **inside its bootstrap CI**
  (W 0.848→0.847; N1 0.875→0.872; N2 0.791→0.787; N3 0.758→0.749; REM 0.825→0.830).

  *Why detection survives but severity does not:* a borrowed report belongs to the **same patient**, and
  abnormal-vs-normal status is stable across that patient's studies, so the **binary** label usually survives
  the swap. **Severity varies study to study, so it does not.**

---

## 5. Features — one pipeline, verified

- **[FIXED]** Originally two pipelines (cohort = precomputed MATLAB `.mat`; expansion = `extract.py`). Only
  `rel_delta` had been calibrated across them; the **alpha band differed**, so `TAR`/`DAR` were never
  cross-comparable. Both cohorts have since been **recomputed through `extract.py`** (27,022 recordings).
- **[VERIFIED]** Pipeline control (`scripts/78_pipeline_control.py`) ran `extract.py` on the *same* routine
  EDFs as their `.mat`: `rel_delta` bias −0.016; `rel_alpha` −0.049; `DAR` +0.29; `TAR` −0.25.
- **[VERIFIED]** Channels identical across sources (C3/C4 central montage).
- **[FIXED]** `TAR` was read from `.mat` index 17 (θ/β). It is index **16** (θ/α), confirmed against the
  file's own `feature_names`.
- **[VERIFIED]** Band edges (`extract.py`): δ 1–4, θ 4–8, α 8–13, β 13–30, γ 30–45, total 0.5–45 Hz (theta widened 4–7→4–8 to close the 7–8 Hz gap).
  **Note the 7–8 Hz gap** — deliberate, but it means "θ" excludes 7–8 Hz.

---

## 6. Sleep stages

- **[VERIFIED]** Canonical mapping (`scripts/26:167`): stager emits 5-s windows; feature segment *i* spans
  samples `[2800i, 2800i+3000)` @200 Hz → centre `14i+7.5` s → window `int((14i+7.5)/5)`.
  `pred_class` 0–4 → W/N1/N2/N3/REM.
- **[FIXED]** Stages existed only for the 4,990 **normal** recordings. `scripts/87_build_abnormal_stages.py`
  now builds them for the abnormals (313,446 segment-stages over 7,408 recordings) so both groups are staged
  **by the same code**.
- **[VERIFIED]** Abnormal stage mix: W 44.5%, N1 16.8%, N2 20.6%, N3 11.9%, REM 6.2%. Because abnormals are
  only ~44% wake, **scoring over all segments confounds slowing with how much the patient slept.** All scoring
  is now restricted to W/N1.

---

## 7. Normative curves

- **[VERIFIED]** Reference = **union** of both report-normal cohorts (conservative; costs nothing in
  detection — `results/union_normal_detection.md`).
- **[VERIFIED]** GAMLSS/LMS, **BCT** with **age-varying skewness** (`nu ~ cs(t, df=3)`); constant skewness was
  the true cause of the infant-age median bias (df 3→12 changed nothing).
- **[VERIFIED]** Sex **pooled**: ΔAUROC ≤ 0.002 across 50 settings (`scripts/74_sex_ablation_discrim.py`).
- Age transform `log10(age + 1/12)`.

---

## 8. Vigilance matching

- **[VERIFIED]** Routine EEGs are recorded under active alerting, so **W/N1 are genuine alert states**;
  overnight wake is unconstrained and drowsy (`rel_alpha` 0.064 overnight vs 0.238 routine).
- Primary detection therefore uses **routine W/N1** against a **routine** normal reference. Using the
  overnight reference degrades N1 from 0.875 → 0.791 — the effect is large and is itself a finding.

---

## 9. Detection design

- Positives = routine abnormals (n = 3,883). Negatives = **held-out 30%** of routine clean-normals (n = 1,451).
- The reference norm is built from the **other 70%**, split on `bdsp_id` → **[VERIFIED]** no patient leakage
  between reference and negatives.
- **[ASSUMED]** Feature/stage selection ("best feature per stage") is reported **without** an outer split.
  The per-stage winner is chosen on the same data the AUROC is reported on. With 6 features × 5 stages this
  is a mild optimism; it should be nested-CV'd before publication.

---

## 10. Severity and prevalence — we cannot currently claim this

Four real defects were found and fixed: the max-statistic (`peak_z`, max 19.4 = artifact) → robust p90;
a negation-blind, table-order adjective extractor → clause-scoped, negation-aware, nearest-to-"slow";
whole-head scoring of focal cases → max-deviation region; all-segment scoring → W/N1 only. Plus clean-pair
filtering.

**Result after all fixes: severity ρ = 0.050 (p = 0.17, n = 753). Null.**

- **[VERIFIED]** `scripts/89_severity_axis_sweep.py`: **168 combinations** (7 features × 4 statistics ×
  {raw, z} × {generalized, focal, all}). **Largest |ρ| anywhere = 0.179**, which fails Bonferroni
  (0.05/168 = 3.0e-4; best p = 6.8e-4), and the top hit has the **wrong sign**.
- **[VERIFIED]** Raw ≈ z (0.159 vs 0.179 generalized). So this is **not** an age-normalization artifact.
- **[VERIFIED]** Prevalence vs reported frequency: ρ = 0.077 (p = 3.3e-6, n = 3,626). Statistically
  significant, clinically negligible.
- **[RETRACTED]** I hypothesised that the reader grades diffuse slowing by **posterior dominant rhythm
  frequency**, which we never measure. **MBW: this is wrong.** Grading the PDR (present/absent, and if present
  at what frequency) and grading slowing (present/absent, focal/generalized, which frequencies) are **separate
  tasks, reported separately** in a clinical EEG report. PDR is out of scope for this paper. A regex extraction
  of PDR Hz from report text was in any case invalid (non-monotonic; it captured slowing and photic-driving
  frequencies). The remaining explanation for the null is the one now measured: **the adjective is attached to a
  judgement of low reliability** (expert Fleiss κ 0.373/0.450; within-rater κ 0.563/0.642 — see
  `results/occasion_human_ceiling.md`).

**What may be claimed today:** we detect pathological slowing (AUROC 0.85–0.88) and we show a monotone
dose-response across report strata (z: −0.11 → +0.43 → +1.49). **What may not be claimed:** that we reproduce
the clinician's *severity grade*. Whether that grade is even reliable is unknown, and unknowable without the
inter-rater ceiling (MOE study, `docs/validation_plan.md` V2).

---

## 11. Open defects, in priority order

1. **Report↔EEG pairing is heuristic — and nearest-in-time is the best available.** (MBW: no true report↔study
   key exists to be had.) Filter `clean_pair`; state the heuristic and its median |Δt| in Methods.
2. ~~`bdsp_id` is not a recording key.~~ **Resolved** by dropping the 350 affected patients (scripts/99).
3. **`findings/*.csv` is itself an EEG×report join** and was never audited for broadcast at the flag level.
4. **Feature/stage selection is not nested.** Report a nested-CV AUROC.
5. **Severity is null** and the human ceiling is unmeasured (V2/MOE).
6. ~~PDR is never measured from the signal.~~ **Withdrawn** — PDR grading and slowing grading are separate,
   separately-reported clinical tasks. PDR is out of scope, and must not be used to infer slowing.

---

## 12. Environment notes (Phase A, local staging)

Running the original stager (`ss_hm_1.pth`) locally required three changes, all recorded here because they
affect reproducibility:

1. **`np.trapz` shim in `features/extract.py`.** numpy ≥ 2 removed `np.trapz`. Band power is a trapezoid
   integral of the PSD; `np.trapz = np.trapezoid` keeps every caller and every prior result bit-identical.
   Without it, *all* feature extraction fails — silently caught per-recording in some scripts.
2. **`timm` pinned to 0.9.16.** `morgoth2/utils.py` imports `timm.optim.nadam.Nadam`, removed in timm 1.0.
3. **`pyhealth` shimmed** (scratchpad `shims/pyhealth/metrics.py`). It does not build on Python 3.14 and its
   metric functions are never called on the `--predict` path. The shim raises if one ever is.

`ss_hm_1.pth` (70,116,218 B) was recovered from
`box:Brandon - DeID/0_People/ChenXiSun/ChenXiSun/Morgoth2/Models/SLEEP_staging/`.
It is **not** `SLEEPPSG.pth` (70,118,138 B) in the opendata bucket — different files. The fleet bucket
`s3://bdsp-brandon-morgoth-slowing` that formerly held it no longer exists.
