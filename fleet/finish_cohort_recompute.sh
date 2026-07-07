#!/usr/bin/env bash
# AUTONOMOUS post-recompute rebuild. Waits for the cohort-recompute fleet to finish + tear down, then:
# pulls the recomputed features, rebuilds the uniform table with BOTH cohorts on the identical extract.py
# pipeline, re-pulls OMOP ages, regenerates the growth curves / keystone / topos / harmonization on the
# UNION (all features now comparable), copies the derived data + figures to the S3 data location, rebuilds
# the dashboard, and commits. Robust: each step logged, failures don't abort the chain. Review in the AM.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/finish_cohort.log; : > "$LOG"
B="s3:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/cohort_recompute"
S3DATA="s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves"   # aws-cp target
COH_LOCAL="/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/cohort_feats"
EXP_LOCAL="/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/n3feats"
WP="--profile opendata-write"
say(){ echo "=== $* ($(date +%H:%M:%S)) ===" ; }
run(){ echo ">> $*"; "$@" && echo OK || echo "FAILED: $*"; }
{
say "FINISH-RECOMPUTE START"

say "0. wait for cohort fleet to drain (workers=0)"
for i in $(seq 1 240); do
  RUN=$(aws ec2 describe-instances --profile stanford --region us-east-1 \
    --filters "Name=tag:fleet,Values=morgoth-cohort" "Name=instance-state-name,Values=running,pending" \
    --query 'length(Reservations[].Instances[])' --output text 2>/dev/null); RUN=${RUN:-0}
  DONE=$(rclone lsf "$B/done/" 2>/dev/null | wc -l | tr -d ' ')
  echo "  wait: workers=$RUN done=$DONE"
  [ "$RUN" -eq 0 ] && [ "$DONE" -gt 5000 ] && break
  sleep 60
done
DONE=$(rclone lsf "$B/done/" 2>/dev/null | wc -l | tr -d ' ')
FEAT=$(rclone lsf "$B/features/" 2>/dev/null | wc -l | tr -d ' ')
echo "fleet finished: done=$DONE features=$FEAT"

say "1. pull recomputed cohort features -> local"
mkdir -p "$COH_LOCAL"
run rclone copy "$B/features/" "$COH_LOCAL/" --transfers 48 --checkers 48 --size-only
echo "local cohort feats: $(find "$COH_LOCAL" -name '*.parquet' | wc -l)"

say "2. rebuild uniform table (both cohorts = extract.py)"
run env PYTHONPATH=src python3 scripts/82_build_uniform_v2.py "$COH_LOCAL" "$EXP_LOCAL"

say "3. OMOP fractional ages"
run env PYTHONPATH=src python3 scripts/71_omop_fractional_age.py

say "4. regenerate growth curves (UNION) + keystone + topos + harmonization"
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth pooled
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth auto
run env PYTHONPATH=src python3 scripts/76_keystone_growth_grid.py rel_delta,TAR,DAR
run env PYTHONPATH=src python3 scripts/68_topoplots_by_age.py rel_delta
run env PYTHONPATH=src python3 scripts/75_source_harmonization.py rel_delta
run env PYTHONPATH=src python3 scripts/06_discrimination.py

say "5. rebuild dashboard"
run env PYTHONPATH=src python3 scripts/build_analysis_dashboard.py

say "6. copy derived data + figures to the S3 data location"
run aws s3 cp data/derived/channel_stage_features.parquet "$S3DATA/derived/channel_stage_features.parquet" $WP
run aws s3 cp data/derived/fractional_age.parquet "$S3DATA/derived/fractional_age.parquet" $WP
run aws s3 sync figures/growth_v2/ "$S3DATA/figures/growth_v2/" $WP
run aws s3 cp results/analysis_dashboard.html "$S3DATA/analysis_dashboard.html" $WP

say "7. commit"
git add figures/growth_v2/ results/analysis_dashboard.html scripts/82_build_uniform_v2.py scripts/76_keystone_growth_grid.py 2>/dev/null
git commit -q -m "Full-pipeline rebuild: both cohorts extract.py-identical; union curves + keystone (all features)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>" && echo "committed $(git rev-parse --short HEAD)" || echo "nothing to commit / commit failed"

say "FINISH-RECOMPUTE DONE"
} 2>&1 | tee -a "$LOG"
