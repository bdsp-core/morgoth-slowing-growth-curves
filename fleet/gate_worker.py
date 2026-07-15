"""Fleet entrypoint for the GATE RE-RUN (one AWS spot worker). Drives `scripts/32_gate_rerun_worker.py`.

Mirrors fleet/batch_worker.py's contract exactly — elastic full-manifest walk, S3 `_done` resume, upload
partitions BEFORE the marker, disk-bounded — but for the gate re-run:

  1 s window step (not 5), the FULL 3-class softmax kept per second, Morgoth's zeroing guard DISABLED, and
  independent per-segment P(focal)/P(generalized) from the EEG-level heads on a 30/60/120 s sliding window.
  See docs/gate_rerun_spec.md.

ADDITIVE. The existing v6 run is READ, never written:
    SRC_V6  (read)   .../Growth_curves/segmaster_v6
                       _done/<id>.done                    -> PINS source_edf + sha256 (no re-resolution)
                       segment_summary/eeg_id=<id>/       -> the CANONICAL segment index, so segment_gate
                                                             joins segment_master 1:1 on (eeg_id, segment)
    S3_OUT  (write)  .../Growth_curves/gate_rerun_v1      -> FRESH prefix. window_gate/, segment_gate/, _done/

Two-venv contract (docs/fleet_dependencies.md §4): this driver and scripts/32 run in the REPO venv and never
import torch. The checkpoints are touched only by scripts/shims/eeg_level_sliding.py, in a subprocess under
PILOT_VENV (Morgoth's venv).

Env:
  SRC_V6, S3_OUT, MANIFEST, OUTPUT_ROOT, DYNAMIC=1, SEED, RCLONE_BIN,
  + scripts/32 env: MORGOTH2_DIR, PILOT_VENV, MORGOTH_DEVICE=cuda, CKPT_DIR, PANEL_ROOT
"""
from __future__ import annotations
import hashlib, importlib.util, json, os, shutil, subprocess, tempfile
from pathlib import Path

import pandas as pd

# scripts/32 creates WGATE/SGATE/GDONE under OUTPUT_ROOT at import -> OUTPUT_ROOT must be set first.
_spec = importlib.util.spec_from_file_location(
    "p32", str(Path(__file__).resolve().parents[1] / "scripts" / "32_gate_rerun_worker.py"))
p32 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p32)

SRC_V6 = os.environ["SRC_V6"].rstrip("/")        # the existing run — READ ONLY
S3_OUT = os.environ["S3_OUT"].rstrip("/")        # FRESH prefix — never segmaster_v6
RC = os.environ.get("RCLONE_BIN", "rclone")
NCB = ["--no-check-bucket"]      # rclone: skip CreateBucket before writes (bucket exists; AWS flagged the spam)
MANIFEST = os.environ.get("MANIFEST", "data/manifest/report_manifest_v6.parquet")
# GATE_PILOT>0: acceptance mode. Process exactly N recordings and stop, so the 100-EEG test can be
# validated (scripts/35) before the full run is paid for. The box is left up for inspection.
PILOT = int(os.environ.get("GATE_PILOT", "0"))


def s3_done_set():
    r = subprocess.run([RC, "lsf", f"{S3_OUT}/_done/"], capture_output=True, text=True)
    return {l[:-5] for l in r.stdout.splitlines() if l.endswith(".done")}


