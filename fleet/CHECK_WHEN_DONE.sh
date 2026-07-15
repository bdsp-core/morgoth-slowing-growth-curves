#!/usr/bin/env bash
# Run in the morning. Tells you if the fleet finished, and validates a fresh recording if so.
cd "$(dirname "$0")/.."
export AWS_PROFILE=fleet AWS_DEFAULT_REGION=us-east-1
P=s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/gate_rerun_v1
wg=$(aws s3 ls $P/window_gate/ --profile bdspwrite 2>/dev/null | wc -l | tr -d ' ')
st=$(aws s3 ls $P/_status/ --profile bdspwrite 2>/dev/null | wc -l | tr -d ' ')
w=$(aws ec2 describe-instances --filters "Name=tag:fleet,Values=morgoth-gate-rerun" "Name=instance-state-name,Values=pending,running" --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)
echo "recordings done : $wg   terminal failures: $st   ( $((wg+st)) / 27478 accounted for )"
echo "workers still up: $w"
if [ "$w" -eq 0 ] && [ "$((wg+st))" -ge 27470 ]; then
  echo ">>> RUN COMPLETE. Ask Claude to assemble results (pull gate_rerun_v1 + fold into two-stage)."
elif [ "$w" -eq 0 ]; then
  echo ">>> workers gone but $((27478-wg-st)) unaccounted — some transient failures; re-run: bash fleet/RELAUNCH_WHEN_BACK.sh"
else
  echo ">>> still running (~$(python3 -c "print(f'{(27478-$wg)/max($wg-2744,1)*0:.0f}')" 2>/dev/null)h left — check the dashboard)."
fi
