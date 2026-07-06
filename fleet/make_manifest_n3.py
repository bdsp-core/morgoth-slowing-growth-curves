"""Build the N3-fill fleet manifest: report-NORMAL, NIGHT-SPANNING (covers 00:00-05:00 clock),
6-48 h, not already in the cohort, across MGB (S0001/S0002) + BCH (I0003). BIDMC (I0002) excluded
(de-id date-shift breaks its metadata<->findings join; recoverable follow-up).

Night-spanning is the right filter: studies start mostly 6-9 am, so a 12 h study runs ~08:00->20:00 and
never reaches sleep. `covers 00:00-05:00`  <=>  dur_h >= ((24 - start_hour) % 24) + 5.

Writes fleet/manifest_full.jsonl (worker schema). Metadata pulled to PILOT_SCRATCH/eegmeta by the caller.
Run: PILOT_SCRATCH=<dir> python fleet/make_manifest_n3.py
"""
from __future__ import annotations
import os, glob, json
import pandas as pd, numpy as np

PS = os.environ["PILOT_SCRATCH"]
FIND = {"S0001": "data/findings/S0001_EEG__reports_findings.csv",
        "S0002": "data/findings/S0002_EEG__reports_findings.csv",
        "I0003": "data/findings/I0003_EEG__reports_findings.csv"}
COLS = ["SiteID", "pid", "date", "rnorm", "rfoc", "rgen", "AgeAtVisit", "SexDSC", "BidsFolder", "SessionID"]
cohort = set(pd.read_csv("metadata/cohort_metadata.csv").bdsp_id.str.replace(r"^S000\d", "", regex=True))

rows = []
for s in FIND:
    mfile = glob.glob(f"{PS}/eegmeta/{s}*metadata*.csv")[0]
    m = pd.read_csv(mfile, dtype=str, low_memory=False)
    f = pd.read_csv(FIND[s], dtype=str, low_memory=False)
    m["SiteID"] = s
    m["pid"] = m.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    st = pd.to_datetime(m.StartTime, errors="coerce")
    m["date"] = st.dt.strftime("%Y%m%d")
    m["dur_h"] = pd.to_numeric(m.DurationInSeconds, errors="coerce") / 3600
    m["shour"] = st.dt.hour + st.dt.minute / 60
    f["pid"] = f.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    f["date"] = pd.to_datetime(f["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    f["rnorm"] = f["normal"].astype(str).str.contains("report", case=False, na=False).astype(int)
    j = m.merge(f[["pid", "date", "rnorm"]], on=["pid", "date"], how="inner")
    j = j.dropna(subset=["BidsFolder", "SessionID", "date", "shour", "AgeAtVisit"])
    night = j.dur_h >= ((24 - j.shour) % 24) + 5
    j = j[(j.rnorm == 1) & (j.dur_h >= 6) & (j.dur_h < 48) & night].drop_duplicates(["pid", "date"])
    if s in ("S0001", "S0002"):
        j = j[~j.pid.isin(cohort)]
    j["rfoc"] = 0; j["rgen"] = 0
    rows.append(j)

d = pd.concat(rows, ignore_index=True)
out = "fleet/manifest_full.jsonl"
with open(out, "w") as fh:
    for _, r in d.iterrows():
        fh.write(json.dumps({c: (None if pd.isna(r.get(c)) else
                                 (int(r[c]) if c in ("rnorm", "rfoc", "rgen") else
                                  float(r[c]) if c == "AgeAtVisit" else str(r[c]))) for c in COLS}) + "\n")
d["age"] = pd.to_numeric(d.AgeAtVisit, errors="coerce")
band = pd.cut(d.age, [0, 3, 6, 13, 18, 30, 45, 60, 75, 200],
              labels=["0-2", "3-5", "6-12", "13-17", "18-29", "30-44", "45-59", "60-74", "75+"], right=False)
print(f"wrote {out}: {len(d)} night-spanning report-normal recordings")
print("by site:", d.SiteID.value_counts().to_dict())
print("by age band:", band.value_counts().sort_index().to_dict())
