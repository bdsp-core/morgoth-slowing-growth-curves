# Statistical Analysis Plan — Lifespan × sleep-stage normative growth curves for EEG slowing

**Status:** DRAFT for colleague review, to be finalized *before* the fleet re-run.
**Version:** 1.0 (2026-07-10). **Owner:** MBW.
**Companion docs:** `docs/DATA_INVENTORY.md` (data tables), `docs/data_dictionary.md` (canonical column
definitions), `docs/run_manifest_schema.md` (frozen EEG list), `docs/claims_table.md` (clause governance),
`docs/description_architecture.md` (descriptor definitions).

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
  generalized (or both - they are not mutually exclusive). This is the only module allowed to make the categorical call. Morgoth can make these determinations at the level of individual 15 second segments, or at the whole EEG level. Here we rely on the 15-second segment level, and make any whole level EEG determination by pooling over the 15 second segment determinations (e.g. taking the maximum, or median, or mean). 
- **DESCRIBE (normative deviation field): how much, where, which band, how prevalent, how persistent,
  in which stage(s).** A measurement layer that never makes the categorical call.

**Design principle (circularity guard).** Two named objects with a hard rule:
- `z` / `S` — the **unsupervised** normative deviation and the amount score. Because they are fit only
  to clinician-labeled normals and never see the report label of abnormal cases, they may support the
  claim *"we measure slowing readers under-report."*
- **Morgoth gate** and any **supervised** score — may **never** support that claim (they are trained
  toward the report and would be circular).

Every reportable sentence clause is tagged ALLOWED / PROVISIONAL / FORBIDDEN in `docs/claims_table.md`;
this SAP inherits that governance.

**Governing principle — one clean-room computation, zero reuse.** Every number in the paper is computed
by **one fleet of computers on AWS run over a single frozen list of EEGs, using exactly one version of the code**. We do
**not** reuse any previously computed feature, stage, gate, or aggregate — not `segment_features`, not
`channel_stage_features`, not `gate_probs`, none of it. Reusing precomputed artifacts (built at different
times, with different coverage, by different scripts) is the direct cause of the which-data confusion
this plan exists to end. Instead: pull whatever EEGs the frozen list names into the bucket, run the
identical pipeline on **all** of them (including the expert-scored EEGs of §3.6), and write everything
fresh into `segment_master`. The old derived tables are retained only for historical reference and are
never an input to a primary result.

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
- S5. Position system performance relative to the human ceiling — the honest bar.
- S6. **Inter-rater reliability (IRR).** On the EEGs scored by multiple experts (§3.6), measure
  between-rater and within-rater agreement for slowing (presence, focal/generalized, band, side/topography)
  — this *is* the human ceiling — and evaluate our system against those same EEGs, run through the
  identical pipeline, so the comparison is on one footing.
- S7. **Benchmark against prior qEEG slowing metrics (van Putten lineage) — and adopt them if superior.**
  Compute the published metrics *faithfully to their definitions* on the canonical data, and run a
  three-arm head-to-head (as-published vs stage/age/sex-normed vs our features + Morgoth) on identical
  recordings and labels. If any van Putten metric beats our chosen feature/score on a target, we **adopt
  it** (§8.7). This is both a fair comparison and a search for anything better than what we have.

