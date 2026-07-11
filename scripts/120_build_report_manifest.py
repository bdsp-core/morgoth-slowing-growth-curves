"""Build and FREEZE the report<->EEG manifest (docs/analysis_plan.md §3.7) — the pre-fleet artifact that
pins which report belongs to which EEG, with all report-derived features and metadata, computed UP FRONT.

Keyed on eeg_id = {patient_id}_{eeg_datetime} (one row per EEG — NOT per patient; a patient may have several
EEGs, see §5.3 / DATA_INVENTORY.md gap #5).

Inputs (all already built):
  data/derived/labels_unified.parquet   report features + age/sex + eeg_datetime (scripts/60)
  data/derived/report_pairing.parquet    clean_pair, nearest-in-time ownership (scripts/88)
  [optional] the scratchpad report CSV   Duration, EEG path, and raw report text (scripts/20 source)

Outputs:
  data/manifest/report_manifest_v<N>.parquet   eeg_id, features, metadata, clean_pair, recording_seconds,
                                               and (with --csv) the paired report_text/report_impression
  data/manifest/report_manifest_v<N>.meta.json freeze record (version, counts, sha256)

The reports are BDSP DE-IDENTIFIED; report text is included (MBW confirmed 2026-07-05 the de-identified-text
exposure is NOT reportable under the BDSP IRB/DUA). The repo remote is a bdsp-core credentialed repo.

Run:
  PYTHONPATH=src python scripts/120_build_report_manifest.py --version 1 --csv <EEGs_And_Reports.csv>
"""
from __future__ import annotations
import argparse, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

DER = Path("data/derived")
OUT = Path("data/manifest"); OUT.mkdir(parents=True, exist_ok=True)

# report-derived feature columns carried into the PHI-free manifest
FEATURE_COLS = ["is_normal", "is_abnormal", "has_focal_slow", "has_gen_slow", "clean_normal",
                "report_stratum", "focal_side", "focal_region", "focal_band",
                "gen_band", "gen_topography", "gen_state", "gen_class", "p_gen_pathologic"]
META_COLS = ["age", "sex", "n_report_chars", "has_report", "report_note_name"]


def build_core() -> pd.DataFrame:
    """labels_unified + report_pairing -> one row per eeg_id with features, metadata, clean_pair."""
    lu = pd.read_parquet(DER / "labels_unified.parquet")
    lu["eeg_datetime"] = lu["eeg_datetime"].astype(str)
    lu["patient_id"] = lu["bdsp_id"].astype(str)                       # bdsp_id == patient (site+person)
    lu["eeg_id"] = lu["patient_id"] + "_" + lu["eeg_datetime"]         # the recording key (§5.3)
    if lu["eeg_id"].duplicated().any():
        dupe = int(lu["eeg_id"].duplicated().sum())
        print(f"  WARNING: {dupe} duplicate eeg_id — a patient with two EEGs at the same timestamp; deduping")
        lu = lu.drop_duplicates("eeg_id")

    keep = ["eeg_id", "patient_id", "eeg_datetime"] + [c for c in FEATURE_COLS + META_COLS if c in lu.columns]
    m = lu[keep].copy()

    # clean_pair from scripts/88, now keyed on eeg_id (one row per EEG) — join is exact per EEG.
    rp = pd.read_parquet(DER / "report_pairing.parquet")
    if "eeg_id" not in rp.columns:
        raise SystemExit("report_pairing.parquet is not eeg_id-keyed — re-run scripts/88 first.")
    m = m.merge(rp[["eeg_id", "clean_pair", "same_date_ambiguous", "abs_time_diff_h"]], on="eeg_id", how="left")
    m["clean_pair"] = m["clean_pair"].fillna(False)
    m["same_date_ambiguous"] = m["same_date_ambiguous"].fillna(False)
    n_amb = int(m["same_date_ambiguous"].sum())
    if n_amb:
        print(f"  {n_amb} EEGs are SAME-DATE ambiguous (>1 EEG/day, which one the report describes is "
              f"undeterminable) — flagged, excluded from clean-label analyses.")
    m["nearest_report_id"] = m.get("report_note_name")
    m["recording_seconds"] = np.nan
    m["eeg_path"] = pd.NA
    return m


