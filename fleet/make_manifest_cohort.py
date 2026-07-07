"""Build the fleet manifest to RECOMPUTE the routine cohort through the same pipeline as the overnight
expansion (extract.py features + Morgoth staging), so both cohorts are pipeline-identical and every
feature (incl. TAR/DAR/alpha) is cross-comparable. One row per cohort normal recording (its routine
rEEG, ses from the .mat filename). Same schema the worker expects (SiteID/pid/date/BidsFolder/SessionID).

Run: python fleet/make_manifest_cohort.py > fleet/manifest_cohort.jsonl
"""
import glob, os, re, json
import pandas as pd

SC = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad"
meta = pd.read_csv("metadata/cohort_metadata.csv", dtype=str).drop_duplicates("bdsp_id").set_index("bdsp_id")
rows = []
for mp in sorted(glob.glob(f"{SC}/mat_normal/sub-*_ses-*.mat")):
    mm = re.match(r"sub-(.+?)_ses-(\d+)_(\d+)", os.path.basename(mp))
    if not mm:
        continue
    bdsp_id, ses, dt = mm.group(1), mm.group(2), mm.group(3)
    site, pid = bdsp_id[:5], bdsp_id[5:]
    m = meta.loc[bdsp_id] if bdsp_id in meta.index else None
    rows.append({
        "SiteID": site, "pid": pid, "date": dt[:8],
        "rnorm": 1, "rfoc": 0, "rgen": 0,
        "AgeAtVisit": (float(m.age) if m is not None and pd.notna(m.age) else None),
        "SexDSC": (m.sex if m is not None else None),
        "BidsFolder": f"sub-{bdsp_id}", "SessionID": ses,
    })
for r in rows:
    print(json.dumps(r))
import sys
print(f"cohort manifest: {len(rows)} recordings", file=sys.stderr)
