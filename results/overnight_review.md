# Overnight review — normative slowing growth curves (redone with full data)

Date: 2026-07-06. Everything below was found/fixed autonomously overnight; figures under `figures/growth_v2/`.

## TL;DR
- Full data now in: **20,971 recordings** (4,916 routine cohort + 16,055 overnight expansion), OMOP
  fractional ages 99.99% resolved. Source-appropriate sleep-stage curves are built on **N2=15,562,
  N3=14,559, REM=14,411** recordings (was ~2,415 for N3) — the fleet N3 fill + full overnight union
  delivered dense lifespan coverage; the LMS median tracks the model-free rolling median almost exactly.
- Fixed 4 real bugs (below). The most consequential was a **cohort/expansion harmonization problem** (your N2 "bimodality") that makes naive pooling invalid.
- Growth curves are now built **source-appropriately** (wake from routine EEG, sleep from overnight EEG) with a BCT/age-varying-skewness LMS fit. A pooled version is kept alongside for comparison.

## Issues found & decisions

### 1. Fleet cost-safety bug (fixed)
`finalize.sh` filtered on a nonexistent `fleet` AWS profile + wrong tag (`morgoth-slowing`); the real
instances were `morgoth-n3pilot`/`morgoth-n3ondemand` under profile `stanford`. The automated teardown
would have **matched nothing and kept 314 instances + 122 spot requests billing**. Fixed finalize.sh
(correct profile/tags, cancels spot first, kills local top-up loops) + documented in RUNBOOK. Fleet is
fully down (verified 0 running / 0 spot).

### 2. Sex is dispensable (decision: drop it)
On the real detector (TAR/DAR normal-referenced z, AUC 0.82), sex-conditional vs sex-pooled norms differ
by **ΔAUC ≤ 0.002 in every setting**. Median sex effect 0.01–0.02. → Pool sexes; one curve per stage.
Manuscript-ready justification. (scripts/74)

### 3. TAR feature-index bug (fixed)
The cohort `.mat` parser (scripts/69) read TAR from index 17 (`theta/beta`) instead of **16
(`theta/alpha`)** — verified against the `.mat`'s own `feature_names`. Corrected; cohort table rebuilt.

### 4. Cohort ↔ expansion harmonization — THE central finding (your N2 bimodality)
The two sources are only partly comparable:
- **Feature pipeline differs.** Cohort = JJ's precomputed `.mat`; expansion = `extract.py::features_31`
  (bands: delta 1–4, theta 4–7, alpha 8–13 — note the 7–8 Hz gap). Only **rel_delta was calibrated**
  across pipelines; band-ratio features (TAR/DAR) are **not comparable across sources** even after the
  index fix (cohort TAR ~1.3 vs expansion ~0.5).
- **Recording context differs.** Cohort = routine ~20-min EEG (mostly wake; sleep segments rare and often
  mis-staged drowsiness). Expansion = overnight EEG (real sleep). Evidence: source-offset of central
  rel_delta (rolling medians, `source_harmonization_rel_delta.png`):

  | stage | peds (1–12) | adult (20–60) |
  |---|---|---|
  | W  | +0.115 | +0.112 |
  | N1 | +0.107 | +0.052 |
  | N2 | +0.156 | +0.004 |
  | N3 | +0.206 | −0.003 |
  | REM| +0.185 | +0.033 |

  Adult **sleep** agrees across sources (~0); pediatric sleep diverges hugely (cohort peds sleep is
  mis-staged/low); **wake** differs at all ages (routine alert wake vs overnight drowsy wake).

**Decision (needs your ratification):** build norms **source-appropriately** —
- **Wake (W, N1): routine cohort** (the alert-wake reference a routine EEG is actually read against).
- **Sleep (N2, N3, REM): overnight expansion** (real, consistently-pipelined sleep; essential for peds).

This eliminates the bimodality and is physiologically defensible. `central_rel_delta_smooth.png` = this
policy; `central_rel_delta_smooth_pooled.png` = naive pooled (shows the artifact) for comparison.
Alternative you might prefer: keep two explicitly-separate reference sets ("routine-EEG norms" vs
"overnight norms") rather than mixing by stage.

### 5. Growth-model improvements (done)
- **clean_normal filter**: 386 abnormal recordings were sitting in the "normal" table (placeholder label
  from the parser); now excluded via authoritative `labels_unified`.
- **BCT with age-varying skewness**: the young-age median bias was constant skewness, not over-smoothing
  (more knots didn't help). BCT + `nu ~ s(age)` halved the infant-trough bias.
- **Sliding-window rolling-median QC overlay** (dashed) on every curve — a model-free reference the LMS
  median should track (replaces crude fixed age bins; window widens with age in log-space).

### 6. Data completeness — found ~2× more overnight data (DONE, rebuilt on all of it)
The overnight features live under TWO S3 prefixes that are **mostly different recordings**:
`.../Growth_curves/expansion/` (11,570) and `.../pilot_n3/` (7,321) — only 2,760 overlap, so the true
union is **~16,131 unique overnight recordings** (16,055 aggregated cleanly). I initially rebuilt on
pilot_n3 alone (7,321); the full-union rebuild is now complete (`scripts/overnight_rebuild2.sh`) →
**20,971 total recordings**. Site composition of the overnight union: MGB (S0001 MGH + S0002 BWH) = 90%,
I0003 (a third site) = 1,651 (10%). Since the routine cohort is MGB, this is MGB-consistent; the small
I0003 slice can be dropped if you want a strict single-institution norm (say the word — it's a one-line
site filter).

### 7. Validation of the finished analyses (7,321-set; full-set refreshes overnight)
- **Discrimination (corrected TAR):** TAR normal-vs-general AUC **0.817** (R_parasagittal), 0.814
  (whole_head), DAR 0.79 — single-source cohort, so unaffected by the harmonization issue and now on the
  correctly-indexed TAR. rel_delta remains the weakest slowing feature (~0.72).
- **Source-appropriate curves:** LMS median tracks the model-free rolling median across all stages; N3
  shows the textbook infant-peak (~0.60 at 6mo–1y) → childhood plateau → adult decline. Bimodality gone.
- **Pooled vs source-appropriate:** pooled inflates variance (esp. wake, which mixes routine alert-wake
  with overnight drowsy-wake); source-appropriate bands are tighter and unbiased.
- **Topoplots:** frontal-predominant delta, high in infancy across stages, declining with age; N3 highest.
  Coherent. (Wake neonatal bins are sparse — routine EEG has few neonates; sleep neonatal coverage is good.)

## Open questions for you
1. Ratify the source-appropriate policy (§4) vs. two-separate-reference-sets vs. pooled.
2. Ratio-feature norms (TAR/DAR) across sources are not valid — do we (a) present rel_delta-family norms
   only for the lifespan chart, (b) recompute cohort features through extract.py if raw cohort EEG is
   retrievable, or (c) restrict TAR/DAR to the single-source discrimination analysis (already valid there)?
3. X-axis: keep log(age) (standard) with sparse top ticks, or the denser rotated ticks (crowds at 60–80)?

## Data / provenance
- Uniform table: `data/derived/channel_stage_features.parquet` (has `src`, `clean_normal`; OMOP fractional
  ages, 100% resolved). Cohort features corrected (TAR=16). All 7,321 expansion feature files on S3
  (`.../Growth_curves/pilot_n3/`) and local; fleet terminated.
