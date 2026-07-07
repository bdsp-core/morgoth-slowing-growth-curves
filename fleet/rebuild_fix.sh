#!/usr/bin/env bash
# Re-run the rebuild after the bdsp_id-date fix so the UNION actually includes the cohort. OMOP skipped
# (DB tunnel down); integer AgeAtVisit used, re-pull fractional ages later.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/rebuild_fix.log; : > "$LOG"
S3DATA="s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves"
COH="/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/cohort_feats"
EXP="/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/n3feats"
WP="--profile opendata-write"
run(){ echo ">> $*"; "$@" && echo OK || echo "FAILED: $*"; }
{
echo "=== REBUILD-FIX $(date) ==="
run env PYTHONPATH=src python3 scripts/82_build_uniform_v2.py "$COH" "$EXP"
echo "--- verify union has BOTH sources with clean_normal ---"
python3 -c "
import pandas as pd
d=pd.read_parquet('data/derived/channel_stage_features.parquet')
cn=d[d.clean_normal==True]
print('clean_normal recordings by src:', cn.groupby('src').bdsp_id.nunique().to_dict())
print('abnormal recordings:', d[d.is_abnormal==True].bdsp_id.nunique())
"
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth pooled
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth auto
run env PYTHONPATH=src python3 scripts/76_keystone_growth_grid.py rel_delta,TAR,DAR
run env PYTHONPATH=src python3 scripts/68_topoplots_by_age.py rel_delta
run env PYTHONPATH=src python3 scripts/75_source_harmonization.py rel_delta
run env PYTHONPATH=src python3 scripts/build_analysis_dashboard.py
run aws s3 cp data/derived/channel_stage_features.parquet "$S3DATA/derived/channel_stage_features.parquet" $WP
run aws s3 sync figures/growth_v2/ "$S3DATA/figures/growth_v2/" $WP
run aws s3 cp results/analysis_dashboard.html "$S3DATA/analysis_dashboard.html" $WP
git add figures/growth_v2/ results/analysis_dashboard.html scripts/82_build_uniform_v2.py 2>/dev/null
git commit -q -m "Fix union rebuild: strip cohort bdsp_id date so both cohorts enter the union (all extract.py)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>" && echo "committed $(git rev-parse --short HEAD)" || echo "commit failed"
echo "=== REBUILD-FIX DONE $(date) ==="
} 2>&1 | tee -a "$LOG"
