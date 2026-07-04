#!/usr/bin/env bash
# AWS Batch array-task entrypoint: pull manifest + checkpoints + BDSP creds, then run this task's slice.
set -euo pipefail

: "${S3_OUT:?set S3_OUT=s3://bucket/prefix/expansion}"
: "${S3_MANIFEST:?set S3_MANIFEST=s3://bucket/.../manifest.jsonl}"
: "${S3_MODELS:?set S3_MODELS=s3://bucket/.../models  (holds the 6 .pth)}"
: "${BDSP_KEY_ID:?}"; : "${BDSP_KEY_SECRET:?}"     # BDSP opendata read keys (Batch job env / Secrets)

export PILOT_VENV="$(command -v python)"
mkdir -p /opt/scratch /opt/morgoth2/checkpoints ~/.config/rclone

# manifest
aws s3 cp "$S3_MANIFEST" /opt/manifest.jsonl --only-show-errors
export MANIFEST_LOCAL=/opt/manifest.jsonl

# checkpoints (sleep window + gate: NORMAL/SLOWING window + 3 EEG-level aggregators)
for f in ss_hm_1.pth NORMAL.pth NORMAL_EEGlevel.pth SLOWING.pth FOC_SLOWING_EEGlevel.pth GEN_SLOWING_EEGlevel.pth; do
  aws s3 cp "$S3_MODELS/$f" "/opt/morgoth2/checkpoints/$f" --only-show-errors
done

# rclone remote 'bdsp' for reading the source EDFs (bdsp-opendata-repository/EEG)
cat > ~/.config/rclone/rclone.conf <<EOF
[bdsp]
type = s3
provider = AWS
access_key_id = ${BDSP_KEY_ID}
secret_access_key = ${BDSP_KEY_SECRET}
region = us-east-1
EOF

export CODE_COMMIT="${CODE_COMMIT:-fleet}"
echo "GPU check:"; python -c "import torch;print('cuda',torch.cuda.is_available())"
exec python /opt/morgoth-slowing-growth-curves/fleet/batch_worker.py
