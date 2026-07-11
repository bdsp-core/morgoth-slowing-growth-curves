# morgoth-slowing-growth-curves

Lifespan **× sleep-stage normative "growth curves"** for quantitative EEG **slowing**, with a two-stage
system that **detects** pathological slowing (focal vs generalized) and produces a governed, clinician-style
**description** — validated against clinical EEG reports and the human inter-rater ceiling. Part of the
[bdsp-core](https://github.com/bdsp-core) automated-EEG effort.

> **Start here → [docs/analysis_plan.md](docs/analysis_plan.md)** — the pre-registered Statistical Analysis
> Plan (the SAP). It is the single source of truth for how data is prepared, analyzed, and reported.

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

`data/manifest/report_manifest_v3.parquet` — the EEG list the clean-room run ingests: **14,957 EEGs /
13,642 patients** (cohort + pool backfill), 4-region taxonomy, report labels + de-identified text + S3
routing. Built by `scripts/{120,88,121,124,125}`. Coverage adequacy: [docs/coverage_report.md](docs/coverage_report.md)
+ [figures/coverage/coverage_overview.png](figures/coverage/coverage_overview.png) (all marginals ≥200).

## Layout

```
docs/            governance (SAP + companions); docs/archive/ = superseded
src/morgoth_slowing/
  features/      extract.py (canonical extractor), recording, artifact
  io/            edf, staging (Morgoth sleep stager), omop
  fleet/         ingest.py — shared fleet-ingest helpers
  report/        parse.py — report NLP; phrase generation
  norms/ scoring/ viz/
scripts/         keep-set: 1 fleet worker (30) + pre-fleet builders (20,60,88,120–125)
                 + current analysis (47,85–116, gamlss_fit.R); scripts/archive/ = legacy
data/manifest/   frozen run + report manifests
references/      van Putten qEEG sources (README + .bib; PDFs gitignored)
tests/
```

## Status

Findings are being hardened on the current (legacy) derived tables; the **one clean-room re-run** over the
frozen manifest produces the final numbers (SAP §12 code-review gate → §13 build order). Data access needs
BDSP credentialed AWS keys — see [docs/data_sources.md](docs/data_sources.md). Environment:
`PYTHONPATH=src`, `KMP_DUPLICATE_LIB_OK=TRUE`; the norms engine is R (GAMLSS, `scripts/gamlss_fit.R`).
