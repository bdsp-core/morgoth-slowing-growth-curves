#!/usr/bin/env bash
# COHORT RECOMPUTE fleet — reprocess the routine cohort (manifest_cohort.jsonl) through the SAME pipeline
# as the overnight expansion (extract.py features + Morgoth staging), so both cohorts are pipeline-
# identical. New S3 prefix (cohort_recompute) + new tag (morgoth-cohort) so it's independent of any prior
# run. On-demand g4dn.xlarge (short job, avoid spot interruption). Elastic/dynamic worker skips .done.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
TARGET=${1:-48}
PROFILE=${AWS_PROFILE_FLEET:-stanford}
AMI=$(cat fleet/.ami_id)
SUBNET=subnet-073fad6d014fa4f63; SG=sg-05daa9abca4b4bacc; KEY=morgoth-pilot-key
HASH=$(git rev-parse --short HEAD)
S3OUT="bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/cohort_recompute"
CODE="$S3OUT/code"
UD=/tmp/ud/cohort.sh; mkdir -p /tmp/ud
cat > "$UD" <<EOF
#!/bin/bash
exec >> /var/log/morgoth-fleet.log 2>&1
sudo -u ubuntu bash -lc '
cd ~/morgoth-slowing-growth-curves && source .venv/bin/activate
rclone copyto $CODE/batch_worker.py fleet/batch_worker.py
rclone copyto $CODE/manifest_cohort.jsonl fleet/manifest_cohort.jsonl
export PILOT_VENV=\$(command -v python) PYTHONPATH=src PYTHONUNBUFFERED=1 MORGOTH_DEVICE=cuda MORGOTH2_DIR=/home/ubuntu/morgoth2 RCLONE_BIN=rclone CODE_COMMIT=$HASH
export DYNAMIC=1 SEED=\$RANDOM\$RANDOM S3_OUT=$S3OUT MANIFEST_LOCAL=/home/ubuntu/morgoth-slowing-growth-curves/fleet/manifest_cohort.jsonl
timeout 216000 python fleet/batch_worker.py
'
shutdown -h now
EOF
CUR=$(aws ec2 describe-instances --profile $PROFILE --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
  --filters "Name=tag:fleet,Values=morgoth-cohort" "Name=instance-state-name,Values=pending,running" \
  --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)
CUR=${CUR:-0}; NEED=$((TARGET-CUR))
echo "cohort fleet current=$CUR target=$TARGET need=$NEED  (profile $PROFILE, commit $HASH)"
launched=0
for ((i=0; i<NEED; i++)); do
  OUT=$(aws ec2 run-instances --profile $PROFILE --region us-east-1 --cli-connect-timeout 15 --cli-read-timeout 40 \
    --image-id "$AMI" --instance-type g4dn.xlarge \
    --key-name "$KEY" --security-group-ids "$SG" --subnet-id "$SUBNET" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=120,VolumeType=gp3}' \
    --instance-initiated-shutdown-behavior terminate \
    --user-data "file://$UD" --count 1 \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=morgoth-cohort},{Key=fleet,Value=morgoth-cohort}]" \
    --query 'Instances[0].InstanceId' --output text 2>&1)
  if [[ "$OUT" == i-* ]]; then launched=$((launched+1));
  elif echo "$OUT" | grep -qiE "InstanceLimitExceeded|VcpuLimitExceeded|Capacity"; then echo "cap/capacity reached at $((CUR+launched))"; break;
  else echo "stop: $(echo "$OUT" | tail -c 160)"; break; fi
done
echo "cohort fleet scaled +$launched -> ~$((CUR+launched)) workers  (tag morgoth-cohort, prefix cohort_recompute)"
