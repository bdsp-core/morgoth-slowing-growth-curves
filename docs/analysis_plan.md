# Statistical Analysis Plan — Lifespan × sleep-stage normative growth curves for EEG slowing

**Status:** DRAFT for colleague review, to be finalized *before* the fleet re-run.
**Version:** 1.0 (2026-07-10). **Owner:** MBW.
**Companion docs:** `docs/DATA_INVENTORY.md` (data tables), `docs/claims_table.md` (clause
governance), `docs/description_architecture.md` (descriptor definitions).

> **How to review this document.** It is written so that following it end-to-end produces every
> number, figure, and table in the paper from a *single* canonical dataset, with no ambiguity about
> which data a given analysis used. If any analysis below cannot name its exact input table, grain,
> coverage, and cohort filter, that is a defect — flag it. The four things that repeatedly bit us are
> called out inline as **⚠ PITFALL** with the rule that prevents them.

---

## 1. Background and rationale

Clinical EEG reports grade "slowing" (excess low-frequency power / paucity of faster activity) with
poor reliability — expert agreement for slowing is the *worst* of the major EEG findings (Fleiss
κ ≈ 0.37 focal, 0.45 generalized; within-rater 0.56–0.64; band-word κ 0.09–0.38). Slowing is also
strongly age- and vigilance-dependent: physiologic drowsiness and sleep produce exactly the spectral
changes that define pathologic slowing awake. No widely used tool separates "abnormal for this
person's age and current brain state" from "normal sleep."

We build **lifespan × sleep-stage normative growth curves** for quantitative EEG slowing features,
conditioned on age, sleep stage, and scalp region, and a **two-stage system** on top:

- **GATE (Morgoth foundation model): whether and what.** Presence of pathologic slowing; focal vs
  generalized. This is the only module allowed to make the categorical call.
- **DESCRIBE (normative deviation field): how much, where, which band, how prevalent, how persistent,
  in which stage.** A measurement layer that never makes the categorical call.

**Design principle (circularity guard).** Two named objects with a hard rule:
- `z` / `S` — the **unsupervised** normative deviation and the amount score. Because they are fit only
  to clinician-labeled normals and never see the report label of abnormal cases, they may support the
  claim *"we measure slowing readers under-report."*
- **Morgoth gate** and any **supervised** score — may **never** support that claim (they are trained
  toward the report and would be circular).

Every reportable sentence clause is tagged ALLOWED / PROVISIONAL / FORBIDDEN in `docs/claims_table.md`;
this SAP inherits that governance.

---

## 2. Objectives and pre-registered hypotheses

**Primary aim.** Establish normative growth curves for EEG slowing features across the lifespan and
sleep stages, and validate a gate-then-describe system that (a) detects pathologic slowing and (b)
produces a governed quantitative description, against clinical reports and against the human
inter-rater ceiling.

**Secondary aims.**
- S1. Detection AUROC for abnormal vs clean-normal, whole-recording, vigilance-matched.
- S2. Focal vs generalized discrimination and, within each, localization (side / lobe; anterior–posterior
  predominance for generalized).
- S3. Reliability of each quantitative descriptor (amount, prevalence, band, persistence).
- S4. Convergent validity vs report band/side/topography; divergent behavior where reports are known
  unreliable (the "we see what readers miss" analysis — **unsupervised path only**).
- S5. Position system performance relative to the human ceiling (κ) — the honest bar.

**Pre-registered predictions** (state direction *and* the outcome that would falsify).
| # | Prediction | Falsified if |
|---|---|---|
| P1 | Detection AUROC ≥ 0.80 whole-recording, vigilance-matched | < 0.75 |
| P2 | Sex can be pooled in the norms | ΔAUROC from adding sex > 0.01 |
| P3 | Amount score is reliable | split-half ICC < 0.8 |
| P4 | Prevalence descriptor is reliable | ICC < 0.8 |
| P5 | Band call is *weak* (report only as low-confidence) | rel-power band-match > 0.8 (then promote it) |
| P6 | Readers under-report **sleep** slowing (unsupervised path) | our sleep-slowing rate ≤ report rate |

