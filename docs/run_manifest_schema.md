# Run manifest — the frozen EEG list

The **single source of truth for "which EEGs are in the run."** The clean-room fleet run
(`docs/analysis_plan.md` §12) consumes exactly this manifest and nothing else: every recording it names is
pulled to the bucket and put through the identical pipeline; no recording outside it is analyzed, and no
prior computation is reused. Freezing the manifest is build-order step 2; it is committed and tagged
alongside the code version used for the run.

## File

`data/manifest/run_manifest_v<N>.csv` (one row per recording). A companion
`run_manifest_v<N>.meta.json` records the freeze: `{version, frozen_utc, code_git_tag, n_recordings,
counts_by_src, counts_by_panel_set, sha256_of_csv}`. Bump `<N>` for any change; never edit a frozen
manifest in place (that is the whole point).

## Columns

| column | type | allowed | definition |
|---|---|---|---|
| `bdsp_id` | str | site+patient+date | recording id; primary key, joins to all canonical tables |
| `patient_id` | str | | patient key (dedup / patient-clustered CIs) |
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
| `notes` | str | | free text (e.g. conversion, known issues) |

`age`/`sex` are **not** in the manifest — they are read at run time (EDF header / OMOP birth date) and
land in `recording_meta`. Inclusion/exclusion (`included`, `exclusion_reason`) is decided **during** the
run and recorded in `recording_meta`, not pre-baked here: the manifest lists candidate EEGs; the run
records which passed. This keeps "what we tried to analyze" and "what qualified" as separate, auditable facts.

## Example (illustrative)

```csv
bdsp_id,patient_id,src,panel,panel_set,role,source_uri,bucket_key,format,n_bytes,sha256,expected_fs_hz,notes
S0001111192519_20150613113205,S0001111192519,cohort,false,none,normal_ref,s3://…/raw/….edf,s3://run-bucket/edf/….edf,edf,124518400,3a7f…,200,
S0002220034411_20180922084500,S0002220034411,expansion,false,none,abnormal,s3://…/raw/….edf,s3://run-bucket/edf/….edf,edf,98230272,9c1b…,200,
ON_0007,ON_0007,cohort,true,occasionnoise,panel,box:OccasionNoise/….edf,s3://run-bucket/edf/….edf,edf,60129542,f42a…,200,18-expert panel; Part I/II re-read
```

## Build & freeze checklist

1. Enumerate candidates: `cohort` + `expansion` recordings (SAP §3.1) and the `panel` EEGs
   (OccasionNoise + MoE, `icare_*` excluded; SAP §3.6).
2. Resolve `source_uri` for each; verify reachable; record `n_bytes` + `sha256`.
3. Assign `bucket_key`; the pull step copies `source_uri`→`bucket_key` and re-verifies `sha256`.
4. Write `run_manifest_v<N>.csv` + `.meta.json`; commit; tag the code (`git tag run-v<N>`).
5. From here, the fleet reads only `bucket_key`s in this manifest. Any add/remove = new version.

## PHI note

`bdsp_id` embeds a real recording date. Treat the manifest with the same care as the other tracked
derived tables (which already contain `bdsp_id`): it stays in-repo for reproducibility, but the
report-text/date-shift/viewer rules of SAP §11 still bind — no raw report text, no identified dates
beyond `bdsp_id`, crosswalks to any opaque `case_id` live only in the scratchpad.
