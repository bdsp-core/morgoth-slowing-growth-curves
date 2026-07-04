"""Generate the fleet work manifest — the stratified list of recordings to ingest at scale.

Reuses the SAME eligible-pool + (label x age-band) round-robin as the validated local worker, but does
NOT exclude local .done markers (the fleet checks S3 for resumability at run time). Writes one JSON
object per line with exactly the columns process_one/edf_path need. Upload the result to S3; each
Batch array task processes a strided slice.

Run:  PYTHONPATH=src python fleet/make_manifest.py [N] [out.jsonl]     (default N=15000)
Then: aws s3 cp fleet/manifest.jsonl s3://<your-bucket>/morgoth-slowing/manifest.jsonl
"""
from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd

_spec = importlib.util.spec_from_file_location("p26", str(Path(__file__).resolve().parents[1] / "scripts" / "26_slowing_ingest_pilot.py"))
p26 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p26)

AGE_BINS = [0, 2, 5, 12, 17, 29, 44, 59, 74, 120]
# columns the fleet worker needs (process_one + edf_path)
COLS = ["SiteID", "pid", "date", "rnorm", "rfoc", "rgen", "AgeAtVisit", "SexDSC", "BidsFolder", "SessionID"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("manifest.jsonl")
    j = p26.eligible().copy()
    j["plabel"] = np.where(j.rnorm == 1, "normal", np.where(j.rfoc == 1, "focal_slow", "general_slow"))
    j["ageband"] = pd.cut(pd.to_numeric(j.AgeAtVisit, errors="coerce"), bins=AGE_BINS)

    def _stream(sub):                                   # round-robin across age bands
        gs = [g.reset_index(drop=True) for _, g in sub.groupby("ageband", observed=True)]
        out, gi = [], [0] * len(gs)
        while any(gi[k] < len(gs[k]) for k in range(len(gs))):
            for k in range(len(gs)):
                if gi[k] < len(gs[k]):
                    out.append(gs[k].iloc[gi[k]]); gi[k] += 1
        return out
    streams = {lab: _stream(j[j.plabel == lab]) for lab in ("focal_slow", "general_slow", "normal")}
    picks, si = [], {k: 0 for k in streams}             # interleave labels
    order = ["focal_slow", "general_slow", "normal"]
    while len(picks) < n and any(si[k] < len(streams[k]) for k in order):
        for lab in order:
            if si[lab] < len(streams[lab]):
                picks.append(streams[lab][si[lab]]); si[lab] += 1
                if len(picks) >= n:
                    break
    df = pd.DataFrame(picks)
    # PRIORITY first-wave stratum: targeted focal-theta-temporal candidates (fixes the theta bottleneck).
    cand = Path(__file__).resolve().parents[1] / "results" / "candidate_focal_theta_temporal.csv"
    if cand.exists():
        c = pd.read_csv(cand, dtype=str)
        c["pid"] = c.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
        c["date"] = pd.to_datetime(c.StartTime, errors="coerce").dt.strftime("%Y%m%d")
        c = c.rename(columns={"SessionID_new": "SessionID"})
        for col, v in [("rnorm", 0), ("rfoc", 1), ("rgen", 0)]:
            c[col] = v
        c = c.dropna(subset=["date", "BidsFolder"]).drop_duplicates(["SiteID", "pid", "date"])
        c = c[[col for col in COLS if col in c.columns]]
        df = pd.concat([c, df], ignore_index=True).drop_duplicates(["SiteID", "pid", "date"])
        print(f"prepended {len(c)} focal-theta priority candidates")
    miss = [c for c in COLS if c not in df.columns]
    if miss:
        print(f"WARNING missing columns in metadata: {miss}")
    with open(out, "w") as fh:
        for _, r in df.iterrows():
            fh.write(json.dumps({c: (None if c not in df.columns or pd.isna(r[c]) else
                                     (int(r[c]) if c in ("rnorm", "rfoc", "rgen") else
                                      float(r[c]) if c == "AgeAtVisit" else str(r[c])))
                                 for c in COLS}) + "\n")
    by = df.assign(plabel=np.where(df.rnorm == 1, "normal", np.where(df.rfoc == 1, "focal", "gen")))
    print(f"wrote {len(df)} recordings -> {out}")
    print("by label:", by.plabel.value_counts().to_dict())


if __name__ == "__main__":
    main()