*(Predictions we already know can fail are kept in — P5 is expected to be confirmed "weak," and a prior
focal-score configuration failed against clean-normal-only negatives; both are reported as-is. We do not
delete failed experiments from the record, but the manuscript need not narrate design mistakes.)*

---

## 3. Study design

### 3.1 Data sources and cohorts
Two sources, one harmonized table, provenance tracked in a `src` column (never inferred from filename):

| Cohort (`src`) | Provenance | Role | Reports? |
|---|---|---|---|
| `cohort` | Growth_curves case series | Rich normal + abnormal across lifespan; has clinical reports | yes |
| `expansion` | Additional clean-normal + abnormal recordings | Enlarge normal reference + abnormal tail | partial |

Target scale: ≈27,000 recordings, ages 0–119 (median ~51), ≈20,900 clean-normal / ≈5,600 abnormal.
De-identification and PHI handling per §11.

### 3.2 Inclusion / exclusion (recording level)
- **Include:** scalp EEG, ≥ a minimum analyzable duration (define, e.g. ≥ 5 min of usable segments),
  standard 10–20 montage reconstructible to the double-banana bipolar set.
- **Exclude:** recordings that are *predominantly* burst-suppression or electrocerebral
  inactivity/disconnection → routed to a dedicated detector, **not** this slowing pipeline (their
  low-frequency power is not "slowing" in the intended sense).
- **Exclude** recordings with < a minimum fraction of usable (non-artifact) segments (define, e.g.
  < 20%).

### 3.3 Unit of analysis and the report-broadcast dedup rule
The clinical unit is the **recording** (`bdsp_id`); the analytic unit for description is the
**segment**. Patients may have multiple recordings.

**⚠ PITFALL 1 — report broadcast.** A single report can be joined onto up to ~170 EEGs of the same
patient by a naive report↔EEG join, contaminating labels. **Rule:** use the nearest-in-time
report per recording and carry a `clean_pair` flag; all label-dependent analyses filter to
`clean_pair`. Report the number of recordings dropped by this filter.

### 3.4 Reference ("normal") definition
`clean_normal` = report explicitly normal **and** not carrying any abnormal finding flags. The
normative model is fit on `clean_normal` recordings only. Abnormal cases never enter the fit.

### 3.5 Label derivation and contamination guards
From report text (read from the PHI-safe scratchpad extract, never committed):
- `is_abnormal`, `has_focal_slow`, `has_gen_slow`; focal `side`/`region`/`band`; generalized
  `band`/`topography` (anterior / posterior / unspecified) / `state`; `gen_class`.
- **⚠ PITFALL 2 — flag-level contamination.** Labels are extracted at the *finding* level with negation
  handling; a report mentioning "no focal slowing" must not set `has_focal_slow`. Severity adjectives
  (mild/moderate/marked) are **not** treated as quantitative (they are null across combinations) and are
  FORBIDDEN as an output.

---

## 4. Signal processing and feature extraction (the canonical pipeline)

One extractor (`src/morgoth_slowing/features/extract.py`), one parameterization, applied identically to
every recording in both cohorts and over the **whole recording**.

### 4.1 Preprocessing
- Reference montage → longitudinal bipolar **double-banana** (18 channels: Fp1-F7 … Cz-Pz).
- Resample to **200 Hz**. Band-limit 0.5–45 Hz. Line-noise handled at feature time (multitaper).

### 4.2 Segmentation
- **Segment = 15 s = 3000 samples @ 200 Hz; step = 14 s (2800 samples, 1 s overlap).** *Not 10 s.*
- Segments are indexed `0..K-1` over the **entire** recording (K up to ~11,000 for multi-hour cEEG).

