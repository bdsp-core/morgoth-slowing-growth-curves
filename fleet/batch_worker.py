"""Fleet entrypoint (one AWS Batch array task). Processes this task's strided slice of the manifest
and writes each recording's outputs to S3, with S3 .done markers for cross-fleet resumability.

Reuses the VALIDATED local worker `process_one` (scripts/30) unchanged — same features + sleep stages
+ focal/gen/normal gate + provenance — then uploads the per-recording files to S3.

Env:
  MANIFEST_LOCAL          path to the manifest.jsonl (pulled from S3 by the entrypoint)
  S3_OUT                  s3://bucket/prefix  (results root; e.g. .../morgoth-slowing/expansion)
  AWS_BATCH_JOB_ARRAY_INDEX / ARRAY_SIZE   which strided slice this task handles
  + the same env the worker needs: MORGOTH2_DIR, PILOT_VENV, PILOT_SCRATCH, MORGOTH_DEVICE=cuda,
    RCLONE_BIN, CODE_COMMIT, RUN_GATE=1, GATE_STEP
"""
from __future__ import annotations
import os, json, subprocess, tempfile, importlib.util, shutil
from pathlib import Path
import pandas as pd

_spec = importlib.util.spec_from_file_location("p30", str(Path(__file__).resolve().parents[1] / "scripts" / "30_ingest_worker.py"))
p30 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p30)

S3_OUT = os.environ["S3_OUT"].rstrip("/")   # rclone remote path, e.g. bdsp:bucket/prefix/expansion
RC = os.environ.get("RCLONE_BIN", "rclone")  # BDSP-keyed remote handles read AND write (same bucket)
# stride index/size: AWS Batch array vars, else plain spot-fleet FLEET_INDEX/FLEET_TOTAL
IDX = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", os.environ.get("FLEET_INDEX", "0")))
SIZE = int(os.environ.get("ARRAY_SIZE", os.environ.get("AWS_BATCH_JOB_ARRAY_SIZE", os.environ.get("FLEET_TOTAL", "1"))))
SUBS = [("features", ".parquet"), ("stages", ".csv"), ("provenance", ".json"), ("gate", ".json")]


def s3_done(rid):
    r = subprocess.run([RC, "lsf", f"{S3_OUT}/done/{rid}.done"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def upload(rid):
    for sub, ext in SUBS:
        f = p30.OUTDIR / sub / f"{rid}{ext}"
        if f.exists():
            subprocess.run([RC, "copyto", str(f), f"{S3_OUT}/{sub}/{rid}{ext}"], check=False)
    subprocess.run(["bash", "-lc", f"echo done | {RC} rcat {S3_OUT}/done/{rid}.done"], check=False)


def main():
    rows = [json.loads(l) for l in open(os.environ["MANIFEST_LOCAL"]) if l.strip()]
    mine = rows[IDX::SIZE]                              # strided slice -> even label mix per task
    print(f"task {IDX}/{SIZE}: {len(mine)} of {len(rows)} recordings")
    work = Path(tempfile.mkdtemp())
    ok = 0
    try:
        for row in mine:
            r = pd.Series(row)
            rid = f"{r.SiteID}{r.pid}_{r.date}"
            if s3_done(rid):
                continue
            try:
                res = p30.process_one(r, work)
                if isinstance(res, dict):
                    upload(rid); ok += 1
                    print(f"  DONE {rid} ({res['usable']}/{res['total']})  [{ok}]")
                else:
                    print(f"  {res} {rid}")
            except Exception as e:
                print(f"  FAIL {rid}: {type(e).__name__}: {e}")
            finally:
                for sub in ("in", "out"):
                    shutil.rmtree(work / sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"task {IDX} done: {ok} recordings uploaded to {S3_OUT}")


if __name__ == "__main__":
    main()
