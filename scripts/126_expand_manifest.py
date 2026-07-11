"""Step 3 — expand the frozen manifest to the SAP scale (~27k) + align to run_manifest_schema.

The legacy expansion set is only bdsp_id-grain (no eeg_datetime), and under zero-reuse we don't reuse it —
so we RE-SELECT the expansion from the pool (its purpose: enlarge the normal reference + abnormal tail).
Adds `src=expansion` rows to v3, aligns to the schema (`panel`/`panel_set`/`role`), and resolves S3 routing.
Panels (OccasionNoise + MoE) are added by scripts/127 (their EDF metadata is separate); this script tags the
schema columns so they can be appended.

Reports are BDSP de-identified; report text included (§11). Hardcoded CSV path removed → env REPORTS_CSV.
Run: PYTHONPATH=src python scripts/126_expand_manifest.py [--target 27000]
"""
from __future__ import annotations
import argparse, os, json, hashlib, importlib.util
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

CSV = os.environ.get("REPORTS_CSV",
                     "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
                     "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv")
DIR = Path("data/manifest")
S3_BIDS = "s3:bdsp-opendata-repository/EEG/bids"

_m20 = importlib.util.spec_from_file_location("m20", "scripts/20_extract_report_labels.py")
m20 = importlib.util.module_from_spec(_m20); _m20.loader.exec_module(m20)


def load_pool():
    cols = ["SiteID", "BDSPPatientID", "StartTime", "AgeAtVisit", "SexDSC", "OrderID", "time_diff",
            "normal", "focalSlowing", "genSlowing", "reports", "impression", "ReportName",
            "BidsFolder", "EEGFolder", "SessionID_new"]
    c = pd.concat([ch for ch in pd.read_csv(CSV, usecols=cols, chunksize=200000, dtype=str, low_memory=False)])
    c["pid"] = c.SiteID.astype(str) + c.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    c["dt"] = pd.to_datetime(c.StartTime, errors="coerce"); c = c.dropna(subset=["dt"])
    c["date"] = c.dt.dt.strftime("%Y%m%d"); c["eeg_datetime"] = c.dt.dt.strftime("%Y%m%d%H%M%S")
    c["eeg_id"] = c.pid + "_" + c.eeg_datetime
    c = c.drop_duplicates("eeg_id")
    c["absd"] = pd.to_numeric(c.time_diff, errors="coerce").abs()
    c = c.dropna(subset=["OrderID"]).sort_values("absd").drop_duplicates(["pid", "date"])  # 1 study/(pid,date)
    nd = c.groupby("OrderID").date.transform("nunique")
    owner = c.sort_values("absd").drop_duplicates("OrderID")[["OrderID", "date"]].rename(columns={"date": "own"})
    c = c.merge(owner, on="OrderID", how="left"); c["clean_pair"] = (nd == 1) | (c.date == c.own)
    c["is_focal"] = c.focalSlowing.isin(["1", "1.0"]); c["is_gen"] = c.genSlowing.isin(["1", "1.0"])
    c["is_normal"] = c.normal.isin(["1", "1.0"]); c["is_abn"] = c.is_focal | c.is_gen
    c["txt"] = (c.impression.fillna("") + " " + c.reports.fillna("")).str.lower()
    return c[c.clean_pair]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", type=int, default=27000)
    ap.add_argument("--src", default="data/manifest/report_manifest_v3.parquet"); a = ap.parse_args()
    man = pd.read_parquet(a.src)
    have = set(man.eeg_id)
    need = max(0, a.target - len(man))
    print(f"manifest v3: {len(man)} | target {a.target} | need +{need} expansion EEGs")
    pool = load_pool()
    new = pool[~pool.eeg_id.isin(have) & ~(pool.pid + "_" + pool.date).isin(
        set(man.patient_id.astype(str) + "_" + man.eeg_datetime.astype(str).str[:8]))].copy()
    # balanced: half abnormal (the valuable tail), half clean-normal
    abn = new[new.is_abn].head(need // 2)
    nrm = new[new.is_normal & ~new.is_abn].head(need - len(abn))
    exp = pd.concat([abn, nrm]).copy()
    exp["focal_region"] = np.where(exp.is_focal, exp.txt.map(m20.extract_region4), np.nan)
    exp["focal_side"] = np.where(exp.is_focal, exp.txt.map(m20.extract_side), np.nan)
    exp["focal_band"] = np.where(exp.is_focal, exp.txt.map(m20.extract_band), np.nan)
    exp["gen_band"] = np.where(exp.is_gen, exp.txt.map(m20.extract_band), np.nan)
    er = pd.DataFrame({
        "eeg_id": exp.eeg_id, "patient_id": exp.pid, "eeg_datetime": exp.eeg_datetime, "src": "expansion",
        "age": pd.to_numeric(exp.AgeAtVisit, errors="coerce"), "sex": exp.SexDSC,
        "is_normal": exp.is_normal.astype(int), "is_abnormal": exp.is_abn.astype(int),
        "has_focal_slow": exp.is_focal.astype(int), "has_gen_slow": exp.is_gen.astype(int),
        "clean_normal": (exp.is_normal & ~exp.is_abn).astype(int),
        "focal_region": exp.focal_region, "focal_side": exp.focal_side, "focal_band": exp.focal_band,
        "gen_topography": np.nan, "gen_band": exp.gen_band, "clean_pair": True, "same_date_ambiguous": False,
        "report_note_name": exp.ReportName, "report_text": exp.reports, "report_impression": exp.impression,
        "bids_task": exp.EEGFolder, "report_session_id": exp.SessionID_new,
        "source_subject_dir": S3_BIDS + "/" + exp.SiteID + "/sub-" + exp.pid + "/",
        "bucket_key": "run-bucket/edf/" + exp.eeg_id + ".edf"})

    out = pd.concat([man, er], ignore_index=True).drop_duplicates("eeg_id")
    # schema alignment: panel columns (cohort/expansion/backfill are not panels)
    for col, val in [("panel", False), ("panel_set", "none")]:
        if col not in out.columns:
            out[col] = val
    out["role"] = np.select([out.clean_normal == 1, out.is_abnormal == 1], ["normal_ref", "abnormal"], "unlabeled")
    out["n_bytes"] = pd.array([pd.NA] * len(out), dtype="Int64"); out["sha256"] = pd.NA  # stamped at pull

    path = DIR / "report_manifest_v4.parquet"; out.to_parquet(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (DIR / "report_manifest_v4.meta.json").write_text(json.dumps({
        "version": 4, "supersedes": "report_manifest_v3", "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_eeg": int(len(out)), "n_patients": int(out.patient_id.nunique()),
        "by_src": {k: int(v) for k, v in out.src.value_counts().items()},
        "n_abnormal": int((out.is_abnormal == 1).sum()), "n_clean_normal": int((out.clean_normal == 1).sum()),
        "panels": "columns present (panel/panel_set/role); OccasionNoise+MoE EEGs appended by scripts/127",
        "sha256": sha}, indent=2))
    print(f"wrote {path}: {len(out)} EEGs | by src {dict(out.src.value_counts())} | "
          f"abnormal {int((out.is_abnormal==1).sum())} clean-normal {int((out.clean_normal==1).sum())}")


if __name__ == "__main__":
    main()
