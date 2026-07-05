#!/usr/bin/env bash
# Regenerate results/analysis_dashboard.html on the FULL fleet dataset. Streams per-recording outputs
# from S3 (no ~100GB local sync — reads each ~11MB parquet into memory via rclone cat), rebuilds the
# pilot-lineage derived tables, re-runs the feature-based analyses, and rebuilds the dashboard.
#
# NOTE: report-label-dependent panels (lateralization / region / report-agreement) need per-site
# free-text report labels extracted from Box (scripts/20_extract_report_labels.py). Those are NOT part
# of the fleet outputs, so those panels re-run only against whatever report labels already exist
# (pilot coverage) — see fleet/RUNBOOK.md §10/R4. Feature-based panels (growth curves, discrimination,
# age-AUROC, van Putten, BSI) DO regenerate on the full dataset.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONPATH=src RCLONE_BIN=${RCLONE_BIN:-~/.local/bin/rclone}
KEYS=/Users/mbwest/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv
export AWS_ACCESS_KEY_ID=$(python3 -c "import csv;print(list(csv.DictReader(open('$KEYS',encoding='utf-8-sig')))[0]['Access key ID'])")
export AWS_SECRET_ACCESS_KEY=$(python3 -c "import csv;print(list(csv.DictReader(open('$KEYS',encoding='utf-8-sig')))[0]['Secret access key'])")
BASE="bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/expansion"

run(){ echo "--- $* ---"; python "$@" || echo "WARN: $* failed (panel may stay at prior data)"; }

echo "=== 1. rebuild derived tables from S3 (streaming, disk-free) $(date) ==="
EXP_DIR="$BASE" python scripts/51_expansion_to_derived.py

echo "=== 2. feature-based analyses on FULL data ==="
run scripts/04_fit_reference_models.py
run scripts/06_discrimination.py
run scripts/47_vanputten_comparison.py
run scripts/48_bsi_growth.py
run scripts/33_age_auroc.py

echo "=== 3. stage + report-dependent panels (best-effort; need segment/report labels) ==="
for s in 10_stage_curves 11_descriptive_scoring 38_stage_stratified_auroc \
         40_lateralization_gated 41_lateralization_by_band 42_region_gated \
         43_flip_augment_lateralizer 44_lateralizer_band_conditioned 46_region_detection \
         49_extra_evals 16_gated_report 17_lr_vs_morgoth; do
  run scripts/${s}.py
done

echo "=== 4. rebuild dashboard ==="
python scripts/build_analysis_dashboard.py
echo "=== reanalyze done -> results/analysis_dashboard.html  $(date) ==="