**⚠ PITFALL 3 — coverage.** The legacy description table used only the first 600 s (42 segments). The
intended use is EEG of *any* length. **Rule:** every per-segment feature, stage, artifact flag, and gate
output is computed over the **whole recording**; "first-600 s" is never a coverage default anywhere.

### 4.3 Artifact detection — flag, do not strip
Per segment, `artifact.usable_mask` computes a **flag** (and reason: flat/high-amplitude/etc.), including
the flat-segment std guard (`FLAT_STD_UV = 0.5`) that catches zero-power segments the p2p check missed.

**⚠ PITFALL 4 — silent stripping.** Previously, flat/artifact segments were *removed* from the table, so
downstream could not see what was dropped or why. **Rule:** artifact segments are **retained with an
`artifact_flag` and `artifact_reason`**; analyses filter on the flag. The fraction flagged is reported
per recording and in Table 1.

### 4.4 Sleep staging
- Per-segment stage in {W, N1, N2, N3, REM} from the Morgoth sleep stager (`ss_hm_1.pth`), aligned to
  the 15 s segment grid by feature-match (never cross-correlation — a prior silent misalignment inflated
  results until fixed).
- Staged over the whole recording. Stage is a first-class key, because norms are stage-conditioned.

### 4.5 Spectral features and bands
Multitaper PSD per segment per channel; band powers:
| Band | Hz |
|---|---|
| delta | 1–4 |
| theta | 4–7 |
| alpha | 8–13 |
| beta | 13–30 |
| gamma | 30–45 |
| total | 0.5–45 |

**Band-edge fix:** the historical 7–8 Hz gap between theta and alpha is being re-extracted; the final
run uses the corrected contiguous edges (result of `scripts/109*`), so theta/alpha are not artificially
separated. Features per (segment, channel/region): `log_{band}`, `rel_{band}` (delta/theta/alpha), `DAR`
(δ/α), `TAR` (θ/α), `DTR` (δ/θ), `low_freq_rel`.

### 4.6 Spatial units
- **18 bipolar channels** (for lateralization / lobe localization), and
- **6 region aggregates**: whole_head, L/R_temporal, L/R_parasagittal, midline.
Region is a key; channel-grain is retained for the abnormal/focal recordings that need it (see §5 scale).

### 4.7 Morgoth gate — per segment (NEW)
The gate currently exists only per recording (`gate_probs`, cohort only). **This SAP requires the fleet
to persist per-segment (or per-gate-window, then mapped to segments) gate outputs:** `p_slowing`,
`p_focal`, `p_generalized` for **all** recordings in both cohorts. The recording-level gate is the
segment aggregate, not a separate computation.

---

## 5. The canonical data tables (define once, build once)

**One long-format master + typed sidecars.** No analysis reads anything else for primary results.

### 5.1 `segment_master` — the source of truth
One row per **(bdsp_id, segment, region)** over the whole recording:

| column | type | notes |
|---|---|---|
| bdsp_id | str | recording id (site+patient+date) |
| segment | int | 0-based, whole recording |
| t_start_s | float | segment onset in seconds |
| region | cat | 6 aggregates (+ 18 channels for the channel-grain build) |
| stage | cat | W/N1/N2/N3/REM |
| artifact_flag | bool | usable = ~flag |
| artifact_reason | cat | flat / high-amp / … / none |
| log_delta…log_total, rel_delta/theta/alpha, DAR, TAR, DTR, low_freq_rel | float | features |
| p_slowing, p_focal, p_generalized | float | per-segment gate |

### 5.2 Sidecars (join keys in brackets)
- `recording_meta` [bdsp_id]: age, sex, src, clean_normal, is_abnormal, recording_seconds, n_segments,
  n_usable, stage fractions, nearest-report id, `clean_pair`.
