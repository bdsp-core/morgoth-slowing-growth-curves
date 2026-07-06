#!/usr/bin/env bash
# Completion routine: STOP PAYING (terminate the whole fleet) once the manifest is fully processed,
# then kick off regeneration of the all-results analysis dashboard from the full S3 outputs.
# Idempotent + safe to run more than once. Workers also self-terminate on their own (elastic worker
# exits when a full pass finds nothing new, + a 60h per-instance backstop) — this is the safety sweep.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
echo "=== FLEET FINALIZE $(date) ==="

# Profile + the FULL set of fleet tags actually used by the scale scripts. NOTE (2026-07-06): the pilot
# and on-demand scale scripts tag instances "morgoth-n3pilot" / "morgoth-n3ondemand" (NOT "morgoth-
# slowing"), and there is no "fleet" AWS profile on the control machine — the working profile is
# "stanford". The old finalize filtered on profile=fleet + tag=morgoth-slowing, so it matched NOTHING and
# would have left the whole fleet billing. Keep this list in sync with fleet/scale_*.sh tags.
PROFILE=stanford; REGION=us-east-1
FLEET_TAGS="morgoth-slowing,morgoth-n3pilot,morgoth-n3ondemand"

# 0. CANCEL spot requests first — otherwise spot capacity self-heals and relaunches terminated workers.
SIRS=$(aws ec2 describe-spot-instance-requests --profile "$PROFILE" --region "$REGION" \
  --filters "Name=state,Values=active,open" --query "SpotInstanceRequests[].SpotInstanceRequestId" \
  --output text 2>/dev/null | tr '\t' '\n' | grep '^sir-' || true)
if [ -n "$SIRS" ]; then
  aws ec2 cancel-spot-instance-requests --profile "$PROFILE" --region "$REGION" \
    --spot-instance-request-ids $SIRS --query 'length(CancelledSpotInstanceRequests)' --output text 2>&1
  echo "cancelled spot requests (^)"
else
  echo "no active spot requests"
fi

# 1. Terminate every fleet worker (belt-and-suspenders beyond self-termination).
LIVE=$(aws ec2 describe-instances --profile "$PROFILE" --region "$REGION" --cli-connect-timeout 15 --cli-read-timeout 40 \
  --filters "Name=tag:fleet,Values=$FLEET_TAGS" "Name=instance-state-name,Values=pending,running" \
  --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null | tr '\t' '\n' | grep '^i-' || true)
if [ -n "$LIVE" ]; then
  echo "$LIVE" | xargs aws ec2 terminate-instances --profile "$PROFILE" --region "$REGION" --instance-ids \
    --query 'length(TerminatingInstances)' --output text 2>&1
  echo "terminated fleet workers (^)"
else
  echo "no fleet workers running (already drained)"
fi

# 1b. Kill any local self-heal / worker-topup loops that would otherwise relaunch capacity.
pkill -f 'fleet_progress.py' 2>/dev/null && echo "killed fleet_progress topup loop" || true
for s in scale_pilot scale_ondemand scale_full scale_elastic; do pkill -f "$s" 2>/dev/null || true; done

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
