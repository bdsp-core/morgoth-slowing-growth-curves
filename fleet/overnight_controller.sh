#!/usr/bin/env bash
# Self-healing overnight controller for the gate re-run. Runs detached; drives the fleet to completion and
# auto-lowers the recording cap (12 -> 8 -> 6 -> 4 h) if the 1s window head OOM-kills (rc=-9) or the run
# stalls. Keeps workers topped up, detects completion, then stops the fleet.
#
# Launch:  caffeinate -is nohup bash fleet/overnight_controller.sh > /tmp/gate_controller.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
export AWS_PROFILE=fleet AWS_DEFAULT_REGION=us-east-1
P=s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/gate_rerun_v1
TARGET=110                 # worker count to maintain (long-recording tail needs a big fleet)
DONE_AT=27470             # ~all 27,478 re-gateable (a handful may stay unprocessable even capped)
STATE=results/.gate_controller_state
CAPS=(12 8 6 4); ci=0     # cap ladder; start at index of the CURRENTLY running cap
# figure out where we already are on the ladder (fleet is running at 12 now)
CAP=${CAPS[$ci]}
stagnant=0; last=0

count_done(){ aws s3 ls $P/_done/ --profile bdspwrite 2>/dev/null | wc -l | tr -d ' '; }
count_win(){ aws s3 ls $P/window_gate/ --profile bdspwrite 2>/dev/null | wc -l | tr -d ' '; }
count_workers(){ aws ec2 describe-instances --filters "Name=tag:fleet,Values=morgoth-gate-rerun" \
  "Name=instance-state-name,Values=running,pending" --query 'length(Reservations[].Instances[])' --output text 2>/dev/null; }
oom_scan(){ # how many of up to 12 sampled workers show rc=-9 as their last event
  local n=0
  for W in $(aws ec2 describe-instances --filters "Name=tag:fleet,Values=morgoth-gate-rerun" \
      "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[].InstanceId' \
      --output text 2>/dev/null | tr '\t' '\n' | head -12); do
    aws s3 cp $P/_logs/$W.log - --profile bdspwrite 2>/dev/null | grep -E "OK |rc=-9" | tail -1 | grep -q "rc=-9" && n=$((n+1))
  done; echo $n
}
kill_fleet(){
  local ids=$(aws ec2 describe-instances --filters "Name=tag:fleet,Values=morgoth-gate-rerun" \
    "Name=instance-state-name,Values=running,pending" --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null)
  [ -n "$ids" ] && echo $ids | tr ' ' '\n' | xargs -n 50 aws ec2 terminate-instances --instance-ids >/dev/null 2>&1
}
relaunch(){  # $1 = cap
  echo "$(date -u +%FT%TZ) relaunch at CAP=$1h"
  GATE_MAX_HOURS=$1 ONDEMAND=1 ./fleet/scale_gate_rerun.sh $TARGET >/dev/null 2>&1 || true
}
lower_cap(){
  ci=$((ci+1))
  if [ $ci -ge ${#CAPS[@]} ]; then echo "$(date -u +%FT%TZ) already at lowest cap; not lowering"; ci=$((${#CAPS[@]}-1)); return 1; fi
  CAP=${CAPS[$ci]}
  echo "$(date -u +%FT%TZ) LOWERING CAP -> ${CAP}h (OOM or stall). cycling fleet."
  kill_fleet; sleep 90; relaunch $CAP; return 0
}

echo "$(date -u +%FT%TZ) controller start. cap=${CAP}h target=$TARGET"
while true; do
  d=$(count_done); w=$(count_win); N=$(count_workers)
  echo "$(date -u +%FT%TZ) done=$d win=$w workers=$N cap=${CAP}h stagnant=$stagnant"
  echo "done=$d win=$w workers=$N cap=${CAP}h ts=$(date -u +%FT%TZ)" > "$STATE"

  # ---- completion ----
  if [ "${d:-0}" -ge "$DONE_AT" ]; then
    echo "$(date -u +%FT%TZ) *** COMPLETE: $d done ***"; echo "COMPLETE done=$d" > "$STATE"; kill_fleet; break
  fi

  # ---- OOM: lower cap ----
  if [ "$N" -gt 0 ]; then
    o=$(oom_scan)
    if [ "${o:-0}" -ge 4 ]; then echo "$(date -u +%FT%TZ) OOM on $o workers"; lower_cap; sleep 300; last=$d; continue; fi
  fi

  # ---- progress / stall tracking ----
  if [ "${d:-0}" -le "${last:-0}" ]; then stagnant=$((stagnant+1)); else stagnant=0; fi
  last=$d

  # ---- workers died: relaunch (unless we just cycled) ----
  if [ "${N:-0}" -lt 90 ]; then
    echo "$(date -u +%FT%TZ) topping up workers ($N < $TARGET)"; relaunch $CAP
  fi

  # ---- long stall with no OOM: probably too-slow/OOM-late at this cap -> lower it ----
  if [ "$stagnant" -ge 10 ]; then      # ~50 min no progress
    echo "$(date -u +%FT%TZ) STALL ($stagnant cycles no progress) -> lower cap"; lower_cap && stagnant=0; last=$d
  fi

  sleep 300
done
echo "$(date -u +%FT%TZ) controller done."
