> ⚠ **SUPERSEDED — historical only.** This doc asserts facts now overridden by `docs/analysis_plan.md` (the SAP) and `docs/claims_table.md` (e.g. theta = 4–8 Hz; severity adjectives / ACNS frequency words / band-from-our-features are FORBIDDEN output; artifact segments are flagged not stripped; zero reuse of prior derived tables). Do not implement from this file. Retained for provenance.

# Data availability & reproducing the analysis from this repo

Everything needed to **run the analyses and finish the paper is in this git repo.** Large raw inputs live
on S3/Box and are only needed to *re-derive* the committed tables.

## ✅ In git — enough to reproduce all analyses + the paper
- **Code:** `scripts/` (numbered pipeline) + `src/`.
- **Derived analysis tables** (`data/derived/*.parquet`, force-added despite the `*.parquet` ignore):
  `recording_features(_py)`, `recording_asymmetry(_py)`, `gate_probs`, `bsi_features`, `labels_canonical`,
  `stage_recording_features`, `growth_curves`, `adjusted_z`, `scores_v2` (~85 MB total).
- **De-identified labels / metadata:** `results/report_extracted_labels.csv` (report-extracted
  side/region/band + normal/abnormal/foc/gen flags, with provenance), `metadata/cohort_metadata.csv`,
  `results/label_counts.md`.
- **Results + figures:** `results/*.md`, `results/figs/*.png`, `figures/curves/`, `figures/stage_curves/`.
- **Dashboards:** `results/analysis_dashboard.html`, `results/fleet_burndown.html`.
- **Docs/plan:** `docs/manuscript_draft.md`, `docs/normative_deviation_plan.md`, `docs/reanalysis_status.md`.

A fresh clone can run `04 / 06 / 33 / 40 / 41 / 44 / 46 / 47 / 48 / 49 / 17 / 52 / 53 / 54` and
`build_analysis_dashboard.py` directly from these tables — no S3 or PHI access required.

## ☁️ On AWS S3 (BDSP credentialed) — large, regenerable, not in git
- Per-recording **features / stages / gate / provenance** for 12,980 recordings (~100 GB):
  `s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/expansion/`.
- Original-abnormal staging CSVs: `.../Growth_curves/original_abnormal_stages/`.
- Regenerate the derived tables with **`fleet/reanalyze.sh`** (streams S3 → rebuilds tables → analyses →
  dashboard). Only needed to re-derive from scratch.
- Fleet is **off** (0 instances). Relaunch for a new cohort/head from AMI `ami-0558041058267feeb`
  (see `fleet/RUNBOOK.md`).

## 🔒 PHI — not in git; BDSP/Box credentialed only
- Raw EEG **report text** (`EEGs_And_Reports.csv`) and structured **findings** CSVs. Needed **only** to
  *re-derive* labels (`scripts/20`, `scripts/52`). The derived label tables above are already committed, so
  the analyses do **not** need the raw PHI.

## Excluded from git (regenerable / too large)
- `data/derived/expansion_pilot_features.parquet` (209 MB aggregate), `data/derived/segment_features(_py).parquet`
  (319 MB each), `data/derived/expansion/features/` (~100 GB). All regenerable from S3.
- **Note:** scripts `10/11/38` (stage curves / descriptive scoring / stage-stratified AUROC) currently read
  the 319 MB per-segment tables; the pending stage-curve fix repoints them to the committed
  `stage_recording_features` (per-recording × stage) so they run from git alone.

## Not for git, ever
`*accessKeys*.csv` (AWS keys) and `fleet/.*` operational scratch are gitignored.
