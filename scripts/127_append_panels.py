"""Step 3 (panels) — append the expert-panel EEGs (OccasionNoise + MoE) to the frozen manifest for the
human-ceiling aim (SAP §3.6, §8.3). Produces report_manifest_v5.

Panels are SEPARATE datasets, not BDSP BIDS, so they carry `source_type` + `source_path` (the worker
resolves BIDS via `source_subject_dir`; for panels it pulls the given file directly):
  OccasionNoise — 100 fid-numbered EDFs (moe/occ/edf/<fid>.edf), category from Occasion.xlsx. `source_type
                  = edf_direct`. NOTE: these EDF headers are non-compliant (shifted-date) and need a header
                  fix before load_edf_referential reads them (see below).
  MoE           — ~1,761 events keyed {pid}_{datetime}; BDSP recordings. `source_type = mat_v73` (the event
                  .mat are MATLAB v7.3/HDF5). `icare_*` cardiac-arrest events excluded (SAP §3.6).

Panel loaders are IMPLEMENTED + validated (src/morgoth_slowing/io/panels.py): OccasionNoise EDF header
repair + MNE read; MoE v7.3 .mat via h5py (one 15-s segment). The worker (scripts/31) branches on
`source_type` (bids / edf_direct / mat_v73) and featurizes panels through the SAME pipeline. Validated on a
mixed pilot (3 bids + 3 OccasionNoise + 3 MoE) → valid segment_master + gate for all three.

Run: PYTHONPATH=src python scripts/127_append_panels.py  [--scratch <dir>]
"""
from __future__ import annotations
import argparse, os, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

DIR = Path("data/manifest")
SCRATCH = os.environ.get("PANEL_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")


def occasion_rows():
    f = Path(SCRATCH) / "moe" / "occ" / "Occasion.xlsx"
    if not f.exists():
        print("  OccasionNoise: Occasion.xlsx not found — skipped"); return pd.DataFrame()
    o = pd.read_excel(f)
    edfdir = Path(SCRATCH) / "moe" / "occ" / "edf"
    rows = []
    for _, r in o.iterrows():
        fid = str(r["fid"])
        # Reference the ORIGINAL edf; the worker's header repair (_repair_edf) is idempotent, so we
        # upload one canonical file per fid and let the box fix the header on read.
        rows.append({"eeg_id": f"ON_{fid}", "patient_id": f"ON_{fid}", "src": "panel",
                     "panel": True, "panel_set": "occasionnoise", "role": "panel",
                     "source_type": "edf_direct", "source_path": f"occasionnoise/{fid}.edf",  # relative to PANEL_ROOT
                     "occasion_category": str(r.get("category", ""))})
    return pd.DataFrame(rows)


def moe_rows():
    f = Path(SCRATCH) / "moe_event_band_feats.parquet"
    if not f.exists():
        print("  MoE: moe_event_band_feats.parquet not found — skipped"); return pd.DataFrame()
    ev = pd.read_parquet(f, columns=["event"]).drop_duplicates("event")
    ev = ev[~ev.event.astype(str).str.startswith("icare")]          # exclude cardiac-arrest (SAP §3.6)
    rows = []
    for e in ev.event.astype(str):
        pid = e.split("_")[0]; dt = e.split("_")[-1]
        rows.append({"eeg_id": f"MOE_{e}", "patient_id": pid, "eeg_datetime": dt, "src": "panel",
                     "panel": True, "panel_set": "moe", "role": "panel",
                     "source_type": "mat_v73", "source_path": f"moe/{e}.mat"})  # relative to PANEL_ROOT
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", default="data/manifest/report_manifest_v4.parquet")
    a = ap.parse_args()
    man = pd.read_parquet(a.src)
    if "source_type" not in man.columns:
        man["source_type"] = "bids"; man["source_path"] = pd.NA
    panels = pd.concat([occasion_rows(), moe_rows()], ignore_index=True)
    print(f"panels to append: {len(panels)} "
          f"({int((panels.panel_set=='occasionnoise').sum())} OccasionNoise + {int((panels.panel_set=='moe').sum())} MoE)")
    out = pd.concat([man, panels], ignore_index=True).drop_duplicates("eeg_id")
    for c in man.columns:                                            # fill missing panel columns
        if c not in out.columns:
            out[c] = pd.NA
    path = DIR / "report_manifest_v5.parquet"; out.to_parquet(path, index=False)
    (DIR / "report_manifest_v5.meta.json").write_text(json.dumps({
        "version": 5, "supersedes": "report_manifest_v4", "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_eeg": int(len(out)), "by_src": {k: int(v) for k, v in out.src.value_counts().items()},
        "by_panel_set": {k: int(v) for k, v in out.panel_set.value_counts().items()},
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "panel_format_todo": "OccasionNoise EDF header fix; v7.3 .mat h5py loader; fetch full MoE .mat set"},
        indent=2))
    print(f"wrote {path}: {len(out)} EEGs | by src {dict(out.src.value_counts())}")
    print("  panels featurize via src/io/panels.py (edf_direct / mat_v73) — validated on the mixed pilot.")


if __name__ == "__main__":
    main()
