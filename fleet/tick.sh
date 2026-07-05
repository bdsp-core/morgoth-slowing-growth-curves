#!/usr/bin/env bash
# One monitoring tick. Refresh the burndown, then decide: SCALE (top up to 128) while there's plenty of
# work, DRAIN (stop topping up) for the tail so we don't relaunch workers that are self-terminating, or
# FINALIZE (shut everything down + regenerate the results dashboard) once done. Prints a STATE line the
# /loop reads to decide whether to keep rescheduling.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
TOTAL=13034
python scripts/fleet_progress.py $TOTAL 2>&1 | tail -1
DONE=$(python3 -c "import json;e=[json.loads(l) for l in open('data/derived/fleet_progress.jsonl') if l.strip()];print(max([x.get('done',0) for x in e if x.get('event')=='done']+[0]))")
REMAIN=$((TOTAL-DONE))
LIVE=$(aws ec2 describe-instances --profile fleet --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
  --filters "Name=tag:fleet,Values=morgoth-slowing" "Name=instance-state-name,Values=pending,running" \
  --query 'length(Reservations[].Instances[])' --output text 2>/dev/null); LIVE=${LIVE:-0}
echo "done=$DONE remain=$REMAIN live=$LIVE"

# Completion: nothing left, OR workers have self-terminated with only a tiny unprocessable tail remaining
# (those are recordings that error every attempt and never get a .done — don't spin the fleet back up).
if [ "$REMAIN" -le 0 ] || { [ "$LIVE" -eq 0 ] && [ "$DONE" -ge $((TOTAL-400)) ]; }; then
  echo "STATE=COMPLETE"; bash fleet/finalize.sh
elif [ "$REMAIN" -le 400 ]; then
  echo "STATE=DRAINING (tail=$REMAIN; not topping up — letting running workers finish + self-terminate)"
else
  bash fleet/scale_elastic.sh 128 2>&1 | tail -2
  echo "STATE=RUNNING"
fi
