"""Coverage-expansion cohort SELECTION for the EEG-slowing project.

Our current cohort (metadata/cohort_metadata.csv) is under-powered for adult N3/deep sleep and for
abnormal-with-sleep (see docs/coverage_by_stage.md). The full BDSP EEG repository holds many more
long, sleep-capturing routine EEGs that carry a clinician-report label. This script finds the NEW
ones worth ingesting -- it does NOT download raw EEG or run ingestion.

Inputs (metadata CSVs only, pulled via rclone remote `bdsp:` into a local temp cache):
  bdsp-opendata-repository/EEG/eeg-metadata/<SITE>_eeg_metadata_*.csv
      -> SiteID, BDSPPatientID, BidsFolder, DurationInSeconds, AgeAtVisit, SexDSC, StartTime
  bdsp-opendata-repository/EEG/HEEDB_Metadata/<SITE>_EEG*_reports_findings.csv
      -> BDSPPatientID, StartTime(EEG), normal, abnormal, 'foc slowing', 'gen slowing'
         (a cell value containing 'report' == the finding is stated in the interpreting report)

Selection (per docs/coverage_by_stage.md "Data expansion" section):
  (a) long enough to contain sleep      : DurationInSeconds > 6*3600
  (b) has a report-derived label        : report-stated normal OR foc slowing OR gen slowing
  (c) not already in our cohort         : match on full bdsp_id (SiteID+BDSPPatientID) + start date

Output: data/derived/expansion_candidates.csv
  cols: bdsp_id, person_id, site, age, sex, duration_h,
        report_normal, report_abnormal, report_focal, report_gen, priority

`priority` up-weights the two real gaps (adult N3-likely = long & age>=18 normal; abnormal-with-sleep):
  1.0 base
  +1.5  adult (age>=18) & normal            -> adult N3 normal-norm gap
  +2.0  focal or generalized slowing        -> abnormal-with-sleep gap (any age)
  +1.0  adult & (focal or gen)              -> adult abnormal-with-sleep (fills both gaps)
  +0.5  multi-day (>=24 h)                  -> more full sleep cycles / more N3

Run:  PYTHONPATH=src .venv/bin/python scripts/23_expansion_cohort.py
"""
from __future__ import annotations
import os, re, subprocess, tempfile
from pathlib import Path
import numpy as np
import pandas as pd

RCLONE = os.path.expanduser("~/.local/bin/rclone")
REMOTE = "bdsp:bdsp-opendata-repository/EEG"
META_DIR = f"{REMOTE}/eeg-metadata"
FIND_DIR = f"{REMOTE}/HEEDB_Metadata"
CACHE = Path(tempfile.gettempdir()) / "bdsp_expansion_cache"
OUT = Path("data/derived/expansion_candidates.csv")
COHORT = Path("metadata/cohort_metadata.csv")

# Sites with BOTH a metadata CSV and a findings CSV that carries foc/gen slowing.
# (I0009 has metadata but no findings file -> excluded; no report label obtainable.)
SITES = ["S0001", "S0002", "I0002", "I0003"]

DUR_MIN = 6 * 3600          # sleep-containing threshold
AGE_BANDS = [0, 3, 6, 13, 18, 30, 45, 60, 75, 999]
AGE_LABELS = ["0-2", "3-5", "6-12", "13-17", "18-29", "30-44", "45-59", "60-74", "75+"]


def _lsf(remote_dir: str) -> list[str]:
    out = subprocess.run([RCLONE, "lsf", remote_dir + "/"], capture_output=True, text=True, check=True)
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def _fetch(remote_dir: str, pattern: str) -> Path:
    """Copy the one file in remote_dir whose name matches `pattern` into CACHE; return local path."""
    CACHE.mkdir(parents=True, exist_ok=True)
    names = [n for n in _lsf(remote_dir) if re.match(pattern, n)]
    if not names:
        raise FileNotFoundError(f"no file matching {pattern!r} in {remote_dir}")
    name = sorted(names)[-1]  # if several, take the latest-sorted (dated) name
    local = CACHE / name
    if not local.exists():
        subprocess.run([RCLONE, "copy", f"{remote_dir}/{name}", str(CACHE)], check=True)
    return local


