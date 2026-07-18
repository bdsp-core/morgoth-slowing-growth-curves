# Reproduce the analysis (SAP-faithful, new-data-only)

Everything below runs on **this fleet run's data only** (`segment_master` v6). All legacy/derived tables,
figures and results from the prior run were **deleted** — they are the "old garbage" the audit flagged as
actively misleading (`docs/audits/audit-report-1.md` §2). Nothing in the analysis reads them.

## 0. Prereqs

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# R + gamlss are REQUIRED for the normative model (SAP §6.1). No shortcut/fallback is used.
curl -Ls https://micro.mamba.pm/api/micromamba/osx-arm64/latest | tar -xj bin/micromamba   # or linux-64
./bin/micromamba create -y -p ~/micromamba/envs/r -c conda-forge r-base c-compiler fortran-compiler make
~/micromamba/envs/r/bin/Rscript -e 'install.packages("gamlss", repos="https://cloud.r-project.org")'
export PATH="$HOME/micromamba/envs/r/bin:$PATH"     # so Rscript resolves
export PYTHONPATH=src
```

## 1. Get the run's data (S3)

```bash
BASE=bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/segmaster_v6
rclone copy $BASE/segment_master/  data/derived/segment_master/  --transfers 48
rclone copy $BASE/segment_summary/ data/derived/segment_summary/ --transfers 48
rclone copy $BASE/_done/           data/derived/segment_master/_done/   --transfers 48
rclone copy $BASE/_status/         data/derived/segment_master/_status/ --transfers 48
```

## 2. Build the canonical tables + labels

```bash
python scripts/33_assemble_ledger.py        # recording_meta + recording_labels (patient_id, lengths, stage_frac)
python scripts/label_rederive_sap.py        # CORRECTED slowing labels  <-- see below
python scripts/fleet_analysis_adapter.py    # segment_master -> channel_stage_features + labels_unified
```

**`label_rederive_sap.py` fixes a real labelling bug** (SAP §3.4/§3.5). The old extractor regexed the
impression *concatenated with the whole report body*, so `has_gen_slow` fired on purely descriptive lines
like *"generalized slowing, likely related to intermittent drowsiness"* — i.e. **physiologic** slowing in a
**normal** study. Rules now applied:
- **focal slowing is always pathologic**;
- **generalized slowing is pathologic only if the report names it among the abnormalities** (impression
  first; report detail as fallback), else physiologic;
- **abnormal-without-slowing** (e.g. epileptiform only) is its own stratum — not a positive, not a normal.

This removed **~5.5k physiologic recordings** from the detection positive class.

## 3. Normative model + deviation field (SAP §6.1 / §6.3)

```bash
python scripts/107_deviation_field_gamlss.py --k 5 --jobs 8
```
GAMLSS/**BCT** (Box–Cox-t: μ, σ, ν=skew, τ=kurtosis, each smooth in age) per (stage × region × feature),
fit on `clean_normal` only, with **k-fold cross-fitting** so a normal's own z uses out-of-fold parameters,
**folds split by `patient_id`** (SAP §3.3). This *replaces* the old Gaussian-kernel mean/SD z, which was
normal-theory and misstated centiles on these right-skewed features (worst in children).
Sanity: cross-fitted median z ≈ **0** for clean-normals, clearly positive for the rest.

## 4. Analyses + figures

```bash
python scripts/table1_sap.py                      # Table 1 to SAP §10 spec
python scripts/84_vigilance_matched_detection.py  # detection (vigilance-matched)
python scripts/76_keystone_growth_grid.py         # Figure 2 keystone growth curves (GAMLSS)
python scripts/ablation_auroc.py                  # attribution of the detection estimate (audit §1)
python scripts/build_dashboard_sap.py             # -> results/analysis_dashboard.html
```

## 5. Known gaps (honest — do not claim these are done)

- **Patient-clustered bootstrap CIs** are not yet wired into every reported interval (SAP §3.3). The
  intervals currently printed are recording-level and therefore too narrow.
- The analysis scripts still read `channel_stage_features` / `labels_unified` — but these are now
  **regenerated from `segment_master`** by the adapter (no legacy data). SAP §13 wants them to read
  `io/canonical` directly; that migration is not done.
- **`S` is supervised on report labels**, so it may NOT be used to evidence the "readers under-report
  slowing" claim (circular). That claim must rest on the unsupervised `z`, tested against the
  **independent expert panels** (OccasionNoise + MoE) — not yet run.
- Panel-dependent figures (human ceiling / expert overlay) need `occasion_features` built from the panel
  recordings — not yet built.

## 6. What the ablation found (audit §1)

Attribution of the detection estimate, W / whole_head / TAR (see `results/ablation_auroc.md`):

| factor | effect on AUROC |
|---|---|
| label correction (physiologic → excluded from positives) | **+0.111** |
| dropping artifact/suppressed segments | **+0.117** |
| pooling cohort + expansion | +0.010 |

The auditor hypothesised that the old 0.848 was **inflated by** flat/suppressed segments. **The data refutes
this** — keeping those segments *lowers* AUROC (0.766 → 0.649). The remaining gap to the old 0.848 is best
explained by the old tables being **first-600-s lineage** (an easier, cleaner slice) — i.e. the two numbers
are **not like-for-like**, rather than "we lost signal." The θ band edge (4–8 Hz, SAP §4.5) is already
applied in this run's features.