**Pre-registered predictions** (state direction *and* the outcome that would falsify).
| # | Prediction | Falsified if |
|---|---|---|
| P1 | Detection AUROC ≥ 0.80 whole-recording, vigilance-matched | < 0.75 |
| P2 | Sex can be pooled in the norms | ΔAUROC from adding sex > 0.01 |
| P3 | Amount score is reliable | split-half ICC < 0.8 |
| P4 | Prevalence descriptor is reliable | ICC < 0.8 |
| P5 | Band call is *weak* (report only as low-confidence) | rel-power band-match > 0.8 (then promote it) |
| P6 | Readers under-report **sleep** slowing (unsupervised path) | our sleep-slowing rate ≤ report rate |
| P7 | Our detection meets/exceeds the human ceiling (expert-vs-consensus balanced acc ≈ 0.80) on the expert-scored EEGs | our balanced acc < between-rater ceiling |
| P8a | Stage/age/sex-norming a van Putten metric beats the same metric as-published (their own instrument, improved by our framework) | ΔAUROC(normed − raw) ≤ 0 |
| P8b | Our best feature/score ≥ the best van Putten metric on each target (else we adopt theirs) | any van Putten arm > ours by ΔAUROC > 0.02 → **adopt it** |

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
Three nested units (§5.3): **patient** = `patient_id` (the legacy `bdsp_id`, site+person), **EEG /
recording** = `eeg_id` = `{patient_id}_{eeg_datetime}` (a patient may have several), and **segment**.
`eeg_id` is the recording key for every analysis; CIs are patient-clustered on `patient_id`.

**⚠ PITFALL 1 — report broadcast.** A single report can be joined onto more than one EEG of the same
patient by a naive report↔EEG join, contaminating labels. **Rule:** assign each EEG its nearest-in-time
report and carry a `clean_pair` flag; all label-dependent analyses filter to `clean_pair`.
**This pairing is computed UP FRONT — before the run — and frozen into the manifest** (§13 step 2, and
`run_manifest_schema.md`), so "which report belongs to which EEG" is fixed once and never re-derived
mid-analysis. Report the number of EEGs dropped by the filter.

### 3.4 Reference ("normal") definition
`clean_normal` = report explicitly normal **and** not carrying any abnormal finding flags. The
normative model is fit on `clean_normal` recordings only. Abnormal cases never enter the fit.

### 3.5 Label derivation and contamination guards
From report text (read from the PHI-safe scratchpad extract, never committed):
- `is_abnormal`, `has_focal_slow`, `has_gen_slow`; focal `side`/`region`/`band`; generalized
  `band`/`topography` (anterior / posterior / unspecified) / `state`; `gen_class`.
- **Focal-side extraction (code):** `scripts/20_extract_report_labels.py` (`side_of` / `extract_side`, v2)
  parses laterality *per slowing-clause* — honoring `R>L`/`L>R` predominance, mapping 10–20 electrode names
  to a side, letting a specific unilateral finding beat a diffuse background comment → `focal_side ∈
  {left, right, bilateral, na}`, materialized in `recording_labels` by `scripts/60_build_unified_labels.py`.
  (v1 dumped ~81% of sided reports into 'bilateral'; v2 recovered ~32k.)
- **⚠ PITFALL 2 — flag-level contamination.** Labels are extracted at the *finding* level with negation
  handling; a report mentioning "no focal slowing" must not set `has_focal_slow`. Severity adjectives
  (mild/moderate/marked) are **not** treated as quantitative (they are null across combinations) and are
  FORBIDDEN as an output.

### 3.6 Expert-panel (multi-rater) EEGs — for inter-rater reliability and the human ceiling
Two datasets provide EEGs each scored by **multiple** electroencephalographers. **Both are pulled into
the bucket and run through the identical pipeline (§4) as part of the one clean-room re-run** — their
`segment_master` rows are computed exactly like every other recording, so our system's output on a given
EEG is directly comparable to that EEG's expert panel. They are tagged with a `panel` flag and a
`panel_set` value in `recording_meta`.

| Set | Composition | Scoring | Use |
|---|---|---|---|
| **OccasionNoise** | 100 EEGs (EDF, 20 ch, 200 Hz, ~50 min; age/sex in EDF header) | 18 experts, recording-level focal/generalized × epileptiform/non-epileptiform; **Part I / Part II re-read by 15 raters** (within-rater test-retest); signed-report category | External test set + within- and between-rater IRR; overlay each expert as an operating point on our ROC |
| **MoE** | ~1,962 events (rounds r1–r3, disjoint) | 18–21 experts, **band-resolved** focal/gen slowing (δ/θ/α/β); rater coverage 7–1000 events | Between-rater IRR incl. band; band-agreement analogue to ours |

