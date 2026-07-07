"""Manifest for the REST of the cohort (everything not in the normal recompute batch = the abnormal +
any remaining recordings), so the ENTIRE cohort ends up on the identical extract.py + Morgoth pipeline.
SessionID/date come from the per-site findings CSVs (joined to labels_unified by pid+date). Same schema
+ same S3 prefix (cohort_recompute) as the normal batch, so all outputs land together.

Run: python fleet/make_manifest_cohort_rest.py > fleet/manifest_cohort_rest.jsonl
"""
import glob, os, re, json, sys
import pandas as pd

SC = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad"
FIND = {"S0001": "data/findings/S0001_EEG__reports_findings.csv",
        "S0002": "data/findings/S0002_EEG__reports_findings.csv"}

already = set(re.match(r"sub-(.+?)_ses", os.path.basename(m)).group(1)
              for m in glob.glob(f"{SC}/mat_normal/sub-*.mat"))       # normals already queued

lu = pd.read_parquet("data/derived/labels_unified.parquet").drop_duplicates("bdsp_id")
lu = lu[~lu.bdsp_id.isin(already) & lu.bdsp_id.str.startswith(("S0001", "S0002"))]
lu["pid"] = lu.pid.astype(str)
lu["date"] = pd.to_datetime(lu.eeg_datetime, errors="coerce").dt.strftime("%Y%m%d")

# SessionID from findings (pid+date)
fs = []
for s, path in FIND.items():
    f = pd.read_csv(path, dtype=str, low_memory=False)
    f["pid"] = f.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    f["date"] = pd.to_datetime(f["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    fs.append(f[["pid", "date", "SessionID"]])
F = pd.concat(fs).dropna(subset=["SessionID"]).drop_duplicates(["pid", "date"])

m = lu.merge(F, on=["pid", "date"], how="inner")
rows, n = [], 0
for _, r in m.iterrows():
    site = r.bdsp_id[:5]
    rows.append({"SiteID": site, "pid": r.bdsp_id[5:], "date": r.date,
                 "rnorm": int(r.is_normal == 1), "rfoc": int(r.has_focal_slow == True),
                 "rgen": int(r.has_gen_slow == True),
                 "AgeAtVisit": (float(r.age) if pd.notna(r.age) else None), "SexDSC": r.sex,
                 "BidsFolder": f"sub-{r.bdsp_id}", "SessionID": str(int(float(r.SessionID)))})
    print(json.dumps(rows[-1])); n += 1
print(f"rest-of-cohort manifest: {n} recordings ({len(lu)} candidates, {len(lu)-n} unmatched to a findings SessionID)",
      file=sys.stderr)
