#!/usr/bin/env bash
# progress of the gate re-run
cd "$(dirname "$0")/.."
export AWS_PROFILE=fleet AWS_DEFAULT_REGION=us-east-1
P=s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/gate_rerun_v1
echo "workers up : $(aws ec2 describe-instances --filters 'Name=tag:fleet,Values=morgoth-gate-rerun' 'Name=instance-state-name,Values=pending,running' --query 'length(Reservations[].Instances[])' --output text 2>/dev/null)"
echo "_done      : $(aws s3 ls $P/_done/ --profile bdspwrite 2>/dev/null | wc -l | tr -d ' ') / 27478"
echo "window_gate: $(aws s3 ls $P/window_gate/ --profile bdspwrite 2>/dev/null | wc -l | tr -d ' ')"
L=$(aws s3 ls $P/_logs/ --profile bdspwrite 2>/dev/null | awk '$3>400{print $4}' | tail -1)
echo "--- latest log ($L) ---"
aws s3 cp $P/_logs/$L - --profile bdspwrite 2>/dev/null | grep -E "OK |FAIL|remotes|seed=" | tail -4
