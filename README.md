# morgoth-slowing-growth-curves

Normative **growth curves** (age × sex percentiles, per sleep/wake state) for quantitative EEG
**slowing** features, used to characterize **pathological slowing** — focal vs. generalized — in the
[morgoth-viewer](https://github.com/bdsp-core/morgoth-viewer) automated EEG report pipeline.

The system turns a patient's EEG into both a reproducible quantitative table and a clinician-style
sentence, e.g.:

> *Awake: frequent moderate right temporal delta slowing, present in 34% of artifact-free awake
> segments; right temporal delta burden 4.1 SD above age/state norms; max continuous run 5.0 min.*

**Start here → [PLAN.md](PLAN.md)** for the full roadmap, and
**[docs/feature_spec.md](docs/feature_spec.md)** for the analytical framework.

## Pipeline at a glance

```
15-s staged segments → multitaper spectra → band/ratio/asymmetry features
   → age×sex×state normative model (growth curves)
   → segment z → burden → patient-level z → topographic class → verbal phrase
```

## Layout

```
config/     example config + channel→region / homologous-pair maps
docs/        feature spec, data sources, glossary
src/morgoth_slowing/
  io/        S3 + segment/BIDS loaders
  features/  multitaper spectra, band power, ratios, asymmetry, regions
  norms/     control cohort, reference (growth-curve) models, z-scores
  scoring/   prevalence/severity/burden, patient-level z, topography
  report/    quantitative-table → verbal-phrase generation
  viz/       growth-curve plots with normal/abnormal overlays
scripts/     numbered end-to-end pipeline steps
notebooks/   data inventory, control selection, QC, curves, discrimination
tests/
```

## Quickstart (once data access is set up)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml   # edit S3 + local paths
python scripts/01_pull_data.py           # sync/inventory S3
python scripts/02_build_control_cohort.py
python scripts/03_compute_features.py
python scripts/04_fit_reference_models.py
python scripts/06_make_growth_curves.py
```

Data access requires BDSP credentialed AWS keys — see [docs/data_sources.md](docs/data_sources.md).
