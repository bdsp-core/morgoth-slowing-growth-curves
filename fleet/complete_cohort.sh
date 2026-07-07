#!/usr/bin/env bash
# FINISH THE COHORT RECOMPUTE: relaunch workers on the rest manifest to process the remaining ~2,785
# (slow cEEG tail; already-done are skipped via .done), wait for completion (workers drain) with a 6h
# backstop, tear the fleet down, then run the full rebuild (rebuild_fix.sh: uniform table + OMOP retry +
# union curves/keystone/topos + S3 + commit). One tracked job so completion notifies.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/complete_cohort.log; : > "$LOG"
B="s3:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/cohort_recompute"
P=stanford; R=us-east-1
teardown(){
  IDS=$(aws ec2 describe-instances --profile $P --region $R \
    --filters "Name=tag:fleet,Values=morgoth-cohort" "Name=instance-state-name,Values=pending,running" \
    --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null | tr '\t' '\n' | grep '^i-' || true)
  [ -n "$IDS" ] && aws ec2 terminate-instances --profile $P --region $R --instance-ids $IDS \
    --query 'length(TerminatingInstances)' --output text 2>&1 || echo "no instances to terminate"
}
{
echo "=== COMPLETE-COHORT START $(date) ==="
echo "--- relaunch 64 workers on the rest manifest (finish the tail) ---"
bash fleet/scale_cohort_rest.sh 64

echo "--- wait for completion (workers drain) or 6h cap ---"
prev=0; stall=0
for i in $(seq 1 180); do        # 180 * 120s = 6h backstop
  RUN=$(aws ec2 describe-instances --profile $P --region $R \
    --filters "Name=tag:fleet,Values=morgoth-cohort" "Name=instance-state-name,Values=running,pending" \
    --query 'length(Reservations[].Instances[])' --output text 2>/dev/null); RUN=${RUN:-0}
  DONE=$(rclone lsf "$B/done/" 2>/dev/null | wc -l | tr -d ' '); DONE=${DONE:-0}
  echo "$(date +%H:%M) done=$DONE/11020 workers=$RUN"
  [ "$RUN" -eq 0 ] && [ "$DONE" -gt 8000 ] && { echo "workers drained at $DONE"; break; }
  if [ "$DONE" -eq "$prev" ]; then stall=$((stall+1)); else stall=0; fi   # stall guard: no new work in ~30min
  [ "$stall" -ge 15 ] && { echo "stalled at $DONE (no progress ~30min) — stopping"; break; }
  prev=$DONE; sleep 120
done
teardown
FINAL=$(rclone lsf "$B/done/" 2>/dev/null | wc -l | tr -d ' ')
echo "=== fleet complete: done=$FINAL/11020 — starting rebuild $(date) ==="

bash fleet/rebuild_fix.sh
echo "=== COMPLETE-COHORT DONE $(date) ==="
} 2>&1 | tee -a "$LOG"
