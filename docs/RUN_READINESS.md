# Run readiness — go / no-go for the full clean-room fleet run

Status board for the reviewer's blockers (2026-07-11 review) + the user's no-shrink manifest requirement.
Each item: what it was, what changed, and how it was verified. **Bottom line at the top.**

> **Bottom line (honest).** The **fleet compute path** (`scripts/31` featurize → `scripts/33` ledger →
> `scripts/32` verify) is ready and validated on real data; the schema is frozen (per-channel
> `segment_master` + `segment_summary` + run ledger). A 120-case, 2-shard pilot **processed 111/120, 89
> included** (9 unresolvable + 22 unusable — 20 of those are single-segment MoE by design), with correct
> physiology and shard-safety. Pre-flight resolved 92.5% of the manifest; `scripts/130` builds the
> KNOWN-GOOD `v6` (**confirmed: 27,524 = v5, `held_N:true`, `every_bids_row_resolved:true`,
> `replacement_age_null:0`** — every row provably resolves, N held, replacements fully labeled+aged).
>
> **NOT yet done before the full run:** the **downstream analysis scripts** (Tables/Figures/deviation_field)
> still read legacy `bdsp_id` tables — they are **post-fleet rebuilds** (they consume `segment_master`,
> which doesn't exist until the run). This is expected and scoped below, not a surprise. **Verdict: green to
> run the FLEET (featurize → ledger); the analysis layer is a separate, post-run rebuild.**

---

## Reviewer blockers

| # | Blocker | Fix | Verified |
|---|---|---|---|
| B1 | `resolve_edf` ignored `eeg_datetime` → could analyze the wrong EDF | `decide_edf` matches `eeg_datetime`→BIDS `scans.tsv` `acq_time` (sec-match → unique-day fallback); hard-fails `noedf`/`ambiguous:NofM`, never guesses | On the 9-session subject: date rows resolve to the right `ses-N`; 3 datetimes with no S3 EDF correctly refuse (old code would have taken a recording 10 yr off). Pilot log shows live `noedf` handling. |
| B2 | No integrity stamp | worker streams a `sha256` + `n_bytes` of the analyzed source into `.done`; surfaced in the ledger | `.done` inspected: `sha256`, `n_bytes` present for BIDS + panels |
| B3 | `DAR/TAR/DTR` were log-ratios named as ratios | renamed `log_DAR/log_TAR/log_DTR`; raw ratio kept as van Putten `ADR`; data_dictionary updated | pilot partitions carry `log_DAR`… + `ADR`; 24 tests pass; **no** column collision (verified) |
| B4 | full EDF loaded before the 24 h cap (OOM risk on long cEEG) | `load_edf_referential(max_hours=24)` reads only the first 24 h per channel and sizes the output to it | code path exercised; a 72 h cEEG now reads ≤24 h (≤13 GB) instead of ~39 GB |
| B5 | `recording_meta` thin + shard-unsafe (every shard rewrote a global parquet) | worker writes ONLY per-eeg sidecars; a SEPARATE `scripts/33` assembles the one-row-per-EEG ledger after shards finish | 2 concurrent shards write with no global-file contention; ledger built with full stats/provenance/outcome |
| B6 | downstream (107 etc.) still read legacy bdsp_id tables | canonical read path proven (`scripts/32` reads `segment_master`, derives regions via `to_regions`, joins summary + ledger); full downstream migration is the documented post-run step (it *consumes* run output) | `scripts/32` runs on pilot output → region table + figure |

## User requirement — no shrink

Some BIDS `eeg_id`s (datetime from report metadata) have **no EDF** on S3. **Fix:** pre-flight resolves every
BIDS row (`scripts/129`); `scripts/130` drops the unresolvable ones AND replaces each with a fresh, labeled,
resolvable candidate drawn from the report pool, so `report_manifest_v6` has **N ≥ v5**. Existence + unique
resolution is guaranteed pre-run; full *usability* (SAP §3.2) is confirmed post-run in the ledger and any
per-bin shortfall is topped up the same way.

---

## Pre-flight resolution (full v5)  — `scripts/129` → `scripts/130`
Resolved every BIDS row against S3 (21,757 subjects, ~1 h, 32 threads):

| | count | % |
|---|---|---|
| BIDS rows (v5) | 25,663 | |
| **resolved** | **23,745** | **92.5%** |
| — `single` (one candidate) | 13,628 | |
| — `sec-match` (exact datetime) | 6,066 | |
| — `day-match` (unique day) | 4,051 | |
| **dropped** | **1,918** | 7.5% |
| — `ambiguous` (multi-session, 0 or >1 date match) | 1,721 | |
| — `noedf` (no EDF of that task on S3) | 197 | |

The 7.5% drop is real (datetimes from report metadata with no matching EDF, or unresolvable multi-session).
The old resolver would have silently analyzed a wrong EDF for many of these. `manifest_rejects.parquet`
lists all 1,918.

**No-shrink v6 (confirmed):** `scripts/130` replaced all 1,918 drops with fresh, resolvable, labeled
candidates from the report pool:

| meta field | value |
|---|---|
| `n_v6` | **27,524** (= v5 — `held_N: true`) |
| composition | 23,745 resolved keepers + 1,918 replacements + 1,861 panels |
| `every_bids_row_resolved` | **true** (0 phantoms — every row maps to one real EDF) |
| `replacement_age_null` | **0** (age from `AgeAtVisit`) |
| `replacements_analysis_ready` | **true** (sex, clean_normal, focal/gen labels, clean_pair, report text all populated) |

`report_manifest_v6.parquet` is the launch manifest. Its `sha256` is pinned in the meta.json.

## Pilot (120 cases, 2 shards, gate on)  — `data/manifest/pilot_manifest.parquet`
Selection: 56 rEEG + 24 cEEG (31 clean_normal) across all age bins incl. 0–1 + 20 OccasionNoise + 20 MoE.
Ran as **2 concurrent shards** sharing `OUTPUT_ROOT` — no file clobber (shard-safety exercised for real).

**Outcomes (from the assembled ledger):** 120 intended → 111 processed, **89 included**, 31 excluded.
- 22 `unusable:short_or_artifact` — **20 are single-segment MoE** (expected; panel aim, not recording N) + 2 short/artifact-heavy BIDS.
- 8 `noedf` (unresolvable BIDS — correctly refused, ~10% consistent with the 7.5% full-manifest rate).
- 1 `error:TimeoutExpired` (an S3 pull/stage timeout — the worker recorded it and moved on; resumable).

**Scale:** `segment_master` = 1,069,056 channel-rows (18 ch/seg) over 59,392 segments; 42,431 usable
whole-head segments. `segment_summary` + ledger all populated. Every `.done` carries sha256 + stats.

**Physiology sanity (whole_head, usable — proves the whole featurize→region→gate path):**

| stage | n_seg | rel_delta | log_DAR | Q_SLOWING | p_slowing (gate) |
|---|--:|--:|--:|--:|--:|
| W | 8198 | 0.324 | 1.42 | 0.576 | 0.367 |
| N1 | 4415 | 0.390 | 1.88 | 0.681 | 0.671 |
| N2 | 13310 | 0.407 | 2.35 | 0.704 | 0.778 |
| N3 | 14259 | 0.448 | 3.03 | 0.803 | 0.941 |
| REM | 2249 | 0.394 | 1.78 | 0.693 | 0.413 |

Monotonic slowing with sleep depth (rel_delta, log_DAR, Q_SLOWING all rise W→N3) — textbook-correct. The
gate `p_slowing` rising W 0.37 → N3 0.94 re-confirms that **deep sleep looks like slowing to the detector**
→ vigilance-matched detection (routine-norm W/N1) is essential, as already established.

---

## Schema (frozen 2026-07-11)
- `segment_master` — per **(eeg_id, segment, channel)**, 18 bipolar channels; regions DERIVED (`to_regions`).
- `segment_summary` — per (eeg_id, segment): stage, artifact, `p_slowing`, whole-head van Putten.
- `recording_meta` (ledger) — per eeg_id: provenance (source_edf, sha256, resolve_reason), stats,
  EEG-level `p_focal`/`p_generalized`, outcome (processed / included / exclusion_reason).
- `recording_labels` — per eeg_id: report/panel labels.

## Run order (see `docs/fleet_launch.md`)
1. `scripts/129` → `scripts/130`  (pre-flight → `v6`, known-good, N held)
2. `scripts/128` + `aws s3 sync panels/`  (upload panel sources; set `PANEL_ROOT`)
3. `scripts/31` sharded  (featurize → per-eeg `segment_master` + `segment_summary` + sidecars)
4. `scripts/33`  (assemble the run ledger)
5. `scripts/32`  (verify) → norms → deviation_field → Tables/Figures; calibrate the gate (SAP §4.7)

## Downstream scripts — runs-now vs post-fleet (honest inventory)
Grep-audited 2026-07-11 (`load_segment_master`/`io.canonical` vs legacy `segment_features`/`bdsp_id`):

**Ready now (fleet + manifest path):**
- `scripts/129`/`130` pre-flight → v6 · `scripts/128` panel staging · `scripts/31` featurize ·
  `scripts/33` ledger · `scripts/32` verify/summary (reads canonical, derives regions) · manifest
  builders `120`–`127`. These are all that the FLEET run needs.

**Post-fleet rebuild (37 scripts — read legacy `bdsp_id` tables; must be repointed to `segment_master`
via `io/canonical.py` AFTER the run produces it):**
- deviation/norms: `107_deviation_field`, `76_keystone_growth_grid`, `gamlss_fit.R`
- descriptors/sentences: `108`, `110`, `113`, `111`
- detection/operating points: `84_vigilance_matched_detection`, `96_nested_cv_detection`, `112`, `103`/`104`
- tables/figures: `85_table1_and_dose_response`, `100`–`106`, `102_region_z_boxplots`, `105_two_stage_figure`
- van Putten benchmark: `47_vanputten_comparison`, `97_moe_band_vs_ours`
- panels/human-ceiling: `93`, `95`/`95b`, `98`
- **Why post-fleet, not now:** every one consumes `segment_master`/`deviation_field`, which don't exist
  until the run completes. They cannot be validated before the run; repointing them is the first task
  after the fleet output lands. `io/canonical.py` (+ `to_regions`) is the single seam they migrate to.

This is the "explicit post-fleet work" list the review asked for: **the run is not blocked on these**;
the final Tables/Figures are.

## Known / documented, not blockers
- Panel MoE rows are single-segment (human-ceiling aim) → correctly `unusable:short_or_artifact` under the
  recording-inclusion rule; they are NOT part of the norm/detection N and are not topped up.
- Flat/suppressed epochs (burst-suppression/disconnection) are flagged, common in abnormal recordings; a
  dedicated detector, not this pipeline, is the eventual home (per project note).
- Full migration of the ~36 downstream analysis scripts to the canonical tables is post-run work.
