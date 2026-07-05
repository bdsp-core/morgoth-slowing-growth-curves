#!/usr/bin/env bash
# Back up the large, git-unfriendly source + intermediate data to BOTH Box (for home access) and S3.
# Resumable (rclone copy skips already-transferred). Sources: raw report text (1.1GB), de-id findings,
# and the per-segment tables (segment_features(_py) 319MB each + segment_stages) that scripts 10/11/38 read.
set -uo pipefail
cd "$(dirname "$0")/.."
RC=~/.local/bin/rclone
SC="/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad"
BOX="box:Brandon - DeID/0_People/ChenXiSun/ChenXiSun/Morgoth2/Datasets/slowing-for-morgoth-viewer"
S3="bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves"
export AWS_ACCESS_KEY_ID=$(python3 -c "import csv;print(list(csv.DictReader(open('/Users/mbwest/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv',encoding='utf-8-sig')))[0]['Access key ID'])")
export AWS_SECRET_ACCESS_KEY=$(python3 -c "import csv;print(list(csv.DictReader(open('/Users/mbwest/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv',encoding='utf-8-sig')))[0]['Secret access key'])")
OPT="--transfers 8 --checkers 8 --retries 5 --low-level-retries 10 --stats 60s --stats-one-line"

# stage the segment tables into one local dir so a single rclone copy handles them
mkdir -p /tmp/segbak
cp -f data/derived/segment_features.parquet data/derived/segment_features_py.parquet data/derived/segment_stages.parquet /tmp/segbak/ 2>/dev/null

echo "=== [1/4] Box: raw reports ==="
$RC copy "$SC/reports/EEGs_And_Reports.csv" "$BOX/reports/" $OPT
echo "=== [2/4] Box: findings + segment tables ==="
$RC copy "$SC/findings/" "$BOX/findings/" $OPT
$RC copy /tmp/segbak/ "$BOX/segment_tables/" $OPT
echo "=== [3/4] S3: segment tables ==="
$RC copy /tmp/segbak/ "$S3/segment_tables/" $OPT
echo "=== [4/4] S3: raw reports ==="
$RC copy "$SC/reports/EEGs_And_Reports.csv" "$S3/source_reports/" $OPT
echo "BACKUP_DONE $(date)"
