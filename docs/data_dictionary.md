# Data dictionary — canonical tables

Authoritative column-level definition for the canonical dataset produced by the one clean-room fleet run
(`docs/analysis_plan.md` §5, §12). **Governance:** adding or changing a column requires editing this file
and `docs/DATA_INVENTORY.md` in the same commit. Every primary result reads only the tables below.

> The legacy Growth_curves `.mat` format (first-600 s, precomputed) is documented separately in
> `docs/legacy_growth_curves_matformat.md` and is **not** an input to any canonical table.

Conventions: power in µV²; `log_*` = natural log of band power; `rel_*` = band power / total power (0–1);
ratios dimensionless. Missing = NaN, never silently imputed (SAP §8.6). Segment = 15 s @ 200 Hz, step 14 s.

---

## 1. `segment_master` — source of truth (per segment × **channel**, whole recording)

Grain (decided 2026-07-11): one row per **(eeg_id, segment, channel)** — the 18 bipolar channels, so the
raw feature store keeps channel-level detail. The 6 clinical regions (whole_head, L/R_temporal,
L/R_parasagittal, midline) are **DERIVED downstream** (`canonical.to_regions`), not stored. The key is the
EEG, not the patient. Partitioned one parquet per recording (`segment_master/eeg_id=<id>/part.parquet`).
Per-segment quantities that are not channel properties (stage, artifact, gate, whole-head/spatial van
Putten metrics) live in the companion **`segment_summary`** (§1b), joined on `(eeg_id, segment)`. EEG-level
gate (`p_focal`, `p_generalized`) lives in the ledger `recording_meta` (§2).

| column | type | units / allowed | definition |
|---|---|---|---|
| `eeg_id` | str | `{patient_id}_{eeg_datetime}` | **recording key**; the partition; joins to summary + ledger |
| `segment` | int32 | 0-based | segment index over the **whole** recording |
| `t_start_s` | float32 | seconds | onset of the 15 s segment (step 14 s) |
| `channel` | category | 18 bipolar derivations | `Fp1-F7`,`F7-T3`,… (double-banana; recording.CH_NAMES) |
| `stage` | category | `W`,`N1`,`N2`,`N3`,`REM`,`Other` | per-segment sleep stage (denormalized from summary) |
| `artifact_flag` | bool | — | True = segment failed usability (retained, not dropped; per-segment) |
| `artifact_reason` | category | `none`,`flat`,`high_amp`,`other` | why flagged (`none` when usable) |
| `log_delta` | float32 | ln µV² | ln power 1–4 Hz (this channel) |
| `log_theta` | float32 | ln µV² | ln power 4–8 Hz |
| `log_alpha` | float32 | ln µV² | ln power 8–13 Hz |
| `log_beta` | float32 | ln µV² | ln power 13–30 Hz |
| `log_gamma` | float32 | ln µV² | ln power 30–45 Hz |
| `log_total` | float32 | ln µV² | ln power 0.5–45 Hz |
| `rel_delta` | float32 | 0–1 | delta / total |
| `rel_theta` | float32 | 0–1 | theta / total |
| `rel_alpha` | float32 | 0–1 | alpha / total |
| `log_DAR` | float32 | ln ratio | **ln**(delta/alpha) — name matches value; log space for GAMLSS (renamed from `DAR`) |
| `log_TAR` | float32 | ln ratio | **ln**(theta/alpha) (renamed from `TAR`) |
| `log_DTR` | float32 | ln ratio | **ln**(delta/theta) (renamed from `DTR`) |
| `low_freq_rel` | float32 | 0–1 | (delta+theta) / total |
| `DTABR` | float32 | ratio | (delta+theta)/(alpha+beta) — van Putten/Finnigan; §8.7 benchmark |
| `ADR` | float32 | ratio | alpha/delta — the **raw** ratio (van Putten); `exp(-log_DAR)` |
| `SEF95` | float32 | Hz | spectral edge frequency (95% of power below) |
| `median_freq` | float32 | Hz | median (SEF50) frequency |
| `peak_freq` | float32 | Hz | dominant/peak frequency |

Band edges use the corrected contiguous set (no 7–8 Hz gap; SAP §4.5). The raw ratios are carried as
van Putten `ADR`/`DTABR`; the log-space ratios are `log_DAR`/`log_TAR`/`log_DTR` (natural log) — the
name states which. `usable = ~artifact_flag`. Regions: `canonical.to_regions()` averages member channels
(whole_head = all 18).

## 1b. `segment_summary` — one row per (eeg_id, segment)

Per-segment context + whole-head/spatial metrics that are not per-channel. Partitioned
`segment_summary/eeg_id=<id>/part.parquet`; join to `segment_master` on `(eeg_id, segment)`.

