# Run manifest — the frozen EEG list

The **single source of truth for "which EEGs are in the run."** The clean-room fleet run
(`docs/analysis_plan.md` §13) consumes exactly this manifest and nothing else: every recording it names is
pulled to the bucket and put through the identical pipeline; no recording outside it is analyzed, and no
prior computation is reused. Freezing the manifest is build-order step 2; it is committed and tagged
alongside the code version used for the run.

## File

`data/manifest/report_manifest_v<N>.parquet` (one row per recording). A companion
`report_manifest_v<N>.meta.json` records the freeze: `{version, frozen_utc, n_v6, counts_by_src, held_N,
every_bids_row_resolved, replacements_analysis_ready, sha256}`. Bump `<N>` for any change; never edit a
frozen manifest in place. The manifest parquet/json are gitignored (`data/*`); the freeze is pinned by
the **tracked manifest index** `docs/run_manifest_index.md` (version + sha256 + composition + S3 location)
so a code tag reconstructs the exact starting point.

## Realized manifest (2026-07-11): **`report_manifest_v6.parquet` = the LAUNCH manifest** (v5 = pre-resolution)

Pipeline: `scripts/120` → `88` (pairing) → `121` (backfill) → `124` (merge) → `125` (routing) → `126`
(expansion) → `127` (panels) → **`129` (pre-flight resolve)** → **`130` (drop-and-replace → v6)**.
**v6 = 27,524 EEGs**, `held_N:true`, `every_bids_row_resolved:true`: cohort 10,977 + expansion 10,233 +
backfill 2,535 + **replacement 1,918** (fresh resolvable rows that replaced the 1,918 unresolvable v5 rows,
fully labeled+aged) + **panel 1,861** (OccasionNoise 100 + MoE 1,761). v5 was 27,524 before pre-flight. Panels carry `source_type` (edf_direct / mat_v73) + a **relative**
`source_path` (`occasionnoise/<fid>.edf`, `moe/<event>.mat`) that the worker's `fetch_panel` resolves
against `PANEL_ROOT` (local dir or `s3://…`; staged/uploaded by `scripts/128` → fleet_launch.md §0b). Their
loaders (`src/morgoth_slowing/io/panels.py`) featurize them through the SAME worker path; they do NOT block
the main cohort run. Built by `scripts/{120,88,121,124,125,126}`. **Panels (OccasionNoise 100 + MoE)
are appended by `scripts/127`** — their source files live in the scratchpad (OccasionNoise `moe/occ/edf/`,
MoE `events_raw/`) until `scripts/128` stages them for upload. Schema-aligned columns present: `panel`, `panel_set`, `role`, `n_bytes`, `sha256`
(the last two stamped at pull). Carries the report
labels + de-identified text (§11) **and** the S3 routing the pull step needs:

| field | value | note |
|---|---|---|
| `source_subject_dir` | `s3:bdsp-opendata-repository/EEG/bids/{site}/sub-{bdsp_id}/` | verified to resolve |
| `bids_task` | `cEEG`/`rEEG`/`EMU`/`EEG`/`OR` | BIDS task |
| `report_session_id` | report-system `SessionID_new` | **≠ the BIDS `ses-N`** (sparse: e.g. ses-1,10,11,…) |
| `bucket_key` | `run-bucket/edf/{eeg_id}.edf` | deterministic destination |
| `n_bytes`, `sha256` | **null → stamped at pull** | see below |

**Exact-EDF resolution + integrity are pull-time by necessity.** The exact file is
`…/sub-{id}/ses-{N}/eeg/sub-{id}_ses-{N}_task-{task}_eeg.edf`, but the BIDS `ses-N` index is not the report
`SessionID_new`, so the pull step **lists `source_subject_dir`, matches the session by date, copies the EDF
to `bucket_key`, and stamps `n_bytes` (S3 metadata) + `sha256` (hashed while streaming)** — a hash cannot
exist before the file is fetched, so it is computed once, for free, during the copy. 76 EEGs with no
locatable subject/date were excluded.

## Columns