- `recording_labels` [bdsp_id]: report-derived labels (§3.5).
- `norms` [age-knot × stage × region × feature]: fitted GAMLSS parameters (§6).
- `deviation_field` [bdsp_id × segment × region × feature]: `z` (derived from `segment_master` + `norms`;
  materialized for speed).

### 5.3 Physical layout & scale (a decision for review)
Full per-segment × **per-channel** (18) × whole-recording × 27k ≈ **1.4 B rows** — not a single parquet.
Per-segment × **region** (6) ≈ **0.5 B rows** — large but partitionable.
**Proposed:** `segment_master` at **region grain** is the canonical default, **partitioned one parquet
per recording** (`segment_master/bdsp_id=.../part.parquet`); channel-grain is computed on demand for the
abnormal/focal subset that needs lateralization. *Reviewers: confirm region-default vs channel-everywhere,
and the partitioning scheme.*

### 5.4 Data dictionary & the one rule
A `docs/data_dictionary.md` defines every column, units, and allowed values. **Governance rule:** adding
or changing a table requires a matching edit to `DATA_INVENTORY.md` and `data_dictionary.md` in the same
commit. No orphan tables, no filename aliases (the `_py` alias incident is why).

---

## 6. Normative model (growth curves)

### 6.1 Specification
GAMLSS with a **BCT (Box–Cox-t) / LMS** family per (stage × region × feature), smooth in age:
distribution parameters μ (location), σ (scale), ν (skew), τ (kurtosis) as penalized smooth functions of
age. This yields age-continuous centiles and a z-score for any (age, stage, region, feature).

### 6.2 Conditioning
- **Age:** continuous (smooth); centiles reported at standard ages. Fractional age used where available.
- **Stage:** separate curves per stage (vigilance matching is built in, not a covariate afterthought).
- **Region / feature:** separate curves per region × feature.
- **Sex:** **pooled** (P2; prior evidence ΔAUROC ≤ 0.002). Sensitivity analysis fits sex-specific curves
  and reports ΔAUROC to justify pooling.

### 6.3 Fitting and the deviation field
- Fit on `clean_normal` only; **k-fold cross-fitting** so a normal recording's own z uses out-of-fold
  parameters (no self-normalization optimism).
- **Deviation field:** `Z[segment, region, feature] = (x − μ(age,stage,region,feature)) / σ(...)`
  (or the BCT z, which handles skew/kurtosis). Report the **linear predictor / SD**, not a probability.

---

## 7. The two-stage analysis

### 7.1 GATE (Morgoth)
- Presence (`p_slowing`), focal (`p_focal`), generalized (`p_generalized`), per segment → recording
  aggregate. Operating points chosen so both focal and generalized false-positive rates are < 1% on
  clean-normals (τ_gen ≈ 0.40, τ_foc ≈ 0.50; re-tuned on the re-run). Gate is the **only** module that
  decides focal-vs-generalized.

### 7.2 DESCRIBE (deviation field) — the governed descriptors
Applied only where the gate fires (else "No pathological slowing."):
1. **Amount** `S = w·(δ-excess, θ-excess, α-attenuation)` — one L1-learned "amount direction" `w`, fit
   in **wake**, applied unchanged everywhere; **α-attenuation is WAKE-ONLY** (alpha = posterior dominant
   rhythm; note `corr(z_TAR−z_θ, −z_α) = 0.985` — TAR is largely alpha loss). Reported in **SD + centile**.
2. **Location:** side (focal), max-deviation lobe (PROVISIONAL); **anterior–posterior predominance** for
   generalized (a real reportable axis; side is undefined there).
3. **Band:** low-confidence delta / theta / mixed (**PROVISIONAL**, P5).
4. **Prevalence:** % of stage-segments exceeding the normal centile (ALLOWED).
5. **Persistence:** longest run / episode count (PROVISIONAL).
6. **Stage-accentuation / sleep-only** (ALLOWED).
Sentence generation is fully claims-gated (`scripts/110`); FORBIDDEN clauses (severity adjective, ACNS
frequency word, focal-vs-gen from our features, peak-SD) are structurally unemittable.

