# morgoth-slowing-growth-curves

Lifespan **× sleep-stage normative "growth curves"** for quantitative EEG **slowing**. A single per-segment
**deviation-from-normal field** both **detects** pathological slowing (focal vs generalized) — beating an
18-expert panel, a foundation-model gate, and the published van Putten qEEG lineage — and reads OUT a
governed, clinician-style **description**, validated against clinical EEG reports and the human inter-rater
ceiling. Part of the [bdsp-core](https://github.com/bdsp-core) automated-EEG effort.

> **Reproduce — three named tiers** (`bash scripts/reproduce_story.sh <tier>`; see
> [REPRODUCE.md](REPRODUCE.md)):
> - **`results`** (default, fast, minutes) — regenerate all figures/tables + the dashboard from the computed
>   derived tables. The iterate-on-publication-figures loop.
> - **`features`** (~1 h) — from the extracted features (`segment_master/`): rebuild the GAMLSS norms +
>   deviation field + descriptors, train the detectors, then produce all results. Needs R + `gamlss`.
> - **`scratch`** (~24 h) — from the raw source EDFs: run the fleet (Morgoth sleep staging + feature
>   extraction on S3), assemble the tables, then `features`. Needs BDSP S3 + the Morgoth env.
>
> The narrative write-up is the **story dashboard** (`results/story_dashboard.html`) and the manuscript
> ([docs/manuscript_draft.md](docs/manuscript_draft.md)).
>
> **Analysis plan → [docs/analysis_plan.md](docs/analysis_plan.md)** — the pre-registered SAP, the source of
> truth for how data is prepared, analyzed, and reported.

## The system

- **GATE (Morgoth foundation model): whether & what.** Presence of pathological slowing; focal vs
  generalized, per 15-s segment, pooled to the recording.
- **DESCRIBE (normative deviation field): how much / where / which band / how prevalent / which stage.**
  Features are z-scored against **age × sleep-stage × region**-matched clinician-normals (GAMLSS/LMS,
  sex-pooled). A measurement layer that never makes the categorical call.
- **Governance:** every reportable clause is ALLOWED / PROVISIONAL / FORBIDDEN in
  [docs/claims_table.md](docs/claims_table.md) (severity adjectives, ACNS frequency words, and
  band-from-our-features are forbidden output).

## Canonical facts (do not re-derive)

| | |
|---|---|
| Recording key | **`eeg_id` = `{patient_id}_{eeg_datetime}`** (one row per EEG, not per patient) |
| Segment | 15 s @ 200 Hz, 14 s step | Coverage | **up to the first 24 h** (never "first 600 s") |
| Bands | δ 1–4, **θ 4–8**, α 8–13, β 13–30, γ 30–45, total 0.5–45 Hz |
| Focal regions | frontal · temporal · central · **posterior** (occipital+parietal folded in) |
| Norms | stage-conditioned, **sex-pooled**; artifact segments **flagged, not stripped** |
| Build rule | **zero reuse** of prior derived tables — one clean fleet run from a frozen manifest |

## Governance / canonical docs

[docs/analysis_plan.md](docs/analysis_plan.md) (SAP) · [docs/DATA_INVENTORY.md](docs/DATA_INVENTORY.md) ·
[docs/data_dictionary.md](docs/data_dictionary.md) · [docs/run_manifest_schema.md](docs/run_manifest_schema.md) ·
[docs/claims_table.md](docs/claims_table.md) · [docs/description_architecture.md](docs/description_architecture.md).
Superseded material lives in [docs/archive/](docs/archive/) and [scripts/archive/](scripts/archive/) (retained
for provenance, never an input to the run).

## The frozen run manifest

`data/manifest/report_manifest_v6.parquet` — the KNOWN-GOOD EEG list the clean-room run ingests:
**≥27,524 EEGs** (cohort + expansion + backfill + OccasionNoise/MoE panels), report labels + de-identified
text + S3 routing. Built by `scripts/{120,88,121,124,125,126,127}`, then **pre-flight resolved**
(`scripts/129`) so every BIDS row provably maps to one real EDF, with unresolvable rows drop-and-replaced
(`scripts/130`, N held). Earlier drafts: v3 (14,957, cohort+backfill), v5 (27,524, +panels). Coverage:
[docs/coverage_report.md](docs/coverage_report.md). The analysis cohort after inclusion is **25,536
recordings / 21,757 patients** ([results/table1.md](results/table1.md)).

## Layout

```
docs/            governance (SAP + companions); docs/archive/ = superseded
src/morgoth_slowing/
  features/      extract.py (canonical extractor), recording, artifact
  io/            edf, staging (Morgoth sleep stager), omop
  fleet/         ingest.py — shared fleet-ingest helpers
  report/        parse.py — report NLP; phrase generation
  norms/ scoring/ viz/
scripts/         reproduce_story.sh = one-command rebuild; build_story_dashboard.py = dashboard;
                 fleet path: worker (31) + ledger (33) + verify (32) + pre-flight (129,130) + manifest
                 builders (120–128); analysis: norms/deviation (43,76,111,115,gamlss_*.R), detection
                 (49,53–55), description (56–58), benchmarks (recompute_vanputten_fullcov,
                 recompute_human_ceiling_v6)
data/manifest/   frozen run + report manifests
references/      van Putten qEEG sources (README + .bib; PDFs gitignored)
tests/
```

## Status

Findings are being hardened on the current (legacy) derived tables; the **one clean-room re-run** over the
frozen manifest produces the final numbers (SAP §12 code-review gate → §13 build order). Environment:
`PYTHONPATH=src`, `KMP_DUPLICATE_LIB_OK=TRUE`; the norms engine is R (GAMLSS, `scripts/gamlss_fit.R`).

## Data access

De-identified, DUA-governed data (BDSP credentialed access). **Source EEGs** are referenced from the
published BDSP EEG dataset (`s3://bdsp-opendata-repository/EEG/bids/`), not re-hosted; the **derived reproduce
cache** lives in this project's credentialed prefix `s3://bdsp-opendata-credentialed/morgoth-slowing/`
(pull with `aws s3 sync` — see [REPRODUCE.md](REPRODUCE.md)). Full provenance (raw→derived, de-identification
status, bdsp.io project) is in [DATA_SOURCE.md](DATA_SOURCE.md).
