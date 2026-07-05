#!/usr/bin/env bash
# Completion routine: STOP PAYING (terminate the whole fleet) once the manifest is fully processed,
# then kick off regeneration of the all-results analysis dashboard from the full S3 outputs.
# Idempotent + safe to run more than once. Workers also self-terminate on their own (elastic worker
# exits when a full pass finds nothing new, + a 60h per-instance backstop) — this is the safety sweep.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
echo "=== FLEET FINALIZE $(date) ==="

# 1. Terminate every fleet worker (belt-and-suspenders beyond self-termination). Pilot box is left up
#    for the re-analysis step; terminate it manually when fully done (see RUNBOOK).
IDS=$(aws ec2 describe-instances --profile fleet --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
  --filters "Name=tag:fleet,Values=morgoth-slowing" "Name=instance-state-name,Values=pending,running" \
  --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null | tr '\t' '\n' | grep -c '^i-' || true)
LIVE=$(aws ec2 describe-instances --profile fleet --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
  --filters "Name=tag:fleet,Values=morgoth-slowing" "Name=instance-state-name,Values=pending,running" \
  --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null | tr '\t' '\n' | grep '^i-' || true)
if [ -n "$LIVE" ]; then
  echo "$LIVE" | xargs aws ec2 terminate-instances --profile fleet --region us-east-1 --instance-ids \
    --query 'length(TerminatingInstances)' --output text 2>&1
  echo "terminated fleet workers"
else
  echo "no fleet workers running (already drained)"
fi

# 2. Stop the local 10-min throughput sampler
SP=$(cat fleet/.sampler_pid 2>/dev/null || true)
[ -n "$SP" ] && kill "$SP" 2>/dev/null && echo "sampler stopped (pid $SP)" || true

# 3. Regenerate the all-results dashboard from the full dataset (mechanical sync + re-analysis).
if [ -f fleet/reanalyze.sh ]; then
  echo "launching re-analysis -> analysis_dashboard.html ..."
  bash fleet/reanalyze.sh 2>&1 | tail -20
else
  echo "NOTE: fleet/reanalyze.sh not present yet — run the re-analysis manually (see RUNBOOK)."
fi
echo "=== FINALIZE DONE $(date) ==="
