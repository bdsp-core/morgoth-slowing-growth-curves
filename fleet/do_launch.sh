#!/usr/bin/env bash
# Launch fleet indices $1..$2 (inclusive), FLEET_TOTAL=64, from the fixed AMI. Per-call timeout so no
# single hung run-instances wedges the batch. Records launched IDs / failures. Idempotent-ish: skips an
# index if an instance tagged Name=morgoth-fleet-$i is already pending/running.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
AMI=$(cat fleet/.ami_id)
SUBNET=subnet-073fad6d014fa4f63; SG=sg-05daa9abca4b4bacc; KEY=morgoth-pilot-key
LO=${1:-1}; HI=${2:-63}
echo "launch $LO..$HI  AMI=$AMI  $(date)"
for ((i=LO;i<=HI;i++)); do
  # skip if this index already has a live instance
  EX=$(aws ec2 describe-instances --profile fleet --region us-east-1 --cli-connect-timeout 10 --cli-read-timeout 25 \
        --filters "Name=tag:Name,Values=morgoth-fleet-$i" "Name=instance-state-name,Values=pending,running" \
        --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)
  if [[ "$EX" =~ ^[0-9]+$ && "$EX" -gt 0 ]]; then echo "skip $i (already up)"; continue; fi
  ID=$(aws ec2 run-instances --profile fleet --region us-east-1 --cli-connect-timeout 10 --cli-read-timeout 25 --image-id "$AMI" \
    --instance-type g4dn.xlarge --instance-market-options 'MarketType=spot' \
    --key-name "$KEY" --security-group-ids "$SG" --subnet-id "$SUBNET" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=120,VolumeType=gp3}' \
    --instance-initiated-shutdown-behavior terminate \
    --user-data "file:///tmp/ud/ud_$i.sh" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=morgoth-fleet-$i},{Key=fleet,Value=morgoth-slowing}]" \
    --query 'Instances[0].InstanceId' --output text 2>fleet/.err_$i.txt)
  if [[ "$ID" == i-* ]]; then echo "$i $ID" | tee -a fleet/.launched_ids.txt;
  else echo "FAIL $i: $(tr -d '\n' <fleet/.err_$i.txt | tail -c 200)" | tee -a fleet/.launch_fail.txt; fi
done
echo "done. launched total: $(sort -u fleet/.launched_ids.txt 2>/dev/null | wc -l)  failed: $(wc -l <fleet/.launch_fail.txt 2>/dev/null || echo 0)  $(date)"
