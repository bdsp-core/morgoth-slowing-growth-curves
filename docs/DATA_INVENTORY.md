# Data inventory & canonical spec

**Purpose.** One place that says, for every data table: what grain it is, what it covers,
where it came from, and whether it is CANONICAL, a DERIVED VIEW, or LEGACY (archive/delete).
This exists because we kept losing track of which table we were working with. If you add a
table, add a row here in the same commit, or it does not exist.

**Companion docs.** `docs/analysis_plan.md` (the SAP — how the canonical data is built and analyzed),
`docs/data_dictionary.md` (column-level definitions of the canonical tables),
`docs/run_manifest_schema.md` (the frozen "which EEGs" list format),
`docs/legacy_growth_curves_matformat.md` (the retired `.mat` source format).

Last audited: 2026-07-10.

---

## 0. The three axes that distinguish our tables

Every feature table differs on **three independent axes** at once. Confusion comes from assuming
two tables match on all three because they share feature *columns* (they never do):

| Axis | Possible values |
|---|---|
| **Grain** | per-segment · per-(recording,region,stage) aggregate · per-recording |
| **Coverage** | first-600 s only (legacy .mat) · whole recording (fleet) |
| **Cohort** | cohort only (~12k) · cohort+expansion (~27k) |
| **Spatial unit** | 6 region aggregates · 18 bipolar channels · both (24) |

A segment is **15 s** (3000 samples @ 200 Hz), step **14 s** (1 s overlap). NOT 10 s.

---

## 1. The two tables people confuse (they overlap on NOTHING but column names)

| | `segment_features.parquet` | `channel_stage_features.parquet` |
|---|---|---|
| **Role** | DESCRIPTION (how much / where / band) | DETECTION (normal vs abnormal) |
| **Grain** | per-segment | per-(recording, region, stage) **aggregate** |
| **Coverage** | **first 600 s only** (exactly 42 seg/rec) | **whole recording** (up to 43 h) |
| **Cohort** | cohort only (12,027 rec) | cohort+expansion (27,022 rec) |
| **Spatial** | 6 region aggregates only | 18 channels + 6 regions (24) |
| **Stages** | no (join `segment_stages`) | yes (stage is a key) |
| **Provenance** | legacy Growth_curves `.mat` extract | the fleet (`scripts/30_ingest_worker.py`) |

They are NOT two versions of one thing. Neither is a superset of the other. You cannot get
per-segment whole-recording data from either.

---

## 2. Canonical tables (use these)

| File | Grain | Coverage | Cohort | Notes |
|---|---|---|---|---|
| `channel_stage_features.parquet` | (rec,region,stage) agg | whole | 27k | DETECTION source of truth. `src`, `clean_normal`, `is_abnormal`, `age`, `sex`. 20,900 clean-normal / 5,559 abnormal. |
| `segment_features.parquet` | per-segment | first-600s | 12k | DESCRIPTION source (prevalence/persistence need per-segment). Flat segments stripped. |
| `segment_stages.parquet` (normals) + `segment_stages_abnormal.parquet` | per-segment | first-600s | 5k+7k | W/N1/N2/N3/REM per segment. Join to `segment_features`. |
| `labels_unified.parquet` | per-recording | — | 12k | Report-derived labels: focal/gen, band, side, topography, gen_class. |
| `gate_probs.parquet` | per-recording | whole | **12k (cohort only!)** | Morgoth gate: p_abnormal/focal/generalized/slowing. **Per-recording only — no per-segment, no expansion.** |

## 3. Derived views (rebuildable; keep but they are not sources)

`recording_features.parquet` (rec×region agg, cohort), `stage_recording_features*.parquet`
(rec×region×stage agg), `cohort_channel_stage.parquet` (cohort slice of channel_stage),
`description_descriptors.parquet`, `adjusted_z.parquet`, `growth_curves.parquet`,
`stage_curves.parquet`, `scores_v2.parquet`, `discrimination.parquet`, the v4a_* set, the
gen_* set, `fractional_age.parquet`, `bsi_features.parquet`, `occasion_*`, `report_*`.

## 4. LEGACY / redundant

The `_py` suffix was a **migration alias**: when features moved from MATLAB (JJ-derived) to the Python
extractor, the Python outputs were written as `*_py.parquet` to sit beside the MATLAB ones "until
validated, then swap" (scripts/13 docstring). The swap half-happened — script 51 wrote *both* names and
half the code read each — which is exactly the split-brain that caused confusion. **Retired 2026-07:**
the `_py` copies were byte-identical, so all readers were repointed to the canonical name and the copies
deleted.

| File | Action | Status |
|---|---|---|
| `recording_features_py.parquet` | delete; readers → `recording_features.parquet` | ✅ done |
| `recording_asymmetry_py.parquet` | delete; readers → `recording_asymmetry.parquet` | ✅ done |
| `segment_features.PREFLATSTRIP.parquet` | archive (gitignored; not in repo) | pre-flat-strip backup, unreferenced |
| `stage_recording_features_cohort.parquet` | fold into `stage_recording_features` at the rebuild | still read by scripts/65; deferred to avoid breakage |

---

## 5. What the canonical spec WANTS but we do NOT yet have

The target is one per-segment table over the **whole** recording, with stage + artifact flag +
all features + Morgoth, for all 27k recordings. Gaps:

1. **Per-segment features over the whole recording.** `segment_features` stops at 600 s; the
   fleet computed whole-recording features but saved only the (region,stage) *aggregate*.
2. **Per-segment Morgoth (focal/generalized).** `gate_probs` is per-recording and cohort-only.
   The fleet ran Morgoth on windows but persisted only the recording-level summary.
3. **Per-segment artifact flags stored alongside.** Flat/artifact segments are *stripped*, not
   *flagged* — so downstream cannot see which segments were dropped or why.
4. **One spatial grain decided.** Per-segment × per-channel × whole-recording × 27k ≈ 1.4 B rows
   (hundreds of GB) — not a single parquet. Must choose region-grain default (~470 M rows,
   partitionable) vs channel-grain, and a partitioned physical layout (one file per recording).
5. **A recording-level key.** ⚠ `bdsp_id` is **patient-level** (site+person, e.g. `S0001111192519`) —
   the date lives in a separate `eeg_datetime`, and one `bdsp_id` already maps to up to 3 EEGs. Legacy
   tables keyed on `bdsp_id` therefore *collapse* a patient's multiple recordings. The canonical run keys
   on **`eeg_id` = `{patient_id}_{eeg_datetime}`** (one row per EEG), with `patient_id` (= legacy
   `bdsp_id`) carried for patient-clustered CIs. Verified 2026-07-10.

See `docs/analysis_plan.md` §5 (`data_dictionary.md`, `run_manifest_schema.md`) for the canonical
`eeg_id`-keyed schema and the fleet re-run that closes 1–5.