| column | type | units / allowed | definition |
|---|---|---|---|
| `eeg_id`,`patient_id`,`eeg_datetime` | str | | keys/provenance |
| `segment`,`t_start_s`,`stage`,`artifact_flag`,`artifact_reason` | | | per-segment context (source of truth) |
| `p_slowing` | float32 | 0–1 | **per-segment** Morgoth gate: P(pathologic slowing) = 1 − P(class 0) |
| `Q_SLOWING` | float32 | ratio | P[2–8]/P[2–25] diffuse slowing (Lodder & van Putten 2013; abn>0.6) |
| `Q_APG` | float32 | 0–1 | P_ant/(P_ant+P_pos) alpha A–P gradient (Lodder & van Putten 2013) |
| `r_sBSI` | float32 | 0–1 | revised **power-based** BSI, hemisphere-mean per PSD bin 0.5–25 Hz (van Putten 2007) |
| `pdBSI` | float32 | −1..1 | our signed extension of r_sBSI (+ = right>left → side) |
| `Q_ASYM` | float32 | 0–1 | max normalized homologous-pair spectral difference (Lodder & van Putten 2013) |

---

## 2. `recording_meta` — one row per EEG (recording)

| column | type | allowed | definition |
|---|---|---|---|
| `eeg_id` | str | `{patient_id}_{eeg_datetime}` | recording key |
| `patient_id` | str | = legacy `bdsp_id` | person key (spans this patient's EEGs) |
| `eeg_datetime` | str | `YYYYMMDDHHMMSS` | recording start |
| `src` | category | `cohort`,`expansion` | provenance (never inferred from filename) |
| `panel` | bool | | True if in a multi-rater expert set (SAP §3.6) |
| `panel_set` | category | `none`,`occasionnoise`,`moe` | which expert panel |
| `age` | float32 | years | age at recording (fractional where available) |
| `sex` | category | `F`,`M`,`unknown` | recorded sex (norms pool sexes; SAP §6.2) |
| `source_edf` | str | | the EXACT source pulled (BIDS session path or panel source_path) — provenance |
| `resolve_reason` | category | `single`,`sec-match`,`day-match`,`edf_direct`,`mat_v73` | how the EDF was resolved (scripts/31 `decide_edf`) |
| `sha256` | str | | integrity hash of the analyzed source file (B2) |
| `n_bytes` | int64 | | size of the analyzed source file |
| `recording_seconds` | float32 | s | analyzed duration (≤ 24 h cap) |
| `n_segments` | int32 | | total segments |
| `n_artifact` | int32 | | segments with `artifact_flag=True` |
| `n_usable` | int32 | | `n_segments − n_artifact` |
| `usable_fraction` | float32 | 0–1 | n_usable / n_segments |
| `stage_frac` | struct | | segment-weighted stage fractions (`frac_W`…`frac_REM`) |
| `p_slowing_coverage` | float32 | 0–1 | fraction of segments with a non-null gate `p_slowing` |
| `p_focal` | float32 | 0–1 | **EEG-level** Morgoth gate: P(focal) — one value per recording |
| `p_generalized` | float32 | 0–1 | **EEG-level** Morgoth gate: P(generalized) |
| `code_commit` | str | | git short SHA of the worker that produced the row |
| `clean_normal` | bool | | report normal AND no abnormal flags (norm-fit set) |
| `is_abnormal` | bool | | any abnormal finding in report |
| `clean_pair` | bool | | report↔EEG pairing unambiguous (SAP §3.3) |
| `processed` | bool | | a `.done` sidecar exists (featurized successfully) |
| `included` | bool | | processed AND passes usability (SAP §3.2: ≥5 min, ≥20 usable seg, ≥0.20 usable frac) |
| `exclusion_reason` | category | `noedf`,`ambiguous:NofM`,`nopanelfile`,`error:*`,`unusable:short_or_artifact`,`not_processed` | if `included=False` |

---

## 3. `recording_labels` — one row per EEG (report-derived)

Read from the PHI-safe scratchpad extract only (SAP §11). All label-dependent analyses filter `clean_pair`.

| column | type | allowed | definition |
|---|---|---|---|
| `eeg_id` | str | | recording key |
| `has_focal_slow` | bool | | report asserts focal slowing (negation-handled) |
| `has_gen_slow` | bool | | report asserts generalized slowing |
| `focal_side` | category | `left`,`right`,`bilateral`,`na` | focal laterality |
| `focal_region` | category | `frontal`,`temporal`,`central`,`parietal`,`occipital`,`na` | focal lobe |
| `focal_band` | category | `delta`,`theta`,`mixed`,`na` | focal band word |
| `gen_band` | category | `delta`,`theta`,`mixed`,`na` | generalized band word |
| `gen_topography` | category | `anterior`,`posterior`,`unspecified`,`na` | generalized predominance |
| `gen_state` | category | `awake`,`sleep`,`unspecified`,`na` | state in which reported |
| `gen_class` | category | project label set | generalized subtype |
| `report_stratum` | category | project label set | ordinal report-severity stratum (dose-response only; NOT a severity claim) |

---

## 4. `panel_votes` — one row per (panel EEG × rater × axis) [SAP §3.6, §8.3]

The expert-panel scores that supply inter-rater reliability and the human ceiling. Rater ids anonymized.

| column | type | allowed | definition |
|---|---|---|---|
| `eeg_id` | str | | panel recording key (join to `recording_meta` where `panel=True`) |
| `panel_set` | category | `occasionnoise`,`moe` | which panel |
| `rater` | category | `R01`…`Rnn` | anonymized rater (author `bwestove`→flagged, excluded from validation) |
| `read` | category | `I`,`II` | OccasionNoise re-read part (within-rater); `I` elsewhere |
| `axis` | category | `presence`,`focal`,`generalized`,`band`,`side`,`topography` | scored axis |
| `value` | category | axis-specific (e.g. band δ/θ/α/β) | the rater's call |
| `consensus_value` | category | | panel majority/adjudicated value for that EEG×axis |
| `consensus_prop` | float32 | 0–1 | fraction of raters positive (graded conspicuity target) |

---

## 5. Controlled vocabularies

**Regions — 6 aggregates:** `whole_head`, `L_temporal`, `R_temporal`, `L_parasagittal`,
`R_parasagittal`, `midline`.
**Regions — 18 bipolar channels (double banana):** `Fp1-F7`,`F7-T3`,`T3-T5`,`T5-O1`,
`Fp2-F8`,`F8-T4`,`T4-T6`,`T6-O2`,`Fp1-F3`,`F3-C3`,`C3-P3`,`P3-O1`,`Fp2-F4`,`F4-C4`,`C4-P4`,`P4-O2`,
`Fz-Cz`,`Cz-Pz`.
**Stages:** `W`,`N1`,`N2`,`N3`,`REM`. **Features:** `log_{delta,theta,alpha,beta,gamma,total}`,
`rel_{delta,theta,alpha}`, `log_DAR`,`log_TAR`,`log_DTR`,`low_freq_rel`.

---

## 6. `norms` — fitted normative model (GAMLSS/BCT)

One row per **(stage, region, feature, age_grid, fold)**; evaluated on a standard age grid for lookup (the
fitted smooth model stored alongside for continuous evaluation).

| column | type | definition |
|---|---|---|
| `stage` | category | W/N1/N2/N3/REM |
| `region` | category | region/channel |
| `feature` | category | feature name (e.g. `TAR`) |
| `age` | float32 | age grid point (years) |
| `mu` | float32 | BCT location |
| `sigma` | float32 | BCT scale |
| `nu` | float32 | BCT skew (λ) |
| `tau` | float32 | BCT df (kurtosis) |
| `n_fit` | int32 | clean-normal recordings contributing at this stage/region |
| `fold` | int8 | cross-fit fold id (norms are out-of-fold; SAP §6.3) |

---

## 7. `deviation_field` — materialized z (per segment × region × feature)

Grain: one row per **(eeg_id, segment, region, feature)** (long). Derived from `segment_master` + `norms`;
materialized for speed. Same partitioning as `segment_master`.

| column | type | definition |
|---|---|---|
| `eeg_id`,`segment`,`region` | | keys (join to `segment_master`) |
| `feature` | category | feature name |
| `z` | float32 | BCT z-score vs age/stage/region-matched normals |
| `centile` | float32 | 0–100, Φ(z)·100 |

---

## 8. `descriptors` — system description outputs (one row per EEG)

What the sentence generator reads (SAP §7.2, §7.4). Report-derived labels live in `recording_labels`
(§3); this table is our *measured* description. Report side vs predicted side are compared, never merged.

| column | type | allowed | definition |
|---|---|---|---|
| `eeg_id` | str | | recording key |
| `gate_focal`,`gate_generalized`,`gate_slowing` | float32 | 0–1 | pooled per-recording gate probs |
| `amount_sd` | float32 | SD | amount score `S` (age/stage-normed), max-alert stage |
| `amount_centile` | float32 | 0–100 | Φ(amount_sd)·100 |
| `band_call` | category | `delta`,`theta`,`mixed` | low-confidence band (PROVISIONAL) |
| `pred_focal_side` | category | `left`,`right`,`bilateral`,`none` | our predicted side from signed L−R deviation / pdBSI / Q_ASYM (§7.4) |
| `side_margin` | float32 | SD | pooled L−R lateralized excess (sign = side; magnitude = confidence) |
| `pred_region` | category | frontal/temporal/central/parietal/occipital/na | max-deviation lobe (PROVISIONAL) |
| `ap_topography` | category | `anterior`,`posterior`,`diffuse` | generalized A–P call (Q_APG) |
| `prevalence` | float32 | 0–1 | fraction of alert-stage segments over the normal centile |
| `persistence_min` | float32 | min | longest run of abnormal segments |
| `sleep_only` | bool | | slowing present only in sleep stages |
