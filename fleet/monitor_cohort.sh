#!/usr/bin/env bash
# Monitor the cohort-recompute fleet; TERMINATE it on completion (or a 4h cost cap) so it can't run away.
set -uo pipefail
cd "$(dirname "$0")/.."
B="s3:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/cohort_recompute"
P=stanford; R=us-east-1; TOTAL=4916; TARGET_DONE=4890
teardown(){
  IDS=$(aws ec2 describe-instances --profile $P --region $R \
    --filters "Name=tag:fleet,Values=morgoth-cohort" "Name=instance-state-name,Values=pending,running" \
    --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null | tr '\t' '\n' | grep '^i-' || true)
  [ -n "$IDS" ] && aws ec2 terminate-instances --profile $P --region $R --instance-ids $IDS \
    --query 'length(TerminatingInstances)' --output text 2>&1 || echo "no instances to terminate"
}
for i in $(seq 1 120); do          # 120 * 120s = 4h hard cap
  DONE=$(rclone lsf "$B/done/" 2>/dev/null | wc -l | tr -d ' '); DONE=${DONE:-0}
  RUN=$(aws ec2 describe-instances --profile $P --region $R \
    --filters "Name=tag:fleet,Values=morgoth-cohort" "Name=instance-state-name,Values=running,pending" \
    --query 'length(Reservations[].Instances[])' --output text 2>/dev/null); RUN=${RUN:-0}
  echo "$(date +%H:%M:%S) done=$DONE/$TOTAL workers=$RUN"
  if [ "$DONE" -ge "$TARGET_DONE" ]; then echo "=== COMPLETE ($DONE) — tearing down ==="; teardown; break; fi
  if [ "$RUN" -eq 0 ] && [ "$DONE" -gt 200 ]; then echo "=== workers drained at $DONE — done ==="; break; fi
  sleep 120
done
echo "cohort monitor exit: done=$(rclone lsf "$B/done/" 2>/dev/null | wc -l | tr -d ' ')  $(date)"
teardown   # belt-and-suspenders
