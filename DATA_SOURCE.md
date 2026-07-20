# Data source & provenance

This project follows the BDSP **two-tier data** model: the **raw/source** recordings stay in their
canonical published home and are *referenced* here (not re-uploaded); the **derived** artifacts that the
figures/tables are computed from live in this project's credentialed S3 prefix, with the small proximal
artifacts committed in-repo.

## 1. Raw / source data (referenced, not re-hosted)

| what | where | how to get it |
|---|---|---|
| **Source EEG recordings** (continuous, BIDS) | `s3://bdsp-opendata-repository/EEG/bids/` — the published **BDSP EEG** dataset | credentialed access via bdsp.io; paths resolve from `source_subject_dir` / `resolved_path` in the report manifest (below). Example: `s3:bdsp-opendata-repository/EEG/bids/S0001/sub-S0001111192519/` |
| **De-identified clinical reports** | committed: `data/manifest/report_manifest_v6.parquet` (one row per recording: `eeg_id`, `report_impression`, `report_text`, `resolved_path`, structured labels) | in this repo. Report free text is **de-identified** (surrogate `S####…` IDs, shifted dates) per BDSP policy — DUA-governed, not PHI |

Cohort: **27,524 recordings / 23,543 patients** in the report manifest; the analysed clean-paired
report cohort and the ON-100 / SAI-100 evaluation sets are described in the manuscript (§2).

## 2. Derived data (this project's credentialed prefix)

`s3://bdsp-opendata-credentialed/morgoth-slowing/`

| prefix | contents | size |
|---|---|---|
| `derived/` | the reproduce cache: `segment_master/` (per-segment × per-channel band powers, hive-partitioned by `eeg_id`), `segment_deviation/` (per-segment age/stage-matched z field), `description_recording.parquet` + `description_stage.parquet`, `single_model_segfeats.parquet`, `occasion_*.parquet`, `grid_norm.json` (GAMLSS norm grids), gate tables | ~72 GB |
| `panels/` | ON-100 expert-panel inputs / votes | ~2.5 GB |

Locally these mirror `data/derived/` (git-ignored; pull with `aws s3 sync`, see `REPRODUCE.md`).

## 3. Raw → derived pipeline (how the derived data was produced)

Documented and driven by [`scripts/reproduce_story.sh`](scripts/reproduce_story.sh) (tier `scratch` = from raw):

1. **Stage + extract** (`scripts/31,32`, the GPU "fleet") — re-montage 10-20 → 18 bipolar channels,
   0.5 Hz HP + notch, 15-s windows, multitaper PSD → band powers/ratios per channel; **sleep stage**
   from the morgoth2 5-class stager → `segment_master/`.
2. **Normative curves** (`scripts/115`, R/GAMLSS) — lifespan × sleep-stage norms per region×feature →
   `grid_norm.json`; **per-segment deviation** (`scripts/43`) → `segment_deviation/`.
3. **Descriptors** (`scripts/56`) → `description_recording/stage`; **single-model features**
   (`scripts/53`); **panel inputs + Morgoth gate** (`scripts/107,36`).

Every figure/table then regenerates from these derived tables — see [`REPRODUCE.md`](REPRODUCE.md).

## 4. De-identification status

De-identified, **not PHI**: subject IDs are BDSP surrogates (`S0001…`), dates are shifted (intervals
preserved). The data is **DUA-governed** — its canonical home is the credentialed bucket; this repo
references it. Committed proximal artifacts (report manifest, findings CSVs, result tables) carry only
surrogate IDs and de-identified report text.

- **bdsp.io project:** _<slug> — set on publication_
- **GitHub:** https://github.com/bdsp-core/morgoth-slowing-growth-curves
