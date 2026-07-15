#!/usr/bin/env bash
# ONE COMMAND to (re)launch the gate re-run after the bundle fix. Safe to run repeatedly: the elastic
# workers skip anything already _done in S3, so this only ever covers what is left.
#   bash fleet/RELAUNCH_WHEN_BACK.sh          # 16 on-demand workers (reliable; ~$8/hr for the fleet)
#   SPOT=1 bash fleet/RELAUNCH_WHEN_BACK.sh   # try spot first (~3x cheaper if capacity exists)
set -uo pipefail
cd "$(dirname "$0")/.."
N=${1:-16}
S=s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/code_gate_rerun
# make sure the bundle in S3 contains the s3: remote before spending a cent
if ! aws s3 cp "$S/bundle.tgz" /tmp/_chk.tgz --profile bdspwrite --only-show-errors 2>/dev/null || \
   ! tar tzf /tmp/_chk.tgz 2>/dev/null | grep -q "fleet/rclone_s3.conf"; then
  echo "PUBLISHING bundle (it is missing rclone_s3.conf) ..."
  tar czf /tmp/_b.tgz src scripts/32_gate_rerun_worker.py scripts/35_validate_gate_output.py \
      scripts/shims fleet/gate_worker.py fleet/rclone_s3.conf data/manifest/report_manifest_v6.parquet
  aws s3 cp /tmp/_b.tgz "$S/bundle.tgz" --profile bdspwrite --only-show-errors
fi
echo "bundle OK. launching $N workers."
if [ "${SPOT:-0}" = "1" ]; then ./fleet/scale_gate_rerun.sh "$N"; else ONDEMAND=1 ./fleet/scale_gate_rerun.sh "$N"; fi
echo
echo "watch progress:  bash fleet/STATUS.sh"
