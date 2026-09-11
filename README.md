# morgoth-slowing-growth-curves

Lifespan **× sleep-stage normative "growth curves"** for quantitative EEG **slowing**. A single per-segment
**deviation-from-normal field** both **detects** pathological slowing (focal vs generalized) — placing most
of an 18-expert panel under its curve on both axes, beating the published van Putten qEEG lineage, and
beating a foundation-model gate on generalized slowing at one of two external sites (it trails on the other;
see §3.4b/§4 of the manuscript) — and reads OUT a governed, clinician-style **description**, validated
against clinical EEG reports and the human inter-rater ceiling. Part of the [bdsp-core](https://github.com/bdsp-core) automated-EEG effort.

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

- **The deviation field (unsupervised): the measurement layer.** Features are z-scored against
  **age × sleep-stage × region**-matched clinician-normals (GAMLSS: BCT for positive-support features, a
  robust normal family on the real line for the log features; sex-pooled). Fitted to the normal population
  only — it sees no label — which is what makes it admissible for the "we see slowing readers do not name"
  argument. **It never makes the categorical call itself.**
- **Two consumers of that one field.** *DESCRIBE* (how much / where / which band / how prevalent / which
  stage) reads the field directly. *DETECT* (whether, and focal vs generalized) is a **supervised** logistic
  head fitted on the field — which is why [docs/claims_table.md](docs/claims_table.md) confines any
  supervised score on `z` to detection benchmarks and forbids it from descriptive or blind-spot claims.
- **GATE (Morgoth foundation model): the reference detector.** Presence of pathological slowing, focal vs
  generalized, per 15-s segment pooled to the recording. It is the benchmark LENS's detector is measured
  against (and beats on generalized slowing on ON-100, trails on SAI-100), not a component of LENS.
  It cannot support any claim about seeing what experts miss: it is trained on their calls.
- **Governance:** every reportable clause is ALLOWED / PROVISIONAL / FORBIDDEN in
  [docs/claims_table.md](docs/claims_table.md). Severity adjectives and ACNS frequency words are FORBIDDEN
  output; the δ/θ/mixed band is **PROVISIONAL** — it ships only as a low-confidence gloss, calibrated to the
  report distribution rather than to accuracy, because its agreement (κ ≈ 0.10) sits at the expert-vs-expert
  floor. Prevalence is reported as a percentage, never as a word.

## Canonical facts (do not re-derive)

| | |
|---|---|
| Recording key | **`eeg_id` = `{patient_id}_{eeg_datetime}`** (one row per EEG, not per patient) |
| Segment | 15 s @ 200 Hz, 14 s step | Coverage | **up to the first 24 h** (never "first 600 s") |
| Bands | δ 1–4, **θ 4–8**, α 8–13, β 13–30, γ 30–45, total 0.5–45 Hz |
| Regions | **11** in the deviation field (`scripts/43` `REGIONS`): whole-head · anterior · posterior · L/R temporal · L/R parasagittal · **L/R anterior · L/R posterior** (the lateralized quadrants added for review C51); **6** in the per-segment feature table (`recording.py` `AGG_REGIONS`) |
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

**The clean-room run over the frozen v6 manifest is done, and every number in the manuscript comes from it.**
Nothing in `results/` is computed from the legacy `bdsp_id`-keyed tables any more (that was the state
`docs/audits/audit-report-1.md` audited; see the SUPERSEDED box at the top of that file). Reproducibility is
executed rather than asserted: `PYTHONPATH=src python3 scripts/certify_reproducibility.py` checks that every
declared display item has a producer and an output, that every producer is in the runner, that every number
the manuscript quotes appears in `results/`, and that the committed results match what the producers emit;
`scripts/verify_fresh_install.sh` re-runs all 22 stage-4 producers with only what git + S3 provide and
diffs the output — **every display item, with no exceptions**, since the de-identified SAI-100 panel Figure 3
needs is now published to the credentialed prefix (`scripts/export_sai100_panel.py`).

Environment: `PYTHONPATH=src`, `KMP_DUPLICATE_LIB_OK=TRUE`; the norms engine is R (GAMLSS,
`scripts/gamlss_fit.R`); pinned versions in `requirements.lock.txt`.

## Data access

De-identified, DUA-governed data (BDSP credentialed access). **Source EEGs** are referenced from the
published BDSP EEG dataset (`s3://bdsp-opendata-repository/EEG/bids/`), not re-hosted; the **derived reproduce
cache** lives in this project's credentialed prefix `s3://bdsp-opendata-credentialed/morgoth-slowing/`
(pull with `aws s3 sync` — see [REPRODUCE.md](REPRODUCE.md)). Full provenance (raw→derived, de-identification
status, bdsp.io project) is in [DATA_SOURCE.md](DATA_SOURCE.md).