### 7.3 Governance
The `z`/`S` (unsupervised) vs Morgoth/supervised distinction (§1) is enforced in analysis code and in
the claims table. Any "we see what readers miss" result must trace to the unsupervised path.

---

## 8. Statistical analysis

All CIs by stratified bootstrap over **recordings** (patient-clustered where a patient has multiple
recordings). Primary metrics pre-specified; α = 0.05; multiplicity per §8.6.

### 8.1 Detection (S1)
- **Primary:** AUROC, abnormal vs clean-normal, **whole-recording**, **vigilance-matched** (compare like
  stages; report per-stage and stage-pooled). Prior evidence: TAR/DAR ≈ 0.80–0.82; central rel_delta is
  weak — not a primary detector.
- **Nested CV** for any tuned score; report the optimism (prior ≈ 0). Report by `src` (cohort vs
  expansion) and note that ratio features are **not** pooled across sources with different acquisition.
- Sparse 3-feature score as the parsimonious detector (generalized ≈ 0.909 previously); focal detection
  requires **generalized cases in the negative set** (focal-vs-clean-normal-only collapses ≈ 0.61 — a
  documented pitfall; the negative set composition is pre-specified, not tuned).

### 8.2 Description validation (S3, S4)
- **Amount:** split-half ICC (prior 0.97). **Prevalence:** ICC (prior 0.94). Both are P3/P4.
- **Band:** agreement of the low-confidence call vs report band word (rel-θ−rel-δ ≈ 0.64; expected weak,
  P5); reported as PROVISIONAL, not promoted unless it clears P5's bar.
- **Generalized A–P predominance:** AUROC of the anterior-minus-posterior gradient (prior ≈ 0.60).
- **Localization:** side/lobe confusion vs report (data-driven max-deviation lobe + supervised LR),
  **macro-F1** (not accuracy — the majority/temporal default inflates accuracy).

### 8.3 Human ceiling (S5) — the honest bar
Report the MoE inter-rater ceiling (Fleiss κ 0.37 focal / 0.45 generalized; within-rater 0.56–0.64; band
κ 0.09–0.38) and a **blinded head-to-head**: our generated description vs the report sentence, scored by
independent neurophysiologists, with rater usernames anonymized R01…Rnn. System performance is always
reported *relative to* this ceiling, not against an implicit gold standard.

### 8.4 External validation
Phase-A external check (prior AUROC ≈ 0.903, with the two failed pre-registered predictions reported
honestly). V4a spindle-verified sleep-slowing analysis (AUROC ≈ 0.83–0.86) supports P6, on the
**unsupervised path** only.

### 8.5 Sensitivity analyses
Sex-specific vs pooled norms (P2); artifact-threshold sensitivity; coverage sensitivity (whole vs
first-600 s — expected to matter for description reliability but **not** to be the driver of any single
case, per the case-2 finding: whole-recording amount for case-2 recordings was median −0.18 SD);
clean_pair on/off; segment overlap; band-edge (pre/post 7–8 Hz fix).

### 8.6 Multiplicity, missing data, reproducibility
- Primary endpoints pre-specified; secondary/exploratory clearly labeled; BH-FDR within families.
- Missing stage/feature: report rates; recordings below the usable-fraction floor excluded (§3.2), not
  imputed.
- **Reproducibility:** every table/figure regenerated by a numbered script from `segment_master` +
  sidecars; environment pinned (timm==0.9.16, `KMP_DUPLICATE_LIB_OK`, np.trapz→trapezoid shim); one
  `make all` from the master to all outputs.

---

## 9. Figures (planned)

