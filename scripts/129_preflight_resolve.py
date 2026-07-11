"""Pre-flight EDF resolution — prove every BIDS manifest row maps to ONE real EDF on S3 BEFORE the fleet
spends compute (addresses: the manifest must be known-good; unresolvable rows never reach the run).

For each row it runs the SAME decision the worker uses (`decide_edf` imported from scripts/31 — single
source of truth), but with no download/featurize: list each subject ONCE, read scans.tsv only for
multi-session subjects, in parallel across subjects. Records per row: resolved / resolved_path /
resolve_reason (single | sec-match | day-match | noedf | ambiguous:NofM).

`resolve_rows(df)` is reused by scripts/130 to resolve replacement candidates from the pool.

Run: PYTHONPATH=src python scripts/129_preflight_resolve.py [--manifest ...v5.parquet] [--threads 24]
"""
from __future__ import annotations
import argparse, importlib.util, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FTimeout
from pathlib import Path
import pandas as pd

_spec = importlib.util.spec_from_file_location("w31", "scripts/31_segment_master_worker.py")
w31 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(w31)
RC = w31.RC


def _list_subject(base):
    """One rclone listing of a subject dir -> EDF rel-paths (cached per subject)."""
    out = subprocess.run([RC, "lsf", base, "--recursive", "--include", "*.edf"],
                         capture_output=True, text=True, timeout=180)
    return [l for l in out.stdout.splitlines() if l.endswith(".edf")]


def _resolve_subject(base, rows):
    """Resolve every manifest row for one subject from a single listing."""
    try:
        edfs = _list_subject(base)
    except Exception as e:
        return [(r.eeg_id, False, None, f"listerr:{type(e).__name__}") for r in rows]
    acq_fn = lambda rel: w31._acq_time(base, rel)                  # scans.tsv acq_time per session
    res = []
    for r in rows:
        try:
            path, reason = w31.decide_edf(base, r.bids_task, r.eeg_datetime, edfs, acq_fn)
        except Exception as e:
            path, reason = None, f"err:{type(e).__name__}"
        res.append((r.eeg_id, path is not None, path, reason))
    return res


def resolve_rows(df: pd.DataFrame, threads=16, deadline=1800) -> pd.DataFrame:
    """Resolve a set of BIDS rows (needs eeg_id, source_subject_dir, bids_task, eeg_datetime).
    Returns [eeg_id, resolved, resolved_path, resolve_reason]. Parallel across subjects, using
    as_completed + a hard DEADLINE so a single stalled S3 call can never block the whole batch (a
    stalled subject is simply abandoned — safe because callers over-draw candidates)."""
    groups = {}
    for r in df.itertuples():
        groups.setdefault(r.source_subject_dir, []).append(r)
    ex = ThreadPoolExecutor(max_workers=threads)
    futs = {ex.submit(_resolve_subject, base, rows): base for base, rows in groups.items()}
    out, done = [], 0
    try:
        for f in as_completed(futs, timeout=deadline):
            try:
                out.extend(f.result())
            except Exception:
                pass
            done += 1
            if done % 500 == 0:
                print(f"  resolved {done}/{len(futs)} subjects", flush=True)
    except FTimeout:
        print(f"  DEADLINE {deadline}s hit: {done}/{len(futs)} subjects done; "
              f"abandoning {len(futs) - done} stalled subjects", flush=True)
    ex.shutdown(wait=False, cancel_futures=True)      # don't block on stalled S3 subprocesses
    return pd.DataFrame(out, columns=["eeg_id", "resolved", "resolved_path", "resolve_reason"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifest/report_manifest_v5.parquet")
    ap.add_argument("--threads", type=int, default=24)
    ap.add_argument("--out", default="data/manifest/preflight_resolution.parquet")
    a = ap.parse_args()
    man = pd.read_parquet(a.manifest)
    bd = man[man.get("src", "").isin(["cohort", "expansion", "backfill"])].copy()
    print(f"resolving {len(bd)} BIDS rows across {bd.source_subject_dir.nunique()} subjects "
          f"({a.threads} threads)…", flush=True)
    res = resolve_rows(bd, a.threads)
    res.to_parquet(a.out, index=False)
    n_ok = int(res.resolved.sum())
    print(f"\nRESOLVED {n_ok}/{len(res)} ({100 * n_ok / len(res):.1f}%)  -> {a.out}")
    print("by reason:")
    for k, v in res.resolve_reason.str.split(":").str[0].value_counts().items():
        print(f"  {k:14} {v}")
    # coverage of the DROPS by src (what needs replacing to hold N)
    drop = res[~res.resolved].merge(bd[["eeg_id", "src"]], on="eeg_id")
    if len(drop):
        print("drops by src:", dict(drop.src.value_counts()))


if __name__ == "__main__":
    main()