def _date8(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y%m%d")


def _report_flag(col: pd.Series) -> pd.Series:
    # cell value containing 'report' (e.g. 'report', 'report verified', 'report annotation')
    return col.fillna("").astype(str).str.contains("report", case=False)


def load_site(site: str) -> pd.DataFrame:
    mfile = _fetch(META_DIR, rf"{site}_eeg_metadata.*\.csv$")
    ffile = _fetch(FIND_DIR, rf"{site}_EEG_*_?reports_findings\.csv$")

    m = pd.read_csv(mfile, dtype=str, low_memory=False)
    m["site"] = site
    m["person_id"] = m["BDSPPatientID"]
    m["bdsp_id"] = site + m["BDSPPatientID"].fillna("")
    m["date"] = _date8(m["StartTime"])
    m["duration_s"] = pd.to_numeric(m["DurationInSeconds"], errors="coerce")
    m["age"] = pd.to_numeric(m["AgeAtVisit"], errors="coerce")
    m["sex"] = m["SexDSC"].map({"Female": "F", "Male": "M"}).fillna("Other/NA")

    f = pd.read_csv(ffile, dtype=str, low_memory=False)
    f["person_id"] = f["BDSPPatientID"]
    f["date"] = _date8(f["StartTime(EEG)"])
    f["report_normal"] = _report_flag(f["normal"])
    f["report_abnormal"] = _report_flag(f["abnormal"])
    f["report_focal"] = _report_flag(f["foc slowing"])
    f["report_gen"] = _report_flag(f["gen slowing"])
    fj = (f[["person_id", "date", "report_normal", "report_abnormal", "report_focal", "report_gen"]]
          .dropna(subset=["person_id", "date"])
          .groupby(["person_id", "date"], as_index=False).max())  # OR the flags within a patient-day

    j = m.merge(fj, on=["person_id", "date"], how="inner")
    print(f"  {site}: meta={len(m):>7} findings={len(f):>7} matched={len(j):>7}")
    return j


def main():
    print("Loading site metadata + findings (rclone cache: %s)" % CACHE)
    df = pd.concat([load_site(s) for s in SITES], ignore_index=True)
    print(f"total meta+findings matches: {len(df)}")

    # (a) long enough for sleep, (b) has a normal / focal / gen report label
    df = df[df.duration_s > DUR_MIN]
    df = df[df.report_normal | df.report_focal | df.report_gen]
    # collapse duplicate rows for the same recording (patient + start date), keep the longest
    df = df.sort_values("duration_s", ascending=False).drop_duplicates(["bdsp_id", "date"])
    print(f"long (>6h) & report-labeled recordings: {len(df)}")

    # (c) drop anything already in our cohort (full bdsp_id + start date)
    coh = pd.read_csv(COHORT, dtype=str)
    coh_keys = set(coh["bdsp_id"] + "_" + coh["eeg_datetime"].str[:8])
    df["_key"] = df["bdsp_id"] + "_" + df["date"]
    n_before = len(df)
    df = df[~df["_key"].isin(coh_keys)]
    print(f"removed already-in-cohort: {n_before - len(df)}  ->  NEW candidates: {len(df)}")

    df["duration_h"] = (df.duration_s / 3600.0).round(2)
    adult = df.age >= 18
    abn = df.report_focal | df.report_gen
    multiday = df.duration_h >= 24
    df["priority"] = (1.0
                      + 1.5 * (adult & df.report_normal)
                      + 2.0 * abn
                      + 1.0 * (adult & abn)
                      + 0.5 * multiday).round(2)

    out = df[["bdsp_id", "person_id", "site", "age", "sex", "duration_h",
              "report_normal", "report_abnormal", "report_focal", "report_gen", "priority"]].copy()
    for c in ["report_normal", "report_abnormal", "report_focal", "report_gen"]:
        out[c] = out[c].astype(int)
    out = out.sort_values(["priority", "duration_h"], ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}: {len(out)} rows")

    # ---- summary: age band x sex x label ----
    df["band"] = pd.cut(df.age, bins=AGE_BANDS, right=False, labels=AGE_LABELS)
    print("\nTotal NEW candidates:", len(df), "| multi-day (>=24h):", int(multiday.sum()))
    print("Label totals (non-exclusive): normal=%d focal=%d gen=%d abnormal=%d"
          % (df.report_normal.sum(), df.report_focal.sum(), df.report_gen.sum(), df.report_abnormal.sum()))
    print("Adult (>=18) long normal (N3 gap):", int((adult & df.report_normal).sum()))
    print("By site:", df.site.value_counts().to_dict())
    for name, flag in [("NORMAL", df.report_normal), ("FOCAL", df.report_focal), ("GEN", df.report_gen)]:
        print(f"\n=== {name}: age-band x sex ===")
        print(pd.crosstab(df[flag].band, df[flag].sex, dropna=False).to_string())
    print("\nTotal candidate EEG-hours: %.0f" % df.duration_h.sum())


if __name__ == "__main__":
    main()
