#!/usr/bin/env bash
# Final completion: pull the COMPLETE recomputed cohort (incl. the tail that finished after the 75% pull),
# rebuild the uniform table so ALL cohort recordings (incl. tail abnormals) are in it, refresh S3 + commit.
# The growth curves/keystone are already final (all normals were in the earlier pull), so no re-fit here.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/final_rebuild.log; : > "$LOG"
COH="/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/cohort_feats"
EXP="/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/n3feats"
B="s3:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/cohort_recompute"
S3DATA="s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves"
run(){ echo ">> $*"; "$@" && echo OK || echo "FAILED: $*"; }
{
echo "=== FINAL REBUILD $(date) ==="
run rclone copy "$B/features/" "$COH/" --transfers 48 --checkers 48 --size-only
echo "local cohort features: $(find "$COH" -name '*.parquet' | wc -l)"
run env PYTHONPATH=src python3 scripts/82_build_uniform_v2.py "$COH" "$EXP"
python3 -c "
import pandas as pd
d=pd.read_parquet('data/derived/channel_stage_features.parquet')
print('recordings:', d.bdsp_id.nunique(), '| by src:', d.groupby('src').bdsp_id.nunique().to_dict())
print('clean_normal by src:', d[d.clean_normal==True].groupby('src').bdsp_id.nunique().to_dict())
print('abnormal (for detection):', d[d.is_abnormal==True].bdsp_id.nunique())
frac=(d.drop_duplicates('bdsp_id').age%1!=0).mean(); print(f'fractional ages: {100*frac:.0f}%')
"
run aws s3 cp data/derived/channel_stage_features.parquet "$S3DATA/derived/channel_stage_features.parquet" --profile opendata-write
git add scripts/82_build_uniform_v2.py fleet/final_rebuild.sh fleet/complete_cohort.sh 2>/dev/null
git commit -q -m "Final rebuild: complete cohort (incl. tail abnormals) in the uniform table; all extract.py

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>" && echo "committed $(git rev-parse --short HEAD)" || echo "commit: nothing/failed"
echo "=== FINAL REBUILD DONE $(date) ==="
} 2>&1 | tee -a "$LOG"