| Fig | Content |
|---|---|
| 1 | System schematic: gate → branch (focal/generalized) → governed describe (the two-stage figure). |
| 2 | Growth curves: slowing feature vs age, per stage (centile fans), for key regions. |
| 3 | Stage dependence: the same feature across W/N1/N2/N3/REM at fixed age (why vigilance matching matters). |
| 4 | Detection: ROC (whole-recording, vigilance-matched), overall + by src + by stage; vs human κ band. |
| 5 | Focal/generalized: side/lobe confusion (macro-F1) + generalized A–P gradient distribution. |
| 6 | Descriptor reliability: split-half amount, prevalence ICC; band low-confidence agreement. |
| 7 | Case vignettes: raw EEG + our governed sentence vs report, including a "reader under-reports sleep slowing" case (unsupervised path). |

## 10. Tables (planned)

**Table 1 — Cohort description** (the summary that was missing). Rows = characteristics; columns
stratified by group. Overall + by `src` (cohort / expansion) and by clean-normal / abnormal:

| Characteristic | metric |
|---|---|
| Recordings, n | count |
| Patients, n | unique |
| Age, y | median (IQR); by decade band 0–18/18–45/45–60/60–75/75+ |
| Sex | n (%) female |
| Recording length | median (IQR) min; % > 1 h (cEEG) |
| Usable segments | median (IQR); % artifact-flagged |
| Stage composition | % W/N1/N2/N3/REM (segment-weighted) |
| Report available / `clean_pair` | n (%) |
| clean_normal / is_abnormal | n (%) |
| Abnormal detail | focal n, generalized n; focal side L/R/bilat; gen topography ant/post/unspec; band δ/θ/mixed |

**Table 2 — Detection performance:** AUROC (95% CI) overall, by src, by stage, vigilance-matched; vs
human ceiling.
**Table 3 — Descriptor reliability & validity:** amount ICC, prevalence ICC, band agreement, A–P AUROC,
localization macro-F1 — each with its claims-table status (ALLOWED/PROVISIONAL).
**Table 4 — Pre-registered predictions:** P1–P6, threshold, result, confirmed/falsified.

---

## 11. Data governance / PHI (binding)
- Raw report text is **never** committed — read from the scratchpad extract only; PHI already scrubbed
  from git history, do not reintroduce.
- OMOP is read-only (person_id → birth_datetime for age only). De-identified `dob` is date-shifted —
  never join to real-date sources.
- Viewer bundles are PHI-free: opaque `case_id`, no bdsp_id/dates/report text/EDF headers; crosswalks
  live only in the scratchpad; `viewer/data/` is gitignored.
- MoE rater usernames (incl. the author) are anonymized R01…Rnn and never committed.

## 12. Build order (the one clean re-run)
1. Freeze this SAP after review.
2. Finalize the extractor (band-edge fix in) and the fleet worker to **persist per-segment features,
   stages, artifact flags, and per-segment gate** over the whole recording, both cohorts.
3. Run the fleet once → write `segment_master` (partitioned) + sidecars; validate row counts, coverage,
   stage/artifact rates against Table 1 expectations.
4. Fit norms (cross-fit) → `norms` → materialize `deviation_field`.
5. Run every numbered analysis script from the master → Tables 1–4, Figures 1–7.
6. Blinded head-to-head + case review.
7. Lock. Any re-run reproduces byte-for-byte from `segment_master` + pinned env.

---

### Appendix A — The four pitfalls this plan exists to prevent
1. **Which data?** Three provenances at three grains/coverages caused constant confusion → ONE
   `segment_master` (whole-recording, per-segment) + typed sidecars + data dictionary; `src` column, no
   filename aliases.
2. **Coverage.** First-600 s vs whole recording → whole recording everywhere; intended use is any length.
3. **Report broadcast / label contamination.** One report → many EEGs; flag-level labels → `clean_pair`
   + finding-level extraction with negation.
4. **Silent stripping.** Artifact segments removed, not flagged → retain + `artifact_flag`.