def _parse_duration(v):
    """Duration may be seconds, or HH:MM:SS. Return seconds (float) or NaN."""
    if pd.isna(v):
        return np.nan
    s = str(v).strip()
    if ":" in s:
        parts = [float(p) for p in s.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    try:
        return float(s)
    except ValueError:
        return np.nan


def enrich_from_csv(m: pd.DataFrame, csv_path: Path, with_text: bool):
    """Best-effort join of Duration, EEG path, and (local only) report text from the raw report CSV.

    NOTE (data-identity reconciliation, §3.7): `labels_unified.eeg_datetime` (from the derived pipeline)
    does NOT equal the report CSV's `StartTime`/`CreationTime` — different datetime origins — so an eeg_id
    join matches ~0. Duration is therefore populated authoritatively in `recording_meta` from the EDF
    header AT RUN TIME (reliable). This CSV path is kept for when the EEG-identity mapping (BIDS/Hash ->
    eeg_datetime) is reconciled; until then it fills text (via ReportName) but leaves duration to run time.
    """
    usecols = ["SiteID", "BDSPPatientID", "StartTime", "Duration",
               "BidsFolder", "EEGFolder", "HashFolderName", "HashFileName", "ReportName", "reports", "impression"]
    c = pd.read_csv(csv_path, usecols=lambda x: x in usecols, dtype=str, low_memory=False)
    c["patient_id"] = c["SiteID"].astype(str) + c["BDSPPatientID"].astype(str).str.replace(r"\.0$", "", regex=True)
    c["eeg_datetime"] = pd.to_datetime(c["StartTime"], errors="coerce").dt.strftime("%Y%m%d%H%M%S")
    c = c.dropna(subset=["eeg_datetime"])
    c["eeg_id"] = c["patient_id"] + "_" + c["eeg_datetime"]
    c = c.drop_duplicates("eeg_id")
    c["recording_seconds_csv"] = c["Duration"].map(_parse_duration)
    c["eeg_path_csv"] = (c["BidsFolder"].fillna("") + "/" + c["EEGFolder"].fillna("")
                         + "/" + c["HashFolderName"].fillna("") + "/" + c["HashFileName"].fillna("")).str.strip("/")

    j = m.merge(c[["eeg_id", "recording_seconds_csv", "eeg_path_csv"]], on="eeg_id", how="left")
    matched = int(j["recording_seconds_csv"].notna().sum())
    print(f"  CSV enrichment: matched {matched}/{len(m)} EEGs on eeg_id "
          f"({100*matched/max(len(m),1):.0f}%) for duration/path (0 expected: eeg_datetime≠StartTime)")
    j["recording_seconds"] = j["recording_seconds_csv"].fillna(j["recording_seconds"])
    j["eeg_path"] = j["eeg_path_csv"].where(j["eeg_path_csv"].astype(bool), j["eeg_path"])
    j = j.drop(columns=["recording_seconds_csv", "eeg_path_csv"])

    # Report TEXT: join on report_note_name == ReportName (matches, unlike the timestamps). The text is
    # shared across EEGs of the same report (broadcast), which is exactly the paired-report text per EEG.
    # De-identified (BDSP), NOT reportable under the IRB/DUA (MBW 2026-07-05) → included in the manifest.
    txt = c[["ReportName", "reports", "impression"]].dropna(subset=["ReportName"]).drop_duplicates("ReportName")
    j = j.merge(txt.rename(columns={"ReportName": "report_note_name",
                                     "reports": "report_text", "impression": "report_impression"}),
                on="report_note_name", how="left")
    nt = int(j["report_text"].notna().sum())
    print(f"  report text attached to {nt}/{len(j)} EEGs ({100*nt/max(len(j),1):.0f}%) via report_note_name")
    return j, None


# report_note_name is a BDSP DE-IDENTIFIED note surrogate (+ shifted date), no more identifying than the
# bdsp_id/patient_id already committed throughout the repo — so it is KEPT. Only the raw report TEXT (free
# narrative, which can carry incidental identifiers) stays local, and it is never in the core anyway.
PHI_COLS = []


def freeze(m: pd.DataFrame, version: int, text: pd.DataFrame | None, scratch: Path | None):
    path = OUT / f"report_manifest_v{version}.parquet"
    committed = m.drop(columns=[c for c in PHI_COLS if c in m.columns])
    committed.to_parquet(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = {
        "version": version,
        "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_eeg": int(len(m)),
        "n_patients": int(m["patient_id"].nunique()),
        "n_clean_pair": int((m["clean_pair"] == True).sum()),
        "n_same_date_ambiguous": int(m["same_date_ambiguous"].sum()),
        "n_with_duration": int(m["recording_seconds"].notna().sum()),
        "n_with_text": int(m["report_text"].notna().sum()) if "report_text" in m else 0,
        "n_abnormal": int((m.get("is_abnormal") == 1).sum()) if "is_abnormal" in m else None,
        "sha256": sha,
        "columns": list(committed.columns),
        "deid": "BDSP de-identified; report text included (NOT reportable under IRB/DUA, MBW 2026-07-05)",
    }
    (OUT / f"report_manifest_v{version}.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  wrote {path} ({len(m)} EEGs) + meta (sha256 {sha[:12]}…)")
    if text is not None and scratch is not None:
        scratch.mkdir(parents=True, exist_ok=True)
        wt = m.merge(text, on="eeg_id", how="left")
        wt_path = scratch / f"report_manifest_v{version}_withtext.parquet"
        wt.to_parquet(wt_path, index=False)
        print(f"  wrote LOCAL (PHI) {wt_path} with report text — NOT committed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--csv", type=str, default=None, help="raw EEGs_And_Reports.csv for Duration/path/text")
    ap.add_argument("--with-text", action="store_true", help="also write a LOCAL withtext version (needs --csv)")
    ap.add_argument("--scratch", type=str, default=None, help="scratchpad dir for the withtext version")
    a = ap.parse_args()

    print("building report manifest core (labels_unified + report_pairing)…")
    m = build_core()
    text = None
    if a.csv:
        print(f"enriching from {a.csv}…")
        m, text = enrich_from_csv(m, Path(a.csv), a.with_text)
    scratch = Path(a.scratch) if a.scratch else None
    freeze(m, a.version, text if a.with_text else None, scratch)
    print("done.")


if __name__ == "__main__":
    main()
