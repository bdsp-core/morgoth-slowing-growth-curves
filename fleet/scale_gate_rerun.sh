#!/usr/bin/env bash
# Top up the GATE RE-RUN fleet toward $1 workers. Same elastic/self-healing/self-terminating design as
# scale_elastic.sh, but driving fleet/gate_worker.py -> scripts/32_gate_rerun_worker.py.
#
# WHAT IS DIFFERENT FROM scale_elastic.sh (docs/gate_rerun_spec.md):
#   GATE_STEP=1   (not 5)  -- scale_elastic.sh:26 set 5. Morgoth's own pipeline uses 1 s and feeds THAT to
#                             the EEG-level heads, so every p_focal/p_generalized we have came from a
#                             sequence 5x sparser than the heads were trained on (24 tokens, not 120).
#   FRESH S3 prefix        -- writes to Growth_curves/gate_rerun_v1. segmaster_v6 is READ ONLY and is never
#                             touched, so the existing run is not thrown away.
#   PILOT=<n>              -- acceptance mode: process only N recordings, then stop (no self-terminate), so
#                             the 100-EEG test can be validated before spending the full run.
#
# Usage:
#   ./fleet/scale_gate_rerun.sh 1 100      # ACCEPTANCE: 1 worker, 100 recordings, box stays up
#   ./fleet/scale_gate_rerun.sh 128        # FULL RUN: top up toward 128 workers, self-terminating
set -uo pipefail
cd "$(dirname "$0")/.."
TARGET=${1:-128}
PILOT=${2:-0}                       # >0 = acceptance run: stop after N recordings, do NOT shut down
AMI=$(cat fleet/.ami_id)
# scale_elastic.sh hardcoded the us-east-1f subnet. g4dn.xlarge SPOT CAPACITY IS EXHAUSTED THERE — AWS
# replies "you can currently get g4dn.xlarge capacity by ... choosing us-east-1a/b/c/d". So walk the AZs
# instead of pinning one: a spot fleet that dies on one AZ's capacity is not elastic.
SUBNETS=(subnet-0d9327335dd39a415 subnet-0092e6aaec4ee7d67 subnet-04d5c16b4cea5e98b subnet-005154d14b49a5b6e subnet-073fad6d014fa4f63)
# ...and don't pin the instance type either. g4dn.xlarge spot capacity was EXHAUSTED IN EVERY AZ when this
# was written. All of these are single-GPU and the worker uses exactly one, so they are interchangeable;
# they differ only in speed and price. Walk them until one places. (All count against the same "All G and
# VT Spot" quota, in vCPUs: the 4-vCPU types cost 4 of the 512, the 8-vCPU ones cost 8.)
TYPES=(g4dn.xlarge g5.xlarge g6.xlarge g4dn.2xlarge g5.2xlarge)
SG=sg-05daa9abca4b4bacc; KEY=morgoth-pilot-key
# ONDEMAND=1 drops the spot market option. Spot capacity for EVERY GPU type was exhausted in EVERY us-east-1
# AZ when this was written, and a 100-recording acceptance run on-demand costs about $0.53 — not worth
# waiting on the spot market for. For the FULL run, spot is ~3x cheaper, so retry spot first.
if [ "${ONDEMAND:-0}" = "1" ]; then MARKET=(); else MARKET=(--instance-market-options MarketType=spot); fi
HASH=$(git rev-parse --short HEAD)
BUCKET="bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves"
SRC_V6="$BUCKET/segmaster_v6"       # READ ONLY — the existing run
S3OUT="$BUCKET/gate_rerun_v1"       # FRESH — never segmaster_v6
CODE="$BUCKET/code_gate_rerun"      # where we publish the new worker files (see §publish below)