Handling rules:
- **Exclusion is label-based, not cohort-based.** `icare_*` (cardiac-arrest) events are **not** dropped
  merely for being cardiac-arrest — a cardiac-arrest EEG that shows slowing is in-domain. Exclude only on
  **label/state** (isoelectric, predominant burst-suppression, electrocerebral inactivity), the same rule
  as §3.2.
- **Author-as-rater:** `bwestove` (MBW) is one panel rater — **disclosed and retained** (exclusion not
  necessary: the ceiling is a between-rater agreement measure and validation is against the panel
  *consensus*, not against any single rater). Rater identities anonymized R01…Rnn; never committed.
- **Consensus label:** for panel EEGs, the multi-rater consensus (majority / adjudicated) is a
  higher-quality reference than a single signed report; the **consensus proportion** (fraction of experts
  who saw slowing) is a graded human *conspicuity* target we may test our `z` against (pre-registered).


### 3.7 The frozen report↔EEG manifest (built up front)
Before the fleet runs we compute and **freeze** the mapping of every EEG to its report, plus all
report-derived features and metadata — so labels are fixed once (§3.3) and pairing quality can be reviewed
by eye before committing compute.

**Contents** (one row per `eeg_id`):
- identity + path: `eeg_id`, `patient_id`, `eeg_datetime`, EEG file path (→ run manifest, `run_manifest_schema.md`);
- pairing: `nearest_report_id`, `clean_pair` (§3.3);
- **report text: LOCAL only** (scratchpad, PHI) — for the pairing review; never committed;
- report features: every extracted label (`is_abnormal`, `has_focal_slow`/`has_gen_slow`,
  `focal_side`/`region`/`band`, `gen_band`/`topography`/`state`, `gen_class`, `report_stratum`, `n_report_chars`);
- metadata: `age`, `sex`, `recording_seconds` (EDF-header duration), `src`, `panel`/`panel_set`.

**Code (already built; in `scripts/`):**
- `scripts/20_extract_report_labels.py` — report text → labels incl. the v2 laterality extractor (§3.5);
  publishes PHI-free labels only, raw text kept local.
- `scripts/88_report_pairing_audit.py` — nearest-in-time pairing → `clean_pair` (the report-broadcast fix,
  §3.3 / PITFALL 1).
- `scripts/60_build_unified_labels.py` — assembles the unified label table (identity + all report features
  + provenance).
- `scripts/120_build_report_manifest.py` — joins these into the frozen manifest (eeg_id = patient+datetime,
  features, clean_pair, age/sex). Duration is populated authoritatively in `recording_meta` from the EDF
  header at run time; the report-CSV `Duration` is deferred pending the eeg_datetime↔CSV-identity reconcile.

**Filename:** committed PHI-free `data/manifest/report_manifest_v<N>.parquet` (+ `.meta.json` freeze record:
version, UTC, code tag, counts, sha256); the with-text version lives only in the scratchpad. Versioned and
frozen exactly like the run manifest (immutable; add/remove → new version).
---

## 4. Signal processing and feature extraction (the canonical pipeline)

One extractor (`src/morgoth_slowing/features/extract.py`), one parameterization, applied identically to
every recording in both cohorts, over the analyzed span (up to the first 24 h; §4.3).

### 4.1 Preprocessing
- Reference montage → longitudinal bipolar **double-banana** (18 channels: Fp1-F7 … Cz-Pz).
- Resample to **200 Hz**. Band-limit 0.5–45 Hz. Line-noise handled at feature time (multitaper).

### 4.2 Segmentation
- **Segment = 15 s = 3000 samples @ 200 Hz; step = 14 s (2800 samples, 1 s overlap).** *Not 10 s.*
- Segments are indexed `0..K-1` over the analyzed span (≤24 h; K up to ~6,170 at the 24 h cap, §4.3).

