"""Fix oversight #1: stage the ORIGINAL abnormal recordings (never staged — the original pipeline
staged only normals). Their raw signal is on S3 as 10-min segments_raw .mat clips, already in the
stager's format. Pull -> ss_hm_1 -> per-window stages -> data/derived/original_abnormal_stages/<rid>.csv.
Resumable via .done markers. Run on the GPU box.

Run: PYTHONPATH=src python scripts/36_stage_original_abnormals.py [N_per_label]   (default all)
"""
from __future__ import annotations
import os, sys, json, time, subprocess, tempfile, shutil, importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("p26", str(Path(__file__).with_name("26_slowing_ingest_pilot.py")))
p26 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p26)

BASE = "bdsp-opendata-credentialed/morgoth1/data/internal_dataset"
SRC = {"focal_slow": f"{BASE}/FOCALSLOWING/segments_raw",
       "general_slow": f"{BASE}/GENSLOWING/segments_raw"}
OUT = Path("data/derived/original_abnormal_stages"); DONE = OUT / "done"
OUT.mkdir(parents=True, exist_ok=True); DONE.mkdir(exist_ok=True)
PROG = p26.OUT / "stage_abnormals_progress.jsonl"


def _prog(**k):
    try:
        with open(PROG, "a") as fh: fh.write(json.dumps({"t": time.time(), **k}) + "\n")
    except Exception: pass


def listing(prefix):
    r = subprocess.run([p26.RC, "lsf", f"bdsp:{prefix}/"], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.endswith(".mat")]


def main(n_per=None):
    files = {lab: listing(pfx) for lab, pfx in SRC.items()}
    # interleave labels
    order, i = [], 0
    labs = list(files)
    while any(i < len(files[l]) for l in labs):
        for l in labs:
            if i < len(files[l]) and (n_per is None or i < n_per):
                order.append((l, files[l][i]))
        i += 1
    total = len(order)
    done0 = len(list(DONE.glob("*.done")))
    _prog(event="start", total=total + done0, done=done0)
    print(f"{total} abnormal clips to stage ({done0} already done)")
    work = Path(tempfile.mkdtemp()); n_ok = done0
    try:
        for lab, fn in order:
            rid = fn[:-4].replace("sub-", "")
            if (DONE / f"{rid}.done").exists():
                continue
            sin, sout = work / "in", work / "out"
            for d in (sin, sout): shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
            try:
                p26.rclone(["copy", f"bdsp:{SRC[lab]}/{fn}", str(sin)])
                p26.stage_dir(str(sin), str(sout))
                csv = next(sout.glob("*.csv"), None)
                if csv:
                    shutil.copy(csv, OUT / f"{rid}.csv")
                    (DONE / f"{rid}.done").touch(); n_ok += 1
                    if n_ok % 25 == 0:
                        print(f"  staged {n_ok}/{total + done0}");
                    _prog(event="done", rid=rid, done=n_ok, label=lab)
            except Exception as e:
                print(f"  FAIL {rid}: {type(e).__name__}: {e}")
                _prog(event="fail", rid=rid, err=type(e).__name__)
            finally:
                for d in ("in", "out"): shutil.rmtree(work / d, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    _prog(event="finish", done=n_ok)
    print(f"done: {n_ok} abnormal recordings staged -> {OUT}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