# PUBLISH: push the new worker files to S3 so the AMI (which has OLD code baked in) picks them up at boot.
# Uses the aws CLI, not rclone: the `bdsp:` rclone remote is configured ON THE AMI, not on the launching
# machine. The WORKER still uses rclone for everything (S3_CODE below is the same prefix, aws-written).
S3_CODE="s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/code_gate_rerun"
if [ "${PUBLISH:-0}" = "1" ]; then
  # SHIP THE WHOLE SOURCE TREE, not individual files. The AMI's repo checkout is from 2026-07-04; the code
  # that actually ran the fleet is from 07-11. So the AMI is missing BOTH the v6 manifest AND
  # morgoth_slowing/fleet/ -- someone must have git-pulled on the box by hand before the original run. That
  # undocumented step is why none of this was reproducible. A version-pinned bundle removes the entire class
  # of "the AMI is stale" bug: the box runs EXACTLY the commit we tested.
  echo "bundling source @ $HASH -> $S3_CODE"
  BUNDLE=/tmp/gate_bundle_$HASH.tgz
  tar czf "$BUNDLE" \
      src scripts/32_gate_rerun_worker.py scripts/35_validate_gate_output.py scripts/shims \
      fleet/gate_worker.py data/manifest/report_manifest_v6.parquet
  aws s3 cp --profile bdspwrite "$BUNDLE" "$S3_CODE/bundle.tgz" >/dev/null || { echo "publish failed"; exit 1; }
  echo "  + bundle.tgz  ($(du -h "$BUNDLE" | cut -f1))  commit $HASH"
  echo "published $(date -u +%FT%TZ)"
fi

# self-terminate on the full run; stay up on the acceptance run so we can inspect the box
if [ "$PILOT" -gt 0 ]; then SHUTDOWN="echo 'PILOT: staying up for inspection'"; else SHUTDOWN="shutdown -h now"; fi