**⚠ PITFALL 3 — coverage.** The legacy description table used only the first 600 s (42 segments). **Rule:**
every per-segment feature, stage, artifact flag, and gate output is computed over **up to the first 24 h**
of the recording (`MAX_ANALYZE_HOURS = 24`): recordings ≤24 h are analyzed in full; longer cEEG is capped at
the first 24 h. "First-600 s" is never a coverage default anywhere.

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
| theta | 4–8 |
| alpha | 8–13 |
| beta | 13–30 |
| gamma | 30–45 |
| total | 0.5–45 |

**Band-edge fix (applied):** theta is **4–8 Hz**, not the legacy 4–7. The old 4–7/8–13 split left a 7–8 Hz
hole that discarded ~23% of theta power (clinically theta runs to 8 Hz); closing it also improves band-word
discrimination (0.58→0.60; `scripts/109`). Theta 4–8 is now contiguous with alpha 8–13. Features per (segment, channel/region): `log_{band}`, `rel_{band}` (delta/theta/alpha), `DAR`
(δ/α), `TAR` (θ/α), `DTR` (δ/θ), `low_freq_rel`.

**Prior-metric features (van Putten lineage), computed faithfully in the same pass** so the S7 benchmark
(§8.7) uses identical PSDs (definitions/refs in `references/README.md`). Per (segment, channel/region):
`DTABR` = (δ+θ)/(α+β), `ADR` = α/δ, `SEF95`, `median_freq`, `peak_freq`. Per (segment, **whole_head**):
`Q_SLOWING` = P[2–8]/P[2–25] (Lodder & van Putten 2013 — their best-agreeing slowing metric, κ=0.76),
`Q_APG` = P_ant/(P_ant+P_pos) on alpha, `r_sBSI` (revised **power-based** BSI, hemisphere-mean per PSD bin
0.5–25 Hz; van Putten 2007), `pdBSI` (our signed extension → side). Per (segment, homologous pair): `Q_ASYM`.

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
One row per **(eeg_id, segment, region)** over the whole recording. **The key is the EEG, not the
patient** — one patient may have several EEGs, so a patient-level key would collide their recordings
(see §5.3).

| column | type | notes |
|---|---|---|
| eeg_id | str | **recording key** = `{patient_id}_{eeg_datetime}` (unique per EEG; matches the legacy `sub-<id>_<YYYYMMDDHHMMSS>` filename) |
| patient_id | str | person key (= legacy `bdsp_id`, site+person); one patient → many `eeg_id` |
| eeg_datetime | str | recording start `YYYYMMDDHHMMSS` (distinguishes a patient's EEGs) |
| segment | int | 0-based, whole recording |
| t_start_s | float | segment onset in seconds |
| region | cat | 6 aggregates (+ 18 channels for the channel-grain build) |
| stage | cat | W/N1/N2/N3/REM |
| artifact_flag | bool | usable = ~flag |
| artifact_reason | cat | flat / high-amp / … / none |
| log_delta…log_total, rel_delta/theta/alpha, DAR, TAR, DTR, low_freq_rel | float | features |
| p_slowing, p_focal, p_generalized | float | per-segment gate |

### 5.2 Sidecars (join keys in brackets)
- `recording_meta` [eeg_id]: patient_id, eeg_datetime, age, sex, src, clean_normal, is_abnormal,
  recording_seconds, n_segments, n_usable, stage fractions, nearest-report id, `clean_pair`.
- `recording_labels` [eeg_id]: report-derived labels (§3.5).
- `norms` [age-knot × stage × region × feature]: fitted GAMLSS parameters (§6).
- `deviation_field` [eeg_id × segment × region × feature]: `z` (derived from `segment_master` + `norms`;
  materialized for speed).
- `descriptors` [eeg_id]: the system's per-recording **description outputs** (what the sentence generator
  reads): amount (SD, centile), band, **`pred_focal_side`** (+ `side_margin`), prevalence, persistence,
  stage-accentuation, and the pooled gate probs. Report side lives in `recording_labels`; predicted side
  lives here — the two are compared in §8.2, never merged.

