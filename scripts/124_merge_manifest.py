"""Fold the backfill into the run manifest: union the cohort report_manifest_v1 with the pool-selected
backfill_candidates into ONE harmonized manifest (report_manifest_v2), keyed on eeg_id, 4-region taxonomy,
`src` tagging cohort vs backfill. This is the EEG list the fleet ingests (docs/analysis_plan.md §3.7/§13).

- Cohort focal_region is re-extracted to the 4-region taxonomy from report_text (scripts/20 REGION4).
- Cohort eeg_path (missing in v1 — derived pipeline dropped it) is resolved from the report CSV via
  (pid, date), the same key scripts/88 uses; backfill paths come straight from the CSV.
Reports are BDSP de-identified; report text is included (docs/analysis_plan.md §11).

Run: PYTHONPATH=src python scripts/124_merge_manifest.py [--version 2]
"""
from __future__ import annotations
import argparse, json, hashlib, importlib.util
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

CSV = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
       "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv")
DIR = Path("data/manifest")
COHORT = DIR / "report_manifest_v1.parquet"
BACKFILL = DIR / "backfill_candidates_v1.parquet"

SCHEMA = ["eeg_id", "patient_id", "eeg_datetime", "src", "age", "sex", "is_normal", "is_abnormal",
          "has_focal_slow", "has_gen_slow", "clean_normal", "focal_region", "focal_side", "focal_band",
          "gen_topography", "gen_band", "clean_pair", "same_date_ambiguous", "eeg_path",
          "report_note_name", "report_text"]

_m20 = importlib.util.spec_from_file_location("m20", "scripts/20_extract_report_labels.py")
m20 = importlib.util.module_from_spec(_m20); _m20.loader.exec_module(m20)


def cohort_paths():
    """One representative EEG path per (pid, date) from the CSV (matches scripts/88's join key)."""
    c = pd.concat([ch for ch in pd.read_csv(
        CSV, usecols=["SiteID", "BDSPPatientID", "StartTime", "time_diff", "BidsFolder", "EEGFolder",
                      "HashFileName"], chunksize=200000, dtype=str, low_memory=False)])
    c["pid"] = c.SiteID.astype(str) + c.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    c["dt"] = pd.to_datetime(c.StartTime, errors="coerce"); c = c.dropna(subset=["dt"])
    c["date"] = c.dt.dt.strftime("%Y%m%d"); c["absd"] = pd.to_numeric(c.time_diff, errors="coerce").abs()
    c = c.sort_values("absd").drop_duplicates(["pid", "date"])
    c["eeg_path"] = (c.BidsFolder.fillna("") + "/" + c.EEGFolder.fillna("") + "/" + c.HashFileName.fillna("")).str.strip("/")
    return c.set_index(["pid", "date"]).eeg_path


def prep_cohort():
    m = pd.read_parquet(COHORT).copy()
    m["src"] = "cohort"
    # re-extract focal region to 4-region from report_text
    m["focal_region"] = np.nan
    fm = m[m.has_focal_slow == 1]
    m.loc[fm.index, "focal_region"] = fm.report_text.fillna("").str.lower().map(m20.extract_region4)
    # resolve path via (pid, date) — pid = full bdsp_id (site+person), matching cohort_paths()
    m["pid"] = m.patient_id.astype(str)
    m["date"] = m.eeg_datetime.astype(str).str[:8]
    paths = cohort_paths()
    m["eeg_path"] = pd.MultiIndex.from_frame(m[["pid", "date"]]).map(paths)
    return m


def prep_backfill():
    b = pd.read_parquet(BACKFILL).copy()
    b["src"] = "backfill"
    b["patient_id"] = b.pid
    b["eeg_datetime"] = b.eeg_id.str.split("_").str[-1]
    b["has_focal_slow"] = b.is_focal.astype(int)
    b["has_gen_slow"] = b.is_gen.astype(int)
    b["is_abnormal"] = ((b.is_focal) | (b.is_gen)).astype(int)
    b["clean_normal"] = ((b.is_normal) & ~((b.is_focal) | (b.is_gen))).astype(int)
    b["is_normal"] = b.is_normal.astype(int)
    b["same_date_ambiguous"] = False
    return b


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--version", type=int, default=2); a = ap.parse_args()
    coh, bf = prep_cohort(), prep_backfill()
    for df in (coh, bf):
        for col in SCHEMA:
            if col not in df.columns:
                df[col] = np.nan
    out = pd.concat([coh[SCHEMA], bf[SCHEMA]], ignore_index=True)
    out = out.drop_duplicates("eeg_id")

    path = DIR / f"report_manifest_v{a.version}.parquet"
    out.to_parquet(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = {
        "version": a.version, "supersedes": "report_manifest_v1 (cohort only)",
        "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_eeg": int(len(out)), "n_patients": int(out.patient_id.nunique()),
        "by_src": {k: int(v) for k, v in out.src.value_counts().items()},
        "n_clean_pair": int((out.clean_pair == True).sum()),
        "n_with_path": int(out.eeg_path.notna().sum()),
        "n_with_text": int(out.report_text.notna().sum()),
        "n_focal": int((out.has_focal_slow == 1).sum()), "n_gen": int((out.has_gen_slow == 1).sum()),
        "n_clean_normal": int((out.clean_normal == 1).sum()),
        "region_taxonomy": "4 (frontal, temporal, central, posterior)",
        "sha256": sha, "columns": list(out.columns),
        "deid": "BDSP de-identified; report text included (NOT reportable under IRB/DUA)",
    }
    (DIR / f"report_manifest_v{a.version}.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {path}")
    print(json.dumps({k: meta[k] for k in ["n_eeg", "n_patients", "by_src", "n_with_path", "n_focal",
                                           "n_gen", "n_clean_normal"]}, indent=2))


if __name__ == "__main__":
    main()