UD=/tmp/ud/gate.sh; mkdir -p /tmp/ud
cat > "$UD" <<EOF
#!/bin/bash
# NOT redirected to a file: cloud-init sends stdout/stderr to the SERIAL CONSOLE, which is readable with
# `aws ec2 get-console-output` — no SSH, no key, works even after the box self-terminates. The box's local
# /var/log is unreachable by design (port 22 closed, spot box terminates itself), so anything written only
# there is lost. Every boot step below echoes a marker so a failure can be bisected from the console alone.
set -x
echo "=== GATE RERUN BOOT $(date -u +%FT%TZ) ==="
sudo -u ubuntu bash -lc '
set -x
echo "STEP repo"; cd ~/morgoth-slowing-growth-curves || { echo "FATAL: repo missing"; exit 90; }
echo "STEP venv"; source .venv/bin/activate || { echo "FATAL: venv missing"; exit 91; }
echo "STEP python: $(which python) $(python -V 2>&1)"
echo "STEP rclone: $(which rclone)"; rclone listremotes || echo "FATAL: no rclone remotes"
mkdir -p fleet scripts/shims
echo "STEP bundle"
rclone copyto $CODE/bundle.tgz /tmp/bundle.tgz || { echo "FATAL: bundle fetch failed"; exit 92; }
tar xzf /tmp/bundle.tgz -C . || { echo "FATAL: bundle extract failed"; exit 93; }
echo "STEP bundle OK: $(python -c "import sys;sys.path.insert(0,\"src\");from morgoth_slowing.fleet import ingest;print(\"morgoth_slowing.fleet OK\")" 2>&1)"
echo "STEP manifest: $(du -h data/manifest/report_manifest_v6.parquet 2>/dev/null | cut -f1)"
export MORGOTH2_DIR=/home/ubuntu/morgoth2
export PILOT_VENV=\$MORGOTH2_DIR/.venv/bin/python     # Morgoth OWN venv — the only one with torch
export CKPT_DIR=\$MORGOTH2_DIR/checkpoints
export PYTHONPATH=src PYTHONUNBUFFERED=1 MORGOTH_DEVICE=cuda RCLONE_BIN=rclone CODE_COMMIT=$HASH
export KMP_DUPLICATE_LIB_OK=TRUE
export MANIFEST=/home/ubuntu/morgoth-slowing-growth-curves/data/manifest/report_manifest_v6.parquet
export PANEL_ROOT=bdsp:bdsp-opendata-credentialed/morgoth-slowing/panels
export OUTPUT_ROOT=/home/ubuntu/gate_out; mkdir -p \$OUTPUT_ROOT
export SRC_V6=$SRC_V6 S3_OUT=$S3OUT SEED=\$RANDOM\$RANDOM
export EDF_REMOTE=bdsp:   # the AMI has no s3: remote; bdsp: is the same S3 with the same creds
export GATE_PILOT=$PILOT
IMDS_TOK=\$(curl -sX PUT -m 2 "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
imds() { curl -s -m 2 -H "X-aws-ec2-metadata-token: \$IMDS_TOK" "http://169.254.169.254/latest/meta-data/\$1"; }
export INSTANCE_TYPE=\$(imds instance-type)
export N_GPUS=\$(nvidia-smi -L 2>/dev/null | wc -l)
export MORGOTH2_COMMIT=\$(git -C \$MORGOTH2_DIR rev-parse --short HEAD 2>/dev/null || echo unknown)
# NOTE: no apostrophes below this line -- we are inside a single-quoted bash -lc block.
# Log shipping: /var/log on a self-terminating spot box is unreadable, so stream the log to S3.
IID=\$(imds instance-id); [ -z "\$IID" ] && IID=unknown
LOG=/home/ubuntu/gate_\$IID.log
( while true; do rclone copyto \$LOG $S3OUT/_logs/\$IID.log 2>/dev/null; sleep 20; done ) &
SHIPPER=\$!
timeout 216000 python fleet/gate_worker.py > \$LOG 2>&1
RC_=\$?
kill \$SHIPPER 2>/dev/null
echo "--- worker exited rc=\$RC_ ---" >> \$LOG
rclone copyto \$LOG $S3OUT/_logs/\$IID.log 2>/dev/null    # final flush, ALWAYS
'
$SHUTDOWN
EOF

if ! bash -n "$UD" 2>/tmp/ud_err; then
  echo "FATAL: generated user-data has a shell syntax error -- refusing to launch:"
  sed -n '1,3p' /tmp/ud_err
  echo "(this is what killed the first three instances: an apostrophe inside the single-quoted bash -lc block)"
  exit 1
fi
echo "user-data syntax OK"

CUR=$(aws ec2 describe-instances --profile fleet --region us-east-1 \
  --filters "Name=tag:fleet,Values=morgoth-gate-rerun" "Name=instance-state-name,Values=pending,running" \
  --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)
CUR=${CUR:-0}; NEED=$((TARGET-CUR))
echo "gate re-run | current=$CUR target=$TARGET need=$NEED | commit $HASH | pilot=$PILOT"
echo "  SRC_V6 (read) : $SRC_V6"
echo "  S3_OUT (write): $S3OUT"
launched=0
for ((i=0; i<NEED; i++)); do
  placed=0
  for TYPE in "${TYPES[@]}"; do
  for SUBNET in "${SUBNETS[@]}"; do        # rotate type x AZ: spot capacity is per (type, AZ) and moves
    OUT=$(aws ec2 run-instances --profile fleet --region us-east-1 \
      --image-id "$AMI" --instance-type "$TYPE" ${MARKET[@]+"${MARKET[@]}"} \
      --key-name "$KEY" --security-group-ids "$SG" --subnet-id "$SUBNET" \
      --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=120,VolumeType=gp3}' \
      --instance-initiated-shutdown-behavior terminate \
      --user-data "file://$UD" --count 1 \
      --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=morgoth-gate-rerun},{Key=fleet,Value=morgoth-gate-rerun}]" \
      --query 'Instances[0].InstanceId' --output text 2>&1)
    if [[ "$OUT" == i-* ]]; then
      launched=$((launched+1)); placed=1; echo "  launched $OUT  ($TYPE, $SUBNET)"; break
    elif echo "$OUT" | grep -q MaxSpotInstanceCount; then
      echo "  SPOT QUOTA CAP reached at $((CUR+launched)) workers"; break 3
    elif echo "$OUT" | grep -qiE "InsufficientInstanceCapacity|capacity"; then
      continue                              # this (type, AZ) is dry — try the next
    else
      echo "  stop: $(echo "$OUT" | tail -c 160)"; break 3
    fi
  done
  [ "$placed" -eq 1 ] && break
  done
  [ "$placed" -eq 0 ] && {
      echo "  no GPU capacity in any (type x AZ) right now."
      [ "${ONDEMAND:-0}" = "1" ] || echo "  -> retry later, or re-run with ONDEMAND=1 (~3x price, but available)"
      break; }
done
echo "scaled +$launched -> ~$((CUR+launched)) workers"
