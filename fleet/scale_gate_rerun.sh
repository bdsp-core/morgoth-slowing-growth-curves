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
SUBNET=subnet-073fad6d014fa4f63; SG=sg-05daa9abca4b4bacc; KEY=morgoth-pilot-key
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
  echo "publishing worker code -> $S3_CODE"
  for f in fleet/gate_worker.py scripts/32_gate_rerun_worker.py scripts/shims/eeg_level_sliding.py \
           scripts/35_validate_gate_output.py; do
    aws s3 cp --profile bdspwrite "$f" "$S3_CODE/$(basename "$f")" >/dev/null \
      || { echo "publish failed: $f"; exit 1; }
    echo "  + $(basename "$f")"
  done
  echo "published $(date -u +%FT%TZ)"
fi

# self-terminate on the full run; stay up on the acceptance run so we can inspect the box
if [ "$PILOT" -gt 0 ]; then SHUTDOWN="echo 'PILOT: staying up for inspection'"; else SHUTDOWN="shutdown -h now"; fi

UD=/tmp/ud/gate.sh; mkdir -p /tmp/ud
cat > "$UD" <<EOF
#!/bin/bash
exec >> /var/log/morgoth-gate.log 2>&1
sudo -u ubuntu bash -lc '
cd ~/morgoth-slowing-growth-curves && source .venv/bin/activate
mkdir -p fleet scripts/shims
rclone copyto $CODE/gate_worker.py fleet/gate_worker.py
rclone copyto $CODE/32_gate_rerun_worker.py scripts/32_gate_rerun_worker.py
rclone copyto $CODE/eeg_level_sliding.py scripts/shims/eeg_level_sliding.py
rclone copyto $CODE/35_validate_gate_output.py scripts/35_validate_gate_output.py
export MORGOTH2_DIR=/home/ubuntu/morgoth2
export PILOT_VENV=\$MORGOTH2_DIR/.venv/bin/python     # Morgoth OWN venv — the only one with torch
export CKPT_DIR=\$MORGOTH2_DIR/checkpoints
export PYTHONPATH=src PYTHONUNBUFFERED=1 MORGOTH_DEVICE=cuda RCLONE_BIN=rclone CODE_COMMIT=$HASH
export KMP_DUPLICATE_LIB_OK=TRUE
export MANIFEST=/home/ubuntu/morgoth-slowing-growth-curves/data/manifest/report_manifest_v6.parquet
export PANEL_ROOT=bdsp:bdsp-opendata-credentialed/morgoth-slowing/panels
export OUTPUT_ROOT=/home/ubuntu/gate_out; mkdir -p \$OUTPUT_ROOT
export SRC_V6=$SRC_V6 S3_OUT=$S3OUT SEED=\$RANDOM\$RANDOM
export GATE_PILOT=$PILOT
export INSTANCE_TYPE=\$(curl -s -m 2 http://169.254.169.254/latest/meta-data/instance-type || echo unknown)
export N_GPUS=\$(nvidia-smi -L 2>/dev/null | wc -l)
export MORGOTH2_COMMIT=\$(git -C \$MORGOTH2_DIR rev-parse --short HEAD 2>/dev/null || echo unknown)
timeout 216000 python fleet/gate_worker.py
'
$SHUTDOWN
EOF

CUR=$(aws ec2 describe-instances --profile fleet --region us-east-1 \
  --filters "Name=tag:fleet,Values=morgoth-gate-rerun" "Name=instance-state-name,Values=pending,running" \
  --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)
CUR=${CUR:-0}; NEED=$((TARGET-CUR))
echo "gate re-run | current=$CUR target=$TARGET need=$NEED | commit $HASH | pilot=$PILOT"
echo "  SRC_V6 (read) : $SRC_V6"
echo "  S3_OUT (write): $S3OUT"
launched=0
for ((i=0; i<NEED; i++)); do
  OUT=$(aws ec2 run-instances --profile fleet --region us-east-1 \
    --image-id "$AMI" --instance-type g4dn.xlarge --instance-market-options 'MarketType=spot' \
    --key-name "$KEY" --security-group-ids "$SG" --subnet-id "$SUBNET" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=120,VolumeType=gp3}' \
    --instance-initiated-shutdown-behavior terminate \
    --user-data "file://$UD" --count 1 \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=morgoth-gate-rerun},{Key=fleet,Value=morgoth-gate-rerun}]" \
    --query 'Instances[0].InstanceId' --output text 2>&1)
  if [[ "$OUT" == i-* ]]; then launched=$((launched+1)); echo "  launched $OUT";
  elif echo "$OUT" | grep -q MaxSpotInstanceCount; then echo "  SPOT QUOTA CAP reached at $((CUR+launched)) workers"; break;
  else echo "  stop: $(echo "$OUT" | tail -c 160)"; break; fi
done
echo "scaled +$launched -> ~$((CUR+launched)) workers"
