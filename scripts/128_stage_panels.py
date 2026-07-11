"""Step 3b — stage the panel EEG source files into ONE canonical tree so they resolve on the fleet.

The manifest gives every panel row a RELATIVE `source_path` (occasionnoise/<fid>.edf, moe/<event>.mat)
that the worker resolves against `PANEL_ROOT` (scripts/31 `fetch_panel`). This script copies the panel
files out of the local scratchpad (where they were downloaded/repaired) into `<stage>/` under exactly
those relative paths, so the SAME tree is:
  - a local `PANEL_ROOT` for pilot re-runs:      PANEL_ROOT=$(pwd)/panels
  - the thing you upload once to S3 for the fleet: aws s3 sync panels/ s3://<bucket>/panels/  ; then
                                                   PANEL_ROOT=s3://<bucket>/panels on the box.

Only files referenced by the frozen manifest are staged (icare_* MoE events are already excluded there).
Idempotent: skips files already staged with the same size.

Run: PYTHONPATH=src python scripts/128_stage_panels.py [--manifest ...v5.parquet] [--stage panels]
"""
from __future__ import annotations
import argparse, os, shutil
from pathlib import Path
import pandas as pd

SCRATCH = os.environ.get("PANEL_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")


def legacy_path(row):
    """Where the panel file currently lives in the local scratchpad."""
    name = Path(row.source_path).name
    if row.source_type == "edf_direct":
        return Path(SCRATCH) / "moe" / "occ" / "edf" / name
    if row.source_type == "mat_v73":
        return Path(SCRATCH) / "events_raw" / name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifest/report_manifest_v5.parquet")
    ap.add_argument("--stage", default="panels")
    a = ap.parse_args()
    man = pd.read_parquet(a.manifest)
    panels = man[man.get("src", "") == "panel"].copy()
    stage = Path(a.stage); staged = missing = skipped = 0
    miss = []
    for row in panels.itertuples():
        src = legacy_path(row)
        dst = stage / str(row.source_path)
        if src is None or not src.exists():
            missing += 1; miss.append(str(row.eeg_id)); continue
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            skipped += 1; continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst); staged += 1
    print(f"panel rows {len(panels)} | staged {staged} | already-present {skipped} | MISSING {missing}")
    if miss:
        print("  missing (not in scratchpad):", ", ".join(miss[:10]), "..." if len(miss) > 10 else "")
    tot = sum(f.stat().st_size for f in stage.rglob("*") if f.is_file()) if stage.exists() else 0
    print(f"stage tree: {stage}/  ({tot/1e9:.2f} GB)")
    print("next: aws s3 sync %s/ s3://<run-bucket>/panels/   then  PANEL_ROOT=s3://<run-bucket>/panels" % a.stage)


if __name__ == "__main__":
    main()
