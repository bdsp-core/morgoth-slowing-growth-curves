"""Fleet entrypoint (one AWS spot worker). Drives the CANONICAL worker `scripts/31_segment_master_worker.py`
over the frozen v6 manifest (27,524 EEGs) and streams each recording's per-eeg_id outputs to S3, with S3
`_done` markers for cross-fleet resumability.

This REPLACES the legacy expansion worker (scripts/30 + features/stages/gate/provenance layout, discarded).
It runs `scripts/31::process_one` unchanged — features + van Putten + Morgoth stage + per-segment/EEG-level
gate — which writes the frozen schema:
  segment_master/eeg_id=<id>/part.parquet   (per segment×channel)
  segment_summary/eeg_id=<id>/part.parquet  (per segment: stage, artifact, p_slowing, whole-head vP)
  _done/<id>.done                            (success + stats + sha256)
then this worker uploads those to S3 and removes them locally (disk-bounded).

Two-venv contract (docs/fleet_dependencies.md §4): the WORKER runs in this repo's venv; the Morgoth
subprocess runs in Morgoth's own venv via PILOT_VENV=$MORGOTH2_DIR/.venv/bin/python. Set that + the aws CLI
on PATH in the entrypoint.

Env:
  S3_OUT        rclone remote path, FRESH prefix (e.g. bdsp:<bucket>/.../Growth_curves/segmaster_v6)
  MANIFEST      v6 parquet (default data/manifest/report_manifest_v6.parquet — tracked in the repo/AMI)
  OUTPUT_ROOT   local scratch where scripts/31 writes before upload (cleaned per recording)
  DYNAMIC=1     elastic full-manifest walk (skip S3-_done); SEED for the per-worker shuffle order
  RCLONE_BIN    BDSP-keyed remote (read AND write same credentialed bucket)
  + scripts/31 env: MORGOTH2_DIR, PILOT_VENV, MORGOTH_DEVICE=cuda, RUN_GATE=1, GATE_STEP, PANEL_ROOT
"""
from __future__ import annotations
import os, subprocess, tempfile, importlib.util, shutil, hashlib
from pathlib import Path
import pandas as pd

# scripts/31 creates OUT/SUMM/DONE/STATUS under OUTPUT_ROOT at import time -> OUTPUT_ROOT must be set first.
_spec = importlib.util.spec_from_file_location(
    "p31", str(Path(__file__).resolve().parents[1] / "scripts" / "31_segment_master_worker.py"))
p31 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p31)

S3_OUT = os.environ["S3_OUT"].rstrip("/")          # FRESH prefix — never the discarded expansion tree
RC = os.environ.get("RCLONE_BIN", "rclone")
MANIFEST = os.environ.get("MANIFEST", "data/manifest/report_manifest_v6.parquet")
IDX = int(os.environ.get("FLEET_INDEX", "0"))
SIZE = int(os.environ.get("FLEET_TOTAL", "1"))


def s3_done_set():
    """One bulk S3 LIST of all _done markers -> set of eeg_ids (cheap vs per-recording HEAD)."""
    r = subprocess.run([RC, "lsf", f"{S3_OUT}/_done/"], capture_output=True, text=True)
    return {l[:-5] for l in r.stdout.splitlines() if l.endswith(".done")}


def s3_done(eid):
    r = subprocess.run([RC, "lsf", f"{S3_OUT}/_done/{eid}.done"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def upload_success(eid):
    """Upload the per-eeg_id partitions THEN the _done marker last, so a _done in S3 always implies the
    data is fully present (a peer that sees _done and skips never misses partitions)."""
    sm = p31.OUT / f"eeg_id={eid}" / "part.parquet"
    ss = p31.SUMM / f"eeg_id={eid}" / "part.parquet"
    if sm.exists():
        subprocess.run([RC, "copyto", str(sm), f"{S3_OUT}/segment_master/eeg_id={eid}/part.parquet"], check=True)
    if ss.exists():
        subprocess.run([RC, "copyto", str(ss), f"{S3_OUT}/segment_summary/eeg_id={eid}/part.parquet"], check=True)
    done = p31.DONE / f"{eid}.done"
    if done.exists():
        subprocess.run([RC, "copyto", str(done), f"{S3_OUT}/_done/{eid}.done"], check=True)


def mark_terminal(eid, status):
    """A permanently-unprocessable recording (noedf / nopanelfile / ambiguous): write an S3 _done marker
    (body = the status) so peers/passes skip it forever, plus a _status record. Transient errors are NOT
    marked -> they retry on the next pass."""
    subprocess.run(["bash", "-lc", f"printf %s {status!r} | {RC} rcat {S3_OUT}/_done/{eid}.done"], check=False)
    subprocess.run(["bash", "-lc", f"printf %s {status!r} | {RC} rcat {S3_OUT}/_status/{eid}.status"], check=False)


def cleanup_local(eid):
    """Remove this recording's local partitions + sidecars after upload (the box holds only in-flight work)."""
    shutil.rmtree(p31.OUT / f"eeg_id={eid}", ignore_errors=True)
    shutil.rmtree(p31.SUMM / f"eeg_id={eid}", ignore_errors=True)
    (p31.DONE / f"{eid}.done").unlink(missing_ok=True)
    (p31.STATUS / f"{eid}.status").unlink(missing_ok=True)


def main():
    man = pd.read_parquet(MANIFEST)
    man["_st"] = man.get("source_type", "bids").fillna("bids")
    rows = [r for _, r in man.iterrows()]
    dynamic = os.environ.get("DYNAMIC", "1") == "1"
    if dynamic:
        # ELASTIC: each worker walks the WHOLE manifest in its own hash-shuffled order, skipping anything
        # already _done in S3. #workers is decoupled from coverage; spot reclaims self-heal; a quota bump
        # just means launching more workers. Repeats passes until a full pass adds nothing new.
        seed = os.environ.get("SEED", str(IDX))
        mine = sorted(rows, key=lambda r: hashlib.md5(f"{seed}:{r.eeg_id}".encode()).digest())
        print(f"dynamic worker seed={seed}: walking {len(mine)} EEGs, S3_OUT={S3_OUT}", flush=True)
    else:
        mine = rows[IDX::SIZE]
        print(f"strided task {IDX}/{SIZE}: {len(mine)} of {len(rows)} EEGs", flush=True)
    work = Path(tempfile.mkdtemp()); ok = 0
    try:
        while True:
            done = s3_done_set()                             # refresh once per pass (bulk LIST)
            processed = 0
            for m in mine:
                eid = m.eeg_id
                if eid in done or s3_done(eid):              # bulk set + last-moment recheck (avoid dup work)
                    continue
                try:
                    res = p31.process_one(m, work)
                    if isinstance(res, dict):
                        upload_success(eid); ok += 1; processed += 1
                        print(f"  DONE {eid}: {res['n_seg']} seg, {res['hours']}h, stages={res['stages']}  [{ok}]", flush=True)
                    elif res != "skip":
                        mark_terminal(eid, res); processed += 1  # noedf / nopanelfile -> skip forever
                        print(f"  {res} {eid} (marked done)", flush=True)
                except Exception as e:
                    print(f"  FAIL {eid}: {type(e).__name__}: {e}", flush=True)  # un-done -> retried next pass
                finally:
                    cleanup_local(eid)
                    for sub in ("in", "out"):
                        shutil.rmtree(work / sub, ignore_errors=True)
            if not dynamic or processed == 0:                # stride: one pass. dynamic: until a pass adds 0
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"worker done: {ok} EEGs uploaded to {S3_OUT}", flush=True)


if __name__ == "__main__":
    main()