### 5.3 Patient vs EEG vs segment — the identity rule
Three nested units, kept explicit so nothing silently collapses: **patient** (`patient_id`) → **EEG /
recording** (`eeg_id`) → **segment** (`segment`). `eeg_id` is the analytic key for every recording-level
table; `patient_id` is carried alongside for patient-clustered CIs and the report-broadcast dedup (§3.3).
Legacy tables keyed on `bdsp_id` == today's `patient_id`, which is why a patient's multiple EEGs were
collapsed — the canonical run does not repeat that.

### 5.4 Physical layout & scale (a decision for review)
Full per-segment × **per-channel** (18) × whole-recording × 27k ≈ **1.4 B rows** — not a single parquet.
Per-segment × **region** (6) ≈ **0.5 B rows** — large but partitionable.
**Proposed:** `segment_master` at **region grain** is the canonical default, **partitioned one parquet
per recording** (`segment_master/eeg_id=.../part.parquet`); channel-grain is computed on demand for the
abnormal/focal subset that needs lateralization. *Reviewers: confirm region-default vs channel-everywhere,
and the partitioning scheme.*

### 5.5 Data dictionary & the one rule
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

### 7.4 Lateralization — which side (focal)
Side is tracked as **two distinct quantities, never conflated**:
- **Report side** (the label): `recording_labels.focal_side ∈ {left, right, bilateral, na}`, extracted by
  `scripts/20` + `scripts/60` (§3.5).
- **Our predicted side** (the measurement): from the **signed** homologous-channel deviation — for each L/R
  homologous pair, the difference in slowing-feature deviation (`z_R − z_L`), together with the signed
  `pdBSI` and per-pair `Q_ASYM` (§4.5). The recording's side = sign of the pooled lateralized excess,
  **abstaining to 'bilateral / none' when no pair clears the normal 97th-centile asymmetry** (same abstain
  logic as the amount descriptor). Stored as `pred_focal_side` (+ `side_margin`, the SD of the L−R excess)
  in the `descriptors` output (§5.2).

Invoked only when the gate fires **focal** (§7.1); for generalized, side is undefined and we report A–P
topography (Q_APG) instead. Validation: predicted vs report side confusion + accuracy (§8.2), against the
human ceiling on the panel (§8.3), with the van Putten pdBSI / Q_ASYM arms as comparators (§8.7).

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
- **Localization:** `descriptors.pred_focal_side` vs `recording_labels.focal_side` (confusion + accuracy),
  and predicted lobe vs report region (data-driven max-deviation lobe + supervised LR), **macro-F1** (not
  accuracy — the majority/temporal default inflates it). Side method defined in §7.4.

### 8.3 Inter-rater reliability and the human ceiling (S5, S6) — the honest bar
Computed on the expert-panel EEGs of §3.6, which are run through the **identical** pipeline so system and
experts are scored on one footing.

**(a) Between-rater agreement (the ceiling).** For each axis — presence of slowing, focal vs generalized,
band (δ/θ/α/β), side/topography — report **Fleiss' κ** (all raters) and **median pairwise Cohen κ**
[95% CI, bootstrap over rater pairs], with **prevalence and Gwet's AC1** alongside (κ is unstable at the
extreme prevalences here — e.g. focal-alpha ≈ 0.5% — so AC1 is the robustness check). Prior estimates to
reproduce: focal-slowing Fleiss κ ≈ 0.37, generalized ≈ 0.45; band far worse (focal-θ κ ≈ 0.09, focal-δ
≈ 0.35); band agreement *conditional on both raters calling slowing* ≈ 0.54 focal / 0.27 generalized.
Restrict to raters with ≥200 votes and pairs with ≥100 co-rated events.

**(b) Within-rater agreement (test–retest).** On the OccasionNoise Part I / Part II re-reads (15 raters),
report within-rater κ per axis (prior ≈ 0.56 focal / 0.64 generalized). This bounds how reproducible a
single expert is — the true ceiling on any single-reader reference label.

**(c) Expert-vs-consensus.** Balanced accuracy of each expert against the panel consensus (prior ≈ 0.80
focal / 0.81 generalized); this is the number our detector must **meet or beat** (P7).

