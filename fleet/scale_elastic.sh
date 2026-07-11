#!/usr/bin/env bash
# Top up the elastic fleet toward $1 workers (default 128). Launches g4dn.xlarge spot singles with the
# elastic dynamic user-data until the target is reached or the spot quota caps out (MaxSpotInstanceCount).
# Safe to run every monitoring tick: at the current quota it launches 0 (one cheap failed call) and reports
# the cap; once a quota increase lands it fills the delta; it also relaunches workers lost to spot reclaim.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
TARGET=${1:-128}
AMI=$(cat fleet/.ami_id)
SUBNET=subnet-073fad6d014fa4f63; SG=sg-05daa9abca4b4bacc; KEY=morgoth-pilot-key
HASH=$(git rev-parse --short HEAD)
# FRESH prefix — the frozen v6 / segment_master run; NEVER the discarded expansion tree.
S3OUT="bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/segmaster_v6"
CODE="bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/code"
UD=/tmp/ud/dyn.sh; mkdir -p /tmp/ud
cat > "$UD" <<EOF
#!/bin/bash
exec >> /var/log/morgoth-fleet.log 2>&1
sudo -u ubuntu bash -lc '
cd ~/morgoth-slowing-growth-curves && source .venv/bin/activate
rclone copyto $CODE/batch_worker.py fleet/batch_worker.py
export MORGOTH2_DIR=/home/ubuntu/morgoth2
export PILOT_VENV=\$MORGOTH2_DIR/.venv/bin/python   # Morgoth OWN venv (two-venv; NOT the worker venv)
export PYTHONPATH=src PYTHONUNBUFFERED=1 MORGOTH_DEVICE=cuda RCLONE_BIN=rclone CODE_COMMIT=$HASH
export KMP_DUPLICATE_LIB_OK=TRUE RUN_GATE=1 GATE_STEP=5
export MANIFEST=/home/ubuntu/morgoth-slowing-growth-curves/data/manifest/report_manifest_v6.parquet
export PANEL_ROOT=bdsp:bdsp-opendata-credentialed/morgoth-slowing/panels   # rclone remote (reuses bdsp: creds)
export OUTPUT_ROOT=/home/ubuntu/out; mkdir -p \$OUTPUT_ROOT
export DYNAMIC=1 SEED=\$RANDOM\$RANDOM S3_OUT=$S3OUT
timeout 216000 python fleet/batch_worker.py
'
shutdown -h now
EOF
CUR=$(aws ec2 describe-instances --profile fleet --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
  --filters "Name=tag:fleet,Values=morgoth-slowing" "Name=instance-state-name,Values=pending,running" \
  --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)
CUR=${CUR:-0}; NEED=$((TARGET-CUR))
echo "current=$CUR target=$TARGET need=$NEED  (commit $HASH)"
launched=0
for ((i=0; i<NEED; i++)); do
  OUT=$(aws ec2 run-instances --profile fleet --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
    --image-id "$AMI" --instance-type g4dn.xlarge --instance-market-options 'MarketType=spot' \
    --key-name "$KEY" --security-group-ids "$SG" --subnet-id "$SUBNET" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=120,VolumeType=gp3}' \
    --instance-initiated-shutdown-behavior terminate \
    --user-data "file://$UD" --count 1 \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=morgoth-elastic},{Key=fleet,Value=morgoth-slowing}]" \
    --query 'Instances[0].InstanceId' --output text 2>&1)
  if [[ "$OUT" == i-* ]]; then launched=$((launched+1));
  elif echo "$OUT" | grep -q MaxSpotInstanceCount; then echo "quota cap reached at $((CUR+launched)) workers"; break;
  else echo "stop: $(echo "$OUT" | tail -c 140)"; break; fi
done
echo "scaled +$launched -> ~$((CUR+launched)) workers"