| column | type | allowed | definition |
|---|---|---|---|
| `eeg_id` | str | `{patient_id}_{eeg_datetime}` | **recording key** (unique per EEG); joins to all canonical tables |
| `patient_id` | str | site+person (= legacy `bdsp_id`) | patient key; one patient → many `eeg_id` (dedup / patient-clustered CIs) |
| `eeg_datetime` | str | `YYYYMMDDHHMMSS` | recording start; distinguishes a patient's EEGs |
| `src` | category | `cohort`,`expansion` | provenance cohort (SAP §3.1) |
| `panel` | bool | | in a multi-rater expert set? (SAP §3.6) |
| `panel_set` | category | `none`,`occasionnoise`,`moe` | which expert panel |
| `role` | category | `normal_ref`,`abnormal`,`unlabeled`,`panel` | intended analytic role (informational; labels are authoritative) |
| `source_uri` | str | `s3://…` / `box:…` | where to pull the raw EDF from |
| `bucket_key` | str | `s3://…bucket/…` | destination in the run bucket (where the fleet reads it) |
| `format` | category | `edf`,`edf+`,`other` | container; `other` requires a conversion note |
| `n_bytes` | int64 | | source file size (integrity) |
| `sha256` | str | 64-hex | source file hash (integrity + exact reproduction) |
| `expected_fs_hz` | float32 | | sanity check vs read (200 after resample) |
| `nearest_report_id` | str | | report paired to this EEG, computed up front (SAP §3.3) |
| `clean_pair` | bool | | report↔EEG pairing unambiguous; label analyses filter on this |
| `notes` | str | | free text (e.g. conversion, known issues) |

`age`/`sex` **are** in v6 (from `AgeAtVisit`/`SexDSC`; replacements carry them too, verified
`replacement_age_null:0`) — the run also re-reads/validates them into `recording_meta`.
Inclusion/exclusion (`included`, `exclusion_reason`) is decided **during** the run and recorded in
`recording_meta`, NOT pre-baked here: the manifest lists candidate EEGs (all provably resolvable); the run
records which passed usability. This keeps "what we tried to analyze" and "what qualified" separate and
auditable — a phantom-free candidate list up front, a usability verdict per EEG after.

## Example (illustrative)

```csv
eeg_id,patient_id,eeg_datetime,src,panel,panel_set,role,source_uri,bucket_key,format,n_bytes,sha256,expected_fs_hz,nearest_report_id,clean_pair,notes
S0001111192519_20150613113205,S0001111192519,20150613113205,cohort,false,none,normal_ref,s3://…/raw/….edf,s3://run-bucket/edf/….edf,edf,124518400,3a7f…,200,R_88213,true,
S0001111192519_20180922084500,S0001111192519,20180922084500,cohort,false,none,abnormal,s3://…/raw/….edf,s3://run-bucket/edf/….edf,edf,98230272,9c1b…,200,R_91007,true,same patient as row 1 — a SECOND EEG
ON_0007_20190104101500,ON_0007,20190104101500,cohort,true,occasionnoise,panel,box:OccasionNoise/….edf,s3://run-bucket/edf/….edf,edf,60129542,f42a…,200,,false,18-expert panel; Part I/II re-read
```

## Build & freeze checklist

1. Enumerate candidates: `cohort` + `expansion` recordings (SAP §3.1) and the `panel` EEGs
   (OccasionNoise + MoE, `icare_*` excluded; SAP §3.6). Each EEG is one `eeg_id` = `{patient_id}_{eeg_datetime}`.
2. **Compute the report↔EEG pairing up front** (nearest-in-time report per `eeg_id`; set
   `nearest_report_id` + `clean_pair`) and freeze it here — so labels are fixed before any analysis (SAP §3.3).
3. Resolve `source_uri` for each; verify reachable; record `n_bytes` + `sha256`.
4. Assign `bucket_key`; the pull step copies `source_uri`→`bucket_key` and re-verifies `sha256`.
5. Write `report_manifest_v<N>.parquet` + `.meta.json`; pin its sha256 in `docs/run_manifest_index.md`
   (tracked); commit; tag the code (`git tag run-v<N>`). For v6, pre-flight `scripts/129`→`130` runs first.
6. From here, the fleet reads only rows in this manifest (each with a resolved EDF). Any add/remove = new version.

## PHI note

`eeg_id` embeds a real recording date. Treat the manifest with the same care as the other tracked
derived tables (which already contain these ids): it stays in-repo for reproducibility, but the
report-text/date-shift/viewer rules of SAP §11 still bind — no raw report text, no identified dates
beyond `eeg_id`/`eeg_datetime`, crosswalks to any opaque `case_id` live only in the scratchpad.