def s3_done(eid):
    r = subprocess.run([RC, "lsf", f"{S3_OUT}/_done/{eid}.done"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def fetch_inputs(eid):
    """Pull the two small things scripts/32 needs from the EXISTING v6 run. Returns the .done dict, or None
    if this recording was never successfully processed (its S3 marker is a status string like 'noedf')."""
    d_local = p32.SRC_DONE / f"{eid}.done"
    d_local.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([RC, "copyto", f"{SRC_V6}/_done/{eid}.done", str(d_local)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not d_local.exists():
        return None
    try:
        meta = json.loads(d_local.read_text())
    except json.JSONDecodeError:
        return None                       # a terminal marker ('noedf', 'ambiguous:2of3'): nothing to re-gate
    if not meta.get("source_edf"):
        return None

    ss = p32.SRC_SUMM / f"eeg_id={eid}" / "part.parquet"
    ss.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([RC, "copyto", f"{SRC_V6}/segment_summary/eeg_id={eid}/part.parquet", str(ss)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not ss.exists():
        return None                       # no canonical segment index -> we would have to invent one. Refuse.
    return meta


def upload_success(eid):
    """Partitions FIRST, marker LAST — so a _done in S3 always implies the data is fully there."""
    for sub, dst in ((p32.WGATE, "window_gate"), (p32.SGATE, "segment_gate")):
        f = sub / f"eeg_id={eid}" / "part.parquet"
        if f.exists():
            subprocess.run([RC, *NCB, "copyto", str(f), f"{S3_OUT}/{dst}/eeg_id={eid}/part.parquet"], check=True)
    d = p32.GDONE / f"{eid}.done"
    if d.exists():
        subprocess.run([RC, *NCB, "copyto", str(d), f"{S3_OUT}/_done/{eid}.done"], check=True)


def mark_terminal(eid, status):
    """Permanently unprocessable for the GATE re-run (no v6 outputs, sha mismatch, recording < 30 s).
    Marker so peers skip it forever. Transient errors are NOT marked -> they retry next pass."""
    subprocess.run(["bash", "-lc", f"printf %s {status!r} | {RC} --no-check-bucket rcat {S3_OUT}/_done/{eid}.done"], check=False)
    subprocess.run(["bash", "-lc", f"printf %s {status!r} | {RC} --no-check-bucket rcat {S3_OUT}/_status/{eid}.status"], check=False)


def cleanup_local(eid):
    for sub in (p32.WGATE, p32.SGATE, p32.SRC_SUMM):
        shutil.rmtree(sub / f"eeg_id={eid}", ignore_errors=True)
    (p32.GDONE / f"{eid}.done").unlink(missing_ok=True)
    (p32.GSTAT / f"{eid}.status").unlink(missing_ok=True)
    (p32.SRC_DONE / f"{eid}.done").unlink(missing_ok=True)


def main():
    man = pd.read_parquet(MANIFEST)
    rows = [r for _, r in man.iterrows()]
    seed = os.environ.get("SEED", "0")
    mine = sorted(rows, key=lambda r: hashlib.md5(f"{seed}:{r.eeg_id}".encode()).digest())
    if PILOT:
        # deterministic, representative sample: skip the 1,761 MoE clips (all exactly 15 s -> below the
        # EEG-level head's 30-row CNN floor, so they can only produce NaN and would prove nothing)
        mine = [r for r in mine if not str(r.eeg_id).startswith("MOE_")][:PILOT]
    print(f"gate re-run worker seed={seed}: {len(mine)} EEGs | step={p32.GATE_STEP}s "
          f"contexts={p32.CONTEXTS} guard=DISABLED"
          + (f" | PILOT={PILOT} (acceptance run)" if PILOT else ""), flush=True)
    print(f"  SRC_V6 (read) : {SRC_V6}", flush=True)
    print(f"  S3_OUT (write): {S3_OUT}", flush=True)

    heads = p32.EEGLevelHeads(
        os.environ.get("CKPT_DIR", os.path.join(os.environ.get("MORGOTH2_DIR", ""), "checkpoints")),
        scratch=Path(tempfile.mkdtemp(prefix="eeglvl_")))
    work = Path(tempfile.mkdtemp()); ok = 0
    try:
        while True:
            done = s3_done_set()
            processed = 0
            for m in mine:
                eid = m.eeg_id
                if eid in done or s3_done(eid):
                    continue
                try:
                    meta = fetch_inputs(eid)
                    if meta is None:
                        mark_terminal(eid, "no_v6_outputs")
                        processed += 1
                        continue
                    res = p32.process_one(eid, meta, heads, work)
                    if isinstance(res, dict):
                        upload_success(eid); ok += 1; processed += 1
                        print(f"  OK {eid}: {res['T']:,} windows, {res['n_seg']:,} segments", flush=True)
                    else:
                        mark_terminal(eid, str(res))          # sha_mismatch / noseg — terminal, not transient
                        processed += 1
                        print(f"  {res} {eid}", flush=True)
                except Exception as e:
                    # transient (spot reclaim, S3 blip, OOM): NO marker -> another worker/pass retries it
                    print(f"  FAIL {eid}: {type(e).__name__}: {e}", flush=True)
                finally:
                    cleanup_local(eid)
                    for sub in ("in", "out"):
                        shutil.rmtree(work / sub, ignore_errors=True)
            if PILOT:
                print(f"\nPILOT complete: {ok}/{len(mine)} processed. Box stays up for inspection.\n"
                      f"Validate with:  rclone copy {S3_OUT} ~/gate_check --include '*.parquet' && "
                      f"OUTPUT_ROOT=~/gate_check python scripts/35_validate_gate_output.py", flush=True)
                break
            if processed == 0:
                print(f"full pass added nothing new — manifest covered. this worker did {ok}.", flush=True)
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
