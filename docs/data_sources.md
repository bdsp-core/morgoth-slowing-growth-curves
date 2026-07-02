# Data Sources & Access

All data lives on AWS S3 in the **credentialed** BDSP open-data bucket
`bdsp-opendata-credentialed`. Access requires BDSP AWS keys (see the BDSP AWS-keys instructions in
Box: `Brandon - PHI/@@AWS-keys-instructions`).

## Paths

| Purpose | S3 path |
|---|---|
| Normative feature set (build growth curves) | `s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/` |
| Focal-slowing example cases | `s3://bdsp-opendata-credentialed/morgoth1/data/internal_dataset/FOCALSLOWING/` |
| Generalized-slowing example cases | `s3://bdsp-opendata-credentialed/morgoth1/data/internal_dataset/GENSLOWING/` |

## One-time setup

**Option A — AWS CLI**
```bash
# install (macOS, no admin): via the official pkg, or pipx install awscli
aws configure    # enter BDSP access key / secret / region
# inventory + size (do this FIRST — resolves the disk-space question)
aws s3 ls --recursive --human-readable --summarize \
  s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/
```

**Option B — rclone** (already installed at `~/.local/bin/rclone`; a `box:` remote exists)
```bash
rclone config    # create an s3 remote, e.g. name it "bdsp", provider AWS, with the BDSP keys
rclone size   bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves
rclone lsf -R bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves | head
# pull to local cache:
rclone copy bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves \
  ./data/raw/Growth_curves --progress
```

## To fill in after Phase 0 (data inventory)

- [ ] Total size of each path (→ confirms disk plan; see PLAN.md §7)
- [ ] File format(s): precomputed features (parquet/npz/csv) vs. raw/BIDS EEG
- [ ] Is sleep staging already present per 15-s segment?
- [ ] Is a normal/abnormal (and focal/generalized) label present, and where?
- [ ] Demographics available: age, sex (required for growth curves)
- [ ] Data dictionary — columns/fields and units

## Local cache convention

- `data/raw/`      — pulled S3 mirrors (gitignored)
- `data/derived/`  — features, cohort tables, fitted models (gitignored)
- `data/.gitkeep`  — keeps the dir; everything else here is ignored
