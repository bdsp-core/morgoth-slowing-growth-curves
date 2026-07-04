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
import os, json, subprocess, tempfile, importlib.util, shutil, hashlib
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


def upload_done_only(rid):
    """Mark an unprocessable recording (noedf / too-short) done so peers/passes don't retry it forever."""
    subprocess.run(["bash", "-lc", f"echo noout | {RC} rcat {S3_OUT}/done/{rid}.done"], check=False)


def _rid(row):
    r = pd.Series(row)
    return f"{r.SiteID}{r.pid}_{r.date}"


def s3_done_set():
    """One bulk listing of all .done markers -> set of rids (cheap: single S3 LIST vs per-recording HEAD)."""
    r = subprocess.run([RC, "lsf", f"{S3_OUT}/done/"], capture_output=True, text=True)
    return {l[:-5] for l in r.stdout.splitlines() if l.endswith(".done")}


def main():
    rows = [json.loads(l) for l in open(os.environ["MANIFEST_LOCAL"]) if l.strip()]
    dynamic = os.environ.get("DYNAMIC", "0") == "1"
    if dynamic:
        # ELASTIC mode: each worker walks the WHOLE manifest in its own hash-shuffled order, skipping
        # anything already .done. Any number of workers fully covers the manifest; spot interruptions
        # self-heal (a dead worker's un-done recordings get picked up by survivors); a quota increase
        # just means launching more workers. Repeats passes until a full pass adds nothing new.
        seed = os.environ.get("SEED", str(IDX))
        mine = sorted(rows, key=lambda r: hashlib.md5(f"{seed}:{_rid(r)}".encode()).digest())
        print(f"dynamic worker seed={seed}: walking {len(rows)} recordings, S3_OUT={S3_OUT}", flush=True)
    else:
        mine = rows[IDX::SIZE]                          # strided slice -> even label mix per task
        print(f"task {IDX}/{SIZE}: {len(mine)} of {len(rows)} recordings", flush=True)
    work = Path(tempfile.mkdtemp())
    ok = 0
    try:
        while True:
            done = s3_done_set()                        # refresh once per pass
            processed = 0
            for row in mine:
                rid = _rid(row)
                if rid in done or s3_done(rid):         # bulk set + last-moment recheck (avoid dup work)
                    continue
                try:
                    res = p30.process_one(pd.Series(row), work)
                    if isinstance(res, dict):
                        upload(rid); ok += 1; processed += 1
                        print(f"  DONE {rid} ({res['usable']}/{res['total']})  [{ok}]", flush=True)
                    else:
                        upload_done_only(rid)           # unprocessable (noedf/short) -> mark done so peers skip
                        print(f"  {res} {rid} (marked done)", flush=True)
                except Exception as e:
                    print(f"  FAIL {rid}: {type(e).__name__}: {e}", flush=True)
                finally:
                    for sub in ("in", "out"):
                        shutil.rmtree(work / sub, ignore_errors=True)
            if not dynamic or processed == 0:           # stride: one pass. dynamic: until a pass adds nothing
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"worker done: {ok} recordings uploaded to {S3_OUT}", flush=True)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
