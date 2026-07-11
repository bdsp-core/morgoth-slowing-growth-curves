"""Finalize the run manifest (report_manifest_v3) to the run_manifest_schema.md contract: add the S3
routing fields the fleet's pull step consumes, drop EEGs that can't be located, and wire the integrity
fields (n_bytes/sha256) for pull-time stamping.

Why sha256/n_bytes are pull-time: (1) the exact EDF is `bids/{site}/{BidsFolder}/ses-{N}/eeg/..._eeg.edf`
where the BIDS `ses-N` is NOT the report system's SessionID_new, so the exact file is found by listing the
subject at pull; (2) sha256 cannot exist before the file is fetched. Both are stamped once, for free, while
the pull streams each EDF into the bucket. This script fills everything deterministic and leaves those two
as null with a defined protocol.

Excludes the 76 EEGs whose (subject,date) has no report-CSV row (no locatable EDF).

Run: PYTHONPATH=src python scripts/125_finalize_run_manifest.py [--version 3]
"""
from __future__ import annotations
import argparse, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

CSV = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
       "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv")
DIR = Path("data/manifest")
S3_BIDS = "s3:bdsp-opendata-repository/EEG/bids"


def csv_subject_meta():
    """One representative row per (BidsFolder, date): SiteID, task (EEGFolder), report SessionID_new."""
    c = pd.concat([ch for ch in pd.read_csv(
        CSV, usecols=["SiteID", "BDSPPatientID", "StartTime", "time_diff", "BidsFolder", "EEGFolder",
                      "SessionID_new"], chunksize=200000, dtype=str, low_memory=False)])
    c["dt"] = pd.to_datetime(c.StartTime, errors="coerce"); c = c.dropna(subset=["dt"])
    c["date"] = c.dt.dt.strftime("%Y%m%d")
    c["absd"] = pd.to_numeric(c.time_diff, errors="coerce").abs()
    c = c.sort_values("absd").drop_duplicates(["BidsFolder", "date"])
    return c.set_index(["BidsFolder", "date"])[["SiteID", "EEGFolder", "SessionID_new"]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--version", type=int, default=3)
    ap.add_argument("--src", default="data/manifest/report_manifest_v2.parquet"); a = ap.parse_args()

    m = pd.read_parquet(a.src).copy()
    m["bids_folder"] = "sub-" + m.patient_id.astype(str)
    m["date"] = m.eeg_datetime.astype(str).str[:8]
    meta = csv_subject_meta()
    key = pd.MultiIndex.from_frame(m[["bids_folder", "date"]])
    m["site_id"] = key.map(meta.SiteID)
    m["bids_task"] = key.map(meta.EEGFolder)
    m["report_session_id"] = key.map(meta.SessionID_new)

    n0 = len(m)
    m = m[m.site_id.notna()].copy()                              # drop EEGs with no locatable subject/date
    print(f"excluded {n0 - len(m)} EEGs with no locatable EDF (no report-CSV subject/date match)")

    # deterministic routing the pull step consumes; exact ses-N EDF is resolved by listing the subject
    m["source_subject_dir"] = f"{S3_BIDS}/" + m.site_id + "/" + m.bids_folder + "/"
    m["bucket_key"] = "run-bucket/edf/" + m.eeg_id + ".edf"
    m["n_bytes"] = pd.array([pd.NA] * len(m), dtype="Int64")     # stamped at pull (S3 metadata)
    m["sha256"] = pd.NA                                          # stamped at pull (hash while streaming)
    m = m.drop(columns=["bids_folder", "date", "site_id"])

    path = DIR / f"report_manifest_v{a.version}.parquet"
    m.to_parquet(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    doc = {
        "version": a.version, "supersedes": Path(a.src).name,
        "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_eeg": int(len(m)), "n_patients": int(m.patient_id.nunique()),
        "by_src": {k: int(v) for k, v in m.src.value_counts().items()},
        "n_with_routing": int(m.source_subject_dir.notna().sum()),
        "by_task": {k: int(v) for k, v in m.bids_task.value_counts().items()},
        "integrity_fields": "n_bytes + sha256 are null here; the pull step lists source_subject_dir, "
                            "matches the session/date, copies the EDF to bucket_key, and stamps both.",
        "sha256_of_manifest": sha, "columns": list(m.columns),
        "deid": "BDSP de-identified; report text included (NOT reportable under IRB/DUA)",
    }
    (DIR / f"report_manifest_v{a.version}.meta.json").write_text(json.dumps(doc, indent=2))
    print(f"wrote {path}")
    print(json.dumps({k: doc[k] for k in ["n_eeg", "n_patients", "by_src", "by_task", "n_with_routing"]}, indent=2))


if __name__ == "__main__":
    main()