**(d) System vs the panel, same footing.** Run our unchanged gate+describe on the panel EEGs; plot our
ROC and **overlay each expert as an operating point** (sensitivity/specificity vs consensus). Report our
balanced accuracy against consensus next to the expert distribution. `bwestove` excluded from any
system-validation comparison (kept only in the pure between-rater ceiling).

**(e) Graded conspicuity.** Correlate our unsupervised `z`/amount `S` with the **consensus proportion**
(fraction of experts who saw slowing) — a human graded target — as an honest, pre-registered test of a
severity-like axis (which single-report severity adjectives failed to provide).

**(f) Blinded head-to-head.** Independent neurophysiologists score our generated description vs the report
sentence, blinded to source; rater ids anonymized R01…Rnn. System performance is always reported
*relative to* this ceiling, never against an implicit gold standard.

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

### 8.7 Benchmark against prior qEEG slowing metrics (van Putten lineage) — S7
The published metrics are computed **faithfully to their original definitions** on the canonical data
(features in §4.5), then compared to ours on identical recordings, whole-recording, **vigilance-matched**,
against the same report/consensus labels. Existing scaffold: `scripts/47_vanputten_comparison.py` (to be
rebuilt against `segment_master`).

**Metrics (definitions taken from the primary sources in `references/`; see `references/README.md`).**

*Slowing (global) — the headline comparators:*
- **Q_SLOWING** = `P[2–8 Hz] / P[2–25 Hz]` (mean spectrum over scalp) [Lodder & van Putten 2013]. Abnormal
  if > 0.6. **This is van Putten's own slowing metric and it had the best report agreement of their five
  (κ = 0.76).** It is the primary thing our slowing score must beat or adopt (P8b).
- **DAR** = δ/α; **ADR** = α/δ (= 1/DAR); **DTABR** = (δ+θ)/(α+β) [Finnigan & van Putten 2013].
- **Relative δ, relative θ** (already in the feature set).
- **SEF95 / median_freq / peak_freq** — spectral-edge & dominant-frequency summaries; lower = slower.

*Anterior–posterior gradient (generalized):*
- **Q_APG** = `P_ant / (P_ant + P_pos)` on **alpha**, eyes-closed, Laplacian montage [Lodder & van Putten
  2013]. Normal < 0.4, abnormal > 0.6 (posterior→anterior shift). Adopt as the A–P comparator.

*Asymmetry / lateralization (focal):*
- **r-sBSI** (revised BSI) = `(1/K) Σ_n |R*_n − L*_n|/(R*_n + L*_n)`, `R*_n = mean over right-hemisphere
  channels of PSD **power** (squared coeff) at bin n`; **0.5–25 Hz** [van Putten 2007]. (Corrects our earlier
  note: it is **power-based and hemisphere-mean per frequency**, ~2× more sensitive than the 2004
  amplitude sBSI — not a per-pair mean.)
- **pdBSI** — **our own signed extension** of r-sBSI (drop the |·| so the sign gives the side); NOT a
  van Putten metric, labelled as ours.
- **Q_ASYM(c)** = normalized spectral difference per homologous pair c ∈ {Fp1,Fp2},{F7,F8},{F3,F4},{T3,T4},
  {C3,C4},{T5,T6},{P3,P4},{O1,O2}; asymmetric if any pair > 0.5 [Lodder & van Putten 2013].

*Not adopted (decided):*
- **r-tBSI** (revised temporal BSI, diffuse change vs a within-recording reference t0) [van Putten 2007] —
  a monitoring metric; our normative deviation is its cross-sectional analogue, so it is not computed as-is.
- **Q_REAC** (alpha reactivity) — **out**: we have no reliable eyes-open/closed annotations.
- **Q_ALPHA** (alpha/PDR peak frequency) — **out**: PDR grading is out of scope, separate from slowing.

**Three arms, same labels/recordings/stages.**
1. **As-published (raw).** The metric computed and thresholded as in the source — whole-head or pairwise,
   **no** age/sex/stage normalization (how it is actually deployed).
