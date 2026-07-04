#!/usr/bin/env bash
# Stage the 6 checkpoints the fleet needs into YOUR S3 bucket (run once, with your AWS creds — e.g. in
# the console CloudShell). 5 gate checkpoints already live in the BDSP credentialed bucket; ss_hm_1.pth
# (sleep window) is on the pilot box (and in Box) — copy it up too.
set -euo pipefail
: "${BUCKET:?set BUCKET=s3://your-bucket/morgoth-slowing}"
SRC=s3://bdsp-opendata-credentialed/morgoth2/models/202605/morgoth      # BDSP (needs BDSP read creds)

for f in NORMAL.pth NORMAL_EEGlevel.pth SLOWING.pth FOC_SLOWING_EEGlevel.pth GEN_SLOWING_EEGlevel.pth; do
  aws s3 cp "$SRC/$f" "$BUCKET/models/$f"
done
echo "ss_hm_1.pth is NOT in the BDSP models dir — copy it from the pilot box or Box:"
echo "  scp -i morgoth-pilot-key.pem ubuntu@<box>:~/morgoth2/checkpoints/ss_hm_1.pth ."
echo "  aws s3 cp ss_hm_1.pth $BUCKET/models/ss_hm_1.pth"
aws s3 ls "$BUCKET/models/"
