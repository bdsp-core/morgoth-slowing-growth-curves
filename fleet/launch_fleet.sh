#!/usr/bin/env bash
# One-command-ish fleet launch for the full slowing-ingestion wave on AWS Batch (spot GPU).
# UNTESTED ON AWS (author had no EC2 creds) — logic is standard; review IAM roles + the budget before
# running. Run from a machine with `aws` configured for account 278057567389 in us-east-1 (e.g. the
# CloudShell in your console, or your Mac after `aws configure`). See fleet/README.md for the full runbook.
set -euo pipefail

# ---- EDIT THESE ---------------------------------------------------------------------------------
REGION=us-east-1
ACCOUNT=278057567389
BUCKET=s3://bdsp-brandon-morgoth-slowing            # a bucket YOU own in us-east-1 for outputs+manifest
N=15000                                             # recordings to ingest (targeted balanced subset)
PER_TASK=60                                         # recordings per Batch array task (~5-8h each)
MAX_VCPUS=200                                       # fleet ceiling (each g4dn.xlarge = 4 vCPU -> ~50 boxes)
BUDGET_USD=800                                      # AWS Budgets alarm threshold
# IAM roles you must have (see README §IAM): Batch service role, EC2 instance role (S3 rw + BDSP read),
# ECS task execution role. Set their ARNs/names:
BATCH_SERVICE_ROLE=arn:aws:iam::$ACCOUNT:role/AWSBatchServiceRole
INSTANCE_PROFILE=arn:aws:iam::$ACCOUNT:instance-profile/ecsInstanceRole
EXEC_ROLE=arn:aws:iam::$ACCOUNT:role/ecsTaskExecutionRole
JOB_ROLE=arn:aws:iam::$ACCOUNT:role/morgothSlowingJobRole        # S3 rw to $BUCKET
SUBNETS=subnet-xxxxxxxx                             # a subnet with internet/S3 access
SG=sg-xxxxxxxx                                      # security group
BDSP_KEY_ID=REDACTED; BDSP_KEY_SECRET=REDACTED      # from AWSKeys/bdsp_opendata_write_accessKeys.csv
# -------------------------------------------------------------------------------------------------

REPO_ECR=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/morgoth-slowing:latest
NARRAY=$(( (N + PER_TASK - 1) / PER_TASK ))

echo ">>> [1/6] build clean context + image"
BUILD=$(mktemp -d)
rsync -a --exclude '.venv' --exclude '.git' --exclude 'data' --exclude 'results' \
      ~/Desktop/GithubRepos/morgoth-slowing-growth-curves "$BUILD/"
rsync -a --exclude '.venv' --exclude '.git' --exclude 'checkpoints' --exclude 'data' \
      ~/Desktop/GithubRepos/morgoth2 "$BUILD/"
docker build -t morgoth-slowing:latest -f "$BUILD/morgoth-slowing-growth-curves/fleet/Dockerfile" "$BUILD"

echo ">>> [2/6] push to ECR"
aws ecr describe-repositories --repository-names morgoth-slowing --region $REGION >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name morgoth-slowing --region $REGION >/dev/null
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "${REPO_ECR%/*}"
docker tag morgoth-slowing:latest "$REPO_ECR"; docker push "$REPO_ECR"

echo ">>> [3/6] manifest + models -> S3"
aws s3 mb "$BUCKET" --region $REGION 2>/dev/null || true
PYTHONPATH=src python fleet/make_manifest.py "$N" fleet/manifest.jsonl
aws s3 cp fleet/manifest.jsonl "$BUCKET/manifest.jsonl"
echo "  (ensure the 6 checkpoints are at $BUCKET/models/ — run fleet/stage_models.sh once)"

echo ">>> [4/6] Batch compute env + queue (spot g4dn.xlarge)"
cat > /tmp/ce.json <<JSON
{ "type":"MANAGED","state":"ENABLED",
  "computeResources":{"type":"SPOT","allocationStrategy":"SPOT_CAPACITY_OPTIMIZED",
    "minvCpus":0,"maxvCpus":$MAX_VCPUS,"desiredvCpus":0,
    "instanceTypes":["g4dn.xlarge"],"subnets":["$SUBNETS"],"securityGroupIds":["$SG"],
    "instanceRole":"$INSTANCE_PROFILE"}, "serviceRole":"$BATCH_SERVICE_ROLE" }
JSON
aws batch create-compute-environment --compute-environment-name morgoth-slowing-ce \
  --cli-input-json file:///tmp/ce.json --region $REGION 2>/dev/null || echo "  (compute env may exist)"
sleep 20
aws batch create-job-queue --job-queue-name morgoth-slowing-q --priority 1 --state ENABLED \
  --compute-environment-order order=1,computeEnvironment=morgoth-slowing-ce --region $REGION 2>/dev/null || echo "  (queue may exist)"

echo ">>> [5/6] job definition (GPU) + submit array"
cat > /tmp/jd.json <<JSON
{ "jobDefinitionName":"morgoth-slowing-jd","type":"container",
  "containerProperties":{"image":"$REPO_ECR","vcpus":4,"memory":15000,
    "resourceRequirements":[{"type":"GPU","value":"1"}],
    "executionRoleArn":"$EXEC_ROLE","jobRoleArn":"$JOB_ROLE",
    "environment":[
      {"name":"S3_OUT","value":"$BUCKET/expansion"},
      {"name":"S3_MANIFEST","value":"$BUCKET/manifest.jsonl"},
      {"name":"S3_MODELS","value":"$BUCKET/models"},
      {"name":"ARRAY_SIZE","value":"$NARRAY"},
      {"name":"BDSP_KEY_ID","value":"$BDSP_KEY_ID"},
      {"name":"BDSP_KEY_SECRET","value":"$BDSP_KEY_SECRET"} ]}}
JSON
aws batch register-job-definition --cli-input-json file:///tmp/jd.json --region $REGION >/dev/null
aws batch submit-job --job-name morgoth-slowing-run --job-queue morgoth-slowing-q \
  --job-definition morgoth-slowing-jd --array-properties size=$NARRAY --region $REGION

echo ">>> [6/6] budget guardrail (\$$BUDGET_USD)"
cat > /tmp/budget.json <<JSON
{ "BudgetName":"morgoth-slowing","BudgetLimit":{"Amount":"$BUDGET_USD","Unit":"USD"},
  "TimeUnit":"MONTHLY","BudgetType":"COST" }
JSON
aws budgets create-budget --account-id $ACCOUNT --budget file:///tmp/budget.json 2>/dev/null || echo "  (budget may exist)"

echo "Submitted array of $NARRAY tasks x $PER_TASK recordings = ~$N. Watch: aws batch list-jobs --job-queue morgoth-slowing-q --region $REGION"