2. **Normed.** The *same* metric expressed as an age/sex/**stage**-conditioned deviation in our framework
   (its `z` from the norms). Tests whether our contribution — lifespan + vigilance normalization — improves
   *their* instrument (P8a). This is the fair, apples-to-apples upgrade.
3. **Ours + Morgoth.** Our chosen feature/amount score (unsupervised) and the Morgoth gate.

**Targets.** Abnormal-vs-clean-normal and generalized-vs-clean-normal for the global metrics
(Q_SLOWING/DAR/DTABR/SEF/rel-δ) and, for generalized topography, Q_APG; focal-vs-clean-normal (and side
accuracy) for the asymmetry metrics (r-sBSI/Q_ASYM/pdBSI). AUROC (95% CI, patient-clustered bootstrap);
side via pdBSI sign and per-pair Q_ASYM vs report side.

**Adoption rule (the "or use theirs" clause, P8b).** Pre-registered and symmetric: if any van Putten arm
beats our best on a target by **ΔAUROC > 0.02** (CIs excluding 0), we **adopt** that metric — add it to the
feature set (and, for lateralization, use pdBSI sign) — and report the swap transparently. If ours wins or
ties, we report the honest margin. Either way the reader sees the head-to-head, not just our victory.

**Expectation (not a gate).** Prior in-house numbers (legacy first-600 s data): raw DAR ≈ 0.68 / DTABR
≈ 0.68 / BSI ≈ 0.74; our age/sex-normed DAR deviation ≈ 0.71; Morgoth p_abnormal ≈ 0.95. The re-run
re-computes all of these whole-recording and vigilance-matched, adds Q_SLOWING/Q_APG/Q_ASYM from the
Lodder & van Putten (2013) paper (their Q_SLOWING agreed with reports at κ=0.76 — a strong bar), and fixes
the normed-BSI arm the legacy run left as NaN (a normalization bug, not a null result).

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
| 8 | Human ceiling: our ROC on the panel EEGs (§3.6) with **each expert overlaid as an operating point**, plus a κ/agreement panel (between- vs within-rater, per axis) and our `z` vs consensus-proportion scatter. |
| 9 | Benchmark: grouped-bar AUROC for van Putten metrics — as-published vs normed vs ours vs Morgoth — for abnormal/generalized/focal (the S7 three-arm comparison). |

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
**Table 4 — Pre-registered predictions:** P1–P7, threshold, result, confirmed/falsified.
**Table 5 — Inter-rater reliability & human ceiling** (on the §3.6 panel EEGs, same pipeline): per axis
(presence, focal/gen, band, side/topography) — prevalence, Fleiss κ, median pairwise Cohen κ [CI], Gwet
AC1, within-rater κ (OccasionNoise re-read), expert-vs-consensus balanced accuracy, and **our system's**
balanced accuracy against consensus on the same EEGs.
**Table 6 — Benchmark vs prior qEEG slowing metrics (van Putten lineage), S7:** per target (abnormal / generalized / focal) — AUROC [95% CI] for each metric in three arms (as-published, age/sex/stage-normed, ours+Morgoth), plus pdBSI side accuracy; the **adopted** column flags any metric that met the ΔAUROC>0.02 adoption rule (P8b).

---

## 11. Data governance / PHI (binding)
- Raw report text is **never** committed — read from the scratchpad extract only; PHI already scrubbed
  from git history, do not reintroduce.
- OMOP is read-only (person_id → birth_datetime for age only). De-identified `dob` is date-shifted —
  never join to real-date sources.
- Viewer bundles are PHI-free: opaque `case_id`, no bdsp_id/dates/report text/EDF headers; crosswalks
  live only in the scratchpad; `viewer/data/` is gitignored.
- MoE rater usernames (incl. the author) are anonymized R01…Rnn and never committed.

## 12. Code organization, review, and testing (pre-fleet gate)
The fleet runs one code version over ~27k+ EEGs; a bug found afterwards means re-running everything. So every
script the fleet executes is **organized, named, reviewed, and tested before freeze** — a hard gate.

1. **Inventory & separate.** Enumerate exactly the modules the fleet runs — the extractor
   (`src/morgoth_slowing/features/extract.py`), `artifact.py`, the sleep-stager loader, the Morgoth gate
   (`run_gate`), and the worker (`scripts/30_ingest_worker.py`) — plus the pre-fleet manifest builders
   (§3.7). Everything else in `scripts/` is *analysis*, not fleet code; label the split.
2. **Name & document.** Each fleet module gets a one-line purpose header and a row in `DATA_INVENTORY.md` /
   `data_dictionary.md`. No dead code on the fleet path (cf. the retired `bandpower.py`).
3. **Unit tests** for the load-bearing functions: band powers on a synthetic PSD with known integrals;
   `usable_mask` on flat/high-amp fixtures; segment indexing and the 24 h cap; the van Putten metrics against
   hand-computed values; stage-grid alignment (a regression test for the cross-correlation misalignment bug).
4. **Golden-recording test.** Run the whole pipeline end-to-end on a few known recordings and diff
   `segment_master` against a checked-in expected output (schema, row counts, coverage, feature ranges).
5. **Review.** A second reader (or an adversarial `/code-review`) signs off on the fleet path.
6. **Freeze.** Tag the reviewed code (`git tag run-v<N>`); the fleet runs only that tag.

---

## 13. Build order (the one clean re-run — zero reuse)
1. Freeze this SAP after review.
2. **Code-review gate (§12):** organize, test, review, and **tag** the fleet code (`git tag run-v<N>`).
3. **Freeze the report↔EEG manifest (§3.7)** — pairing (`clean_pair`) + all report features + metadata,
   computed up front so labels are fixed before any analysis; commit the PHI-free version.
4. **Freeze the EEG run list** (`run_manifest_schema.md`): both cohorts (§3.1) **and** the expert-panel EEGs
   (§3.6). Exclusion is **label-based only** (isoelectric / burst-suppression), never cohort-based. This is
   the single source of "which EEGs."
5. **Pull to the bucket.** Copy every EEG on the run list into the bucket. Nothing is analyzed from a prior
   location or a prior computation.
6. **Run the fleet once over the entire manifest** — cohort, expansion, and panel EEGs through the tagged,
   *identical* code path, **up to the first 24 h** per recording. No reuse of `segment_features` /
   `channel_stage_features` / `gate_probs` or any prior aggregate. Write everything fresh → `segment_master`
   (partitioned) + sidecars (incl. per-segment features, stages, artifact flags, per-segment gate).
7. Validate row counts, coverage, stage/artifact rates, and panel-EEG presence against Table 1 expectations.
8. Fit norms (cross-fit) → `norms` → materialize `deviation_field`; run the describe step → `descriptors`.
9. Run every numbered analysis script from the master → Tables 1–6, Figures 1–9 (incl. IRR/human ceiling
   on the panel EEGs, same footing).
10. Blinded head-to-head + case review.
11. Lock. Any re-run reproduces byte-for-byte from the manifests + `segment_master` + pinned env + code tag.

---

### Appendix A — The five pitfalls this plan exists to prevent
1. **Which data?** Three provenances at three grains/coverages caused constant confusion → ONE
   `segment_master` (whole-recording, per-segment) + typed sidecars + data dictionary; `src` column, no
   filename aliases.
2. **Coverage.** First-600 s vs whole recording → analyze **up to the first 24 h** everywhere; intended use is EEG of any length (capped at 24 h).
3. **Report broadcast / label contamination.** One report → many EEGs; flag-level labels → `clean_pair`
   + finding-level extraction with negation.
4. **Silent stripping.** Artifact segments removed, not flagged → retain + `artifact_flag`.
5. **Reuse.** Mixing precomputed artifacts built at different times/coverage/code caused the confusion
   this whole plan addresses → **zero reuse**: one frozen EEG manifest, one code version, one fleet run
   over *all* recordings (cohort + expansion + expert panel), everything written fresh (§13).
