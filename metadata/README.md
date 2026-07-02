# Cohort metadata

`cohort_metadata.csv` — one row per Growth_curves recording; enough to regenerate **Table 1** and the
**growth curves** without re-reading S3. Rebuild with `python scripts/build_cohort_metadata.py`.

| column | meaning |
|---|---|
| `bdsp_id` | BDSP patient id (= OMOP `person_id`), from the filename |
| `session` | session tag if present (`ses-N`), else blank |
| `eeg_datetime` | EEG recording datetime `YYYYMMDDHHMMSS`, from the filename |
| `label` | `normal` (control) / `focal_slow` / `general_slow` (folder = class) |
| `age` | age in years, embedded in the `.mat` file |
| `age_valid` | False for implausible ages (<0 or >120) — 18 rows |
| `sex` | M/F from OMOP `gender_concept_id` (resolved 12,378/12,379) |

De-identified BDSP research ids only. `bdsp_id` = `"S000<site>"` + OMOP `person_id`. To refresh:
`python scripts/07_pull_sex_omop.py && python scripts/build_cohort_metadata.py && python scripts/make_table1.py`.
