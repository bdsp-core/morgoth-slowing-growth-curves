"""Compute precise fractional age-at-EEG = (EEG date - birth_datetime)/365.25 from OMOP, and write it
onto the uniform reference table (replacing integer AgeAtVisit). Read-only OMOP query: person_id ->
birth_datetime only (no note/free-text). De-id dates are per-patient-consistent so the difference is valid.

Run: python scripts/71_omop_fractional_age.py
"""
from __future__ import annotations
import re, subprocess
import pandas as pd, numpy as np, psycopg

TABLE = "data/derived/channel_stage_features.parquet"
BOXPW = "box:Brandon - PHI/AWSKeys/StanfordAWS_keys/bdsp-stanford-aurora-master-password.txt"
XWALK = "/Users/mwestover/GithubRepos/OMOP/current_bdsp_patient_id_lookup_OMOP_13thMay2026.csv"


def eeg_date_map():
    """bdsp_id -> EEG date (from the _YYYYMMDD suffix for expansion, else cohort_metadata)."""
    m = {}
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    for r in meta.itertuples():
        m[r.bdsp_id] = str(r.eeg_datetime)[:8]
    return m


def main():
    df = pd.read_parquet(TABLE)
    ids = df.bdsp_id.unique()
    emap = eeg_date_map()
    rec = []
    for b in ids:
        pid = re.sub(r"^[SI]000\d", "", b).split("_")[0]           # strip site prefix + date suffix
        if "_" in b:
            date = b.split("_")[1][:8]                              # expansion: date in the id
        else:
            date = emap.get(b)                                     # cohort: from metadata
        if pid.isdigit() and date:
            rec.append((b, int(pid), date))
    R = pd.DataFrame(rec, columns=["bdsp_id", "person_id", "eeg_date"])
    # merged->current id crosswalk (some person_ids were merged in OMOP)
    xw = pd.read_csv(XWALK)
    xwd = dict(zip(xw.MergedBDSPPatientID, xw.CurrentBDSPPatientID))
    R["person_id_q"] = R.person_id.map(lambda p: xwd.get(p, p))
    print(f"recordings to resolve: {len(R)} | unique person_ids: {R.person_id_q.nunique()}")

    pw = subprocess.run(["rclone", "cat", BOXPW], capture_output=True, text=True).stdout.strip()
    conn = psycopg.connect(host="localhost", port=5433, dbname="bdsp_omop", user="bdspadmin", password=pw)
    pids = sorted(R.person_id_q.unique().tolist())
    births = {}
    with conn.cursor() as cur:
        for i in range(0, len(pids), 5000):
            chunk = pids[i:i + 5000]
            cur.execute("SELECT person_id, birth_datetime FROM omop_prod.person WHERE person_id = ANY(%s)", (chunk,))
            births.update({r[0]: r[1] for r in cur.fetchall()})
    conn.close()
    print(f"birth dates resolved: {len(births)} / {len(pids)} person_ids")

    R["birth"] = R.person_id_q.map(births)
    R["eeg_dt"] = pd.to_datetime(R.eeg_date, format="%Y%m%d", errors="coerce")
    R["birth_dt"] = pd.to_datetime(R.birth, errors="coerce")
    R["age_frac"] = (R.eeg_dt - R.birth_dt).dt.days / 365.25
    ok = R[(R.age_frac.notna()) & (R.age_frac >= 0) & (R.age_frac < 120)]
    print(f"valid fractional ages: {len(ok)} / {len(R)}")
    print("first-year recordings now resolved to months:",
          int((ok.age_frac < 1).sum()), "| age<1 distribution (months):",
          np.round(sorted((ok[ok.age_frac < 1].age_frac.values * 12))[:20], 1).tolist())

    # write age_frac onto the uniform table (fall back to old integer age where unresolved)
    amap = dict(zip(ok.bdsp_id, ok.age_frac))
    df["age_int"] = df["age"]
    df["age"] = df.bdsp_id.map(amap).fillna(df["age"])
    df.to_parquet(TABLE)
    R[["bdsp_id", "person_id", "eeg_date", "age_frac"]].to_parquet("data/derived/fractional_age.parquet")
    print(f"updated {TABLE} with fractional age ({df.bdsp_id.map(amap).notna().mean()*100:.0f}% of recordings)")


if __name__ == "__main__":
    main()
