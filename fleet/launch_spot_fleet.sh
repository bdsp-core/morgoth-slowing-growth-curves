#!/usr/bin/env bash
# Launch a spot fleet of N g4dn.xlarge from an AMI of the (proven) pilot box. Each instance processes a
# STRIDE of the manifest (FLEET_INDEX::FLEET_TOTAL) and writes per-recording outputs to S3, then self-
# terminates. No Docker/ECR/Batch — reuses the pilot's working env (repo, venv, checkpoints, rclone).
#
# Run from a machine with `aws` configured for the account (e.g. console CloudShell). Fill the block below.
# START SMALL: set N=2 first, confirm S3 outputs, THEN re-run with the full N.
set -euo pipefail

# ---- EDIT THESE ---------------------------------------------------------------------------------
REGION=us-east-1
AMI=ami-xxxxxxxx                 # AMI you created from the pilot box (see RUNBOOK step 2)
KEY=morgoth-pilot-key            # your EC2 key pair name
SG=sg-xxxxxxxx                   # security group (SSH from your IP is enough)
SUBNET=subnet-xxxxxxxx           # a subnet with internet/S3 access (us-east-1)
IAM_PROFILE=morgoth-fleet        # instance profile name w/ S3 read+write to $BUCKET (RUNBOOK step 1)
BUCKET=s3://your-bucket/morgoth-slowing        # your bucket; manifest at $BUCKET/manifest.jsonl
N=2                              # number of instances (START AT 2; scale to ~40 after validation)
# -------------------------------------------------------------------------------------------------

S3_OUT="$BUCKET/expansion"
S3_MANIFEST="$BUCKET/manifest.jsonl"
for ((i=0; i<N; i++)); do
  UD=$(cat <<EOF | base64
#!/bin/bash
exec >> /var/log/morgoth-fleet.log 2>&1
cd /home/ubuntu/morgoth-slowing-growth-curves
sudo -u ubuntu bash -lc '
  cd ~/morgoth-slowing-growth-curves && source .venv/bin/activate
  export PILOT_VENV=\$(command -v python) PYTHONPATH=src PYTHONUNBUFFERED=1 MORGOTH_DEVICE=cuda \
         MORGOTH2_DIR=~/morgoth2 RCLONE_BIN=rclone CODE_COMMIT=fleet \
         FLEET_INDEX=$i FLEET_TOTAL=$N S3_OUT=$S3_OUT
  aws s3 cp $S3_MANIFEST /home/ubuntu/manifest.jsonl
  export MANIFEST_LOCAL=/home/ubuntu/manifest.jsonl
  python fleet/batch_worker.py
'
# self-terminate when the slice is done (spot; comment out to keep for inspection)
shutdown -h now
EOF
)
  aws ec2 run-instances --region "$REGION" --image-id "$AMI" --instance-type g4dn.xlarge \
    --instance-market-options 'MarketType=spot' \
    --key-name "$KEY" --security-group-ids "$SG" --subnet-id "$SUBNET" \
    --iam-instance-profile "Name=$IAM_PROFILE" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=120,VolumeType=gp3}' \
    --instance-initiated-shutdown-behavior terminate \
    --user-data "$UD" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=morgoth-fleet-$i}]" \
    --query 'Instances[0].InstanceId' --output text
done
echo "launched $N spot instances. Watch outputs: aws s3 ls $S3_OUT/done/ | wc -l   (target ~13034)"
