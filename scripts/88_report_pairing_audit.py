"""AUDIT: which recordings are paired with the report that was actually written about THEM?

`EEGs_And_Reports.csv` is an EEG x report join. Each EEG row carries at most one OrderID, but a single
OrderID (one report) is stamped onto up to 170 different EEGs of the same patient -- the upstream join
attached reports to EEGs at the PATIENT level. Joining on (bdsp_id, date) therefore selects the right ROW
while the text inside it may describe a different study of that patient.

Tell-tale: the reader's own severity adjective "agrees" across consecutive studies of a patient 97% of the
time (rho=0.95). No clinical rating is that reliable -- the text is xeroxed, not consistent.

Rule used here: a report belongs to the EEG nearest it in time. An EEG is CLEANLY PAIRED iff its OrderID is
claimed by no other EEG, or it is that OrderID's nearest-in-time owner.

Writes only IDs + pairing booleans; no report text, no OrderID (health-system identifier).
Run: python scripts/88_report_pairing_audit.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

REP = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
       "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv")
OUT = "data/derived/report_pairing.parquet"


def main():
    cols = ["SiteID", "BDSPPatientID", "StartTime", "OrderID", "time_diff"]
    r = pd.concat([c for c in pd.read_csv(REP, usecols=cols, chunksize=100000, dtype=str, low_memory=False)])
    r["pid"] = r.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    r["date"] = pd.to_datetime(r.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    r["absd"] = pd.to_numeric(r.time_diff, errors="coerce").abs()
    r = r.dropna(subset=["date", "OrderID"])

    # collapse to one row per (pid, date): if two EEGs share a day, keep the closest-in-time pairing
    r = r.sort_values("absd").drop_duplicates(["pid", "date"])

    n_dates = r.groupby("OrderID").date.transform("nunique")
    r["shared"] = n_dates > 1
    # the OrderID's true owner = the EEG date nearest it in time
    owner = r.sort_values("absd").drop_duplicates("OrderID")[["OrderID", "date"]].rename(columns={"date": "own"})
    r = r.merge(owner, on="OrderID", how="left")
    r["is_owner"] = r.date == r.own
    r["clean_pair"] = (~r.shared) | r.is_owner

    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["pid"] = meta.bdsp_id.str.replace(r"^S000\d", "", regex=True)
    meta["date"] = meta.eeg_datetime.str[:8]
    j = meta[["bdsp_id", "pid", "date"]].merge(
        r[["pid", "date", "shared", "is_owner", "clean_pair", "absd"]], on=["pid", "date"], how="left")
    j["clean_pair"] = j.clean_pair.fillna(False)

    n = len(j)
    print(f"cohort recordings              : {n:,}")
    print(f"  matched a report row         : {j.shared.notna().sum():,} ({j.shared.notna().mean():.1%})")
    print(f"  report shared w/ another EEG  : {(j.shared == True).sum():,}")
    print(f"  ... and OURS is not the owner : {((j.shared == True) & (~j.is_owner.fillna(False))).sum():,}")
    print(f"CLEANLY PAIRED                  : {j.clean_pair.sum():,} ({j.clean_pair.mean():.1%})")
    print(f"BORROWED / UNMATCHED text       : {(~j.clean_pair).sum():,} ({1 - j.clean_pair.mean():.1%})")

    j["abs_time_diff_h"] = j.absd / 3600.0
    j[["bdsp_id", "shared", "is_owner", "clean_pair", "abs_time_diff_h"]].to_parquet(OUT)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
