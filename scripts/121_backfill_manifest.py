"""Backfill the report manifest from the full BDSP report pool so every coverage cell reaches the target
(MBW: all squares green >=200; age bins 0-1 and 13-17 >=500). Uses the 4-region taxonomy (scripts/20
REGION4). PHI: reports are BDSP de-identified (may be committed, docs/analysis_plan.md §11).

Method:
  1. Full pool = EEGs_And_Reports.csv, deduped to one row per EEG (pid+StartTime).
  2. Clean pairing (OrderID owned by nearest EEG) + single EEG per (pid,date) [no same-date ambiguity].
  3. Extract findings: structured flags (normal/focalSlowing/genSlowing) + text (region4/side/band, gen topo).
  4. Existing cohort identified by (pid, date) from report_manifest_v1; re-extract its region4 from report_text.
  5. Deficit per cell = TARGET - current; greedily select NEW cleanly-paired EEGs to fill each deficit,
     plus enough NEW EEGs in the young age bins.
  6. Write backfill_candidates + a combined coverage crosstab; scripts/123 re-plots.

Run: PYTHONPATH=src python scripts/121_backfill_manifest.py [--target 250] [--age-target 550]
"""
from __future__ import annotations
import argparse, importlib.util
from pathlib import Path
import numpy as np, pandas as pd

CSV = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
       "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv")
MANIFEST = "data/manifest/report_manifest_v1.parquet"
OUTDIR = Path("data/manifest"); OUTDIR.mkdir(parents=True, exist_ok=True)
AGE_BINS = [0, 1, 6, 13, 18, 45, 60, 75, 200]
AGE_LAB = ["0-1", "1-5", "6-12", "13-17", "18-44", "45-59", "60-74", "75+"]
YOUNG = ["0-1", "13-17"]

_m20 = importlib.util.spec_from_file_location("m20", "scripts/20_extract_report_labels.py")
m20 = importlib.util.module_from_spec(_m20); _m20.loader.exec_module(m20)


def load_pool():
    cols = ["SiteID", "BDSPPatientID", "StartTime", "AgeAtVisit", "SexDSC", "OrderID", "time_diff",
            "normal", "focalSlowing", "genSlowing", "reports", "impression", "ReportName",
            "HashFolderName", "HashFileName", "BidsFolder", "EEGFolder"]
    c = pd.concat([ch for ch in pd.read_csv(CSV, usecols=cols, chunksize=200000, dtype=str, low_memory=False)])
    c["pid"] = c.SiteID.astype(str) + c.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    c["dt"] = pd.to_datetime(c.StartTime, errors="coerce")
    c = c.dropna(subset=["dt"])
    c["date"] = c.dt.dt.strftime("%Y%m%d")
    c["eeg_id"] = c.pid + "_" + c.dt.dt.strftime("%Y%m%d%H%M%S")
    c = c.drop_duplicates("eeg_id")
    c["absd"] = pd.to_numeric(c.time_diff, errors="coerce").abs()
    c = c.dropna(subset=["OrderID"])
    # COLLAPSE to one study per (pid,date) keeping the file nearest the report (same-day files are one cEEG
    # study, not distinct studies) — matches scripts/88; excluding them all discards ~114k EEGs wrongly.
    c = c.sort_values("absd").drop_duplicates(["pid", "date"])
    nd = c.groupby("OrderID").date.transform("nunique")
    owner = c.sort_values("absd").drop_duplicates("OrderID")[["OrderID", "date"]].rename(columns={"date": "own"})
    c = c.merge(owner, on="OrderID", how="left")
    c["clean_pair"] = (nd == 1) | (c.date == c.own)
    c["age"] = pd.to_numeric(c.AgeAtVisit, errors="coerce")
    c["age_bin"] = pd.cut(c.age, bins=AGE_BINS, labels=AGE_LAB, right=False)
    c["txt"] = (c.impression.fillna("") + " " + c.reports.fillna("")).str.lower()
    c["is_focal"] = c.focalSlowing.isin(["1", "1.0"])
    c["is_gen"] = c.genSlowing.isin(["1", "1.0"])
    c["is_normal"] = c.normal.isin(["1", "1.0"])
    c["eeg_path"] = (c.BidsFolder.fillna("") + "/" + c.EEGFolder.fillna("") + "/" + c.HashFileName.fillna("")).str.strip("/")
    return c


def extract_findings(df):
    df = df.copy()
    f = df.is_focal
    df.loc[f, "focal_region"] = df.loc[f, "txt"].map(m20.extract_region4)
    df.loc[f, "focal_side"] = df.loc[f, "txt"].map(m20.extract_side)
    df.loc[f, "focal_band"] = df.loc[f, "txt"].map(m20.extract_band)
    g = df.is_gen
    gr = df.loc[g, "txt"].map(m20.extract_region4)
    df.loc[g, "gen_topography"] = gr.map(lambda r: "anterior" if r == "frontal" else ("posterior" if r == "posterior" else "unspec"))
    df.loc[g, "gen_band"] = df.loc[g, "txt"].map(m20.extract_band)
    return df


def cohort_region4(manifest):
    """Re-extract the existing cohort's focal region under the 4-region taxonomy from its report_text."""
    m = manifest.copy()
    m["date"] = m.eeg_datetime.astype(str).str[:8]
    m["pid"] = m.patient_id.str.replace(r"^S000\d", "", regex=True)
    fm = m[m.has_focal_slow == 1].copy()
    fm["focal_region"] = fm.report_text.fillna("").str.lower().map(m20.extract_region4)
    m.loc[fm.index, "focal_region"] = fm["focal_region"]
    return m


def cell_counts(df, kind):
    if kind == "focal_region_band":
        d = df[df.get("has_focal_slow", df.get("is_focal")) == 1] if "has_focal_slow" in df else df[df.is_focal]
        return pd.crosstab(d.focal_region, d.focal_band)
    if kind == "focal_side_band":
        d = df[df.get("has_focal_slow", df.get("is_focal")) == 1] if "has_focal_slow" in df else df[df.is_focal]
        return pd.crosstab(d.focal_side, d.focal_band)
    if kind == "gen_topo_band":
        d = df[df.get("has_gen_slow", df.get("is_gen")) == 1] if "has_gen_slow" in df else df[df.is_gen]
        return pd.crosstab(d.gen_topography, d.gen_band)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=250)
    ap.add_argument("--age-target", type=int, default=550)
    a = ap.parse_args()

    print("loading pool…")
    pool = extract_findings(load_pool())
    print(f"  pool: {len(pool):,} EEGs | cleanly-paired single-per-date: {int(pool.clean_pair.sum()):,}")
    man = cohort_region4(pd.read_parquet(MANIFEST))
    man_clean = man[(man.clean_pair == True) & (~man.same_date_ambiguous)]
    cohort_keys = set(man.pid.astype(str) + "_" + man.date.astype(str))     # (pid,date) already in cohort

    new = pool[pool.clean_pair & ~(pool.pid + "_" + pool.date).isin(cohort_keys)].copy()
    print(f"  NEW cleanly-paired EEGs available (not in cohort): {len(new):,}")

    # ---- fill each cell's deficit (target - current) with NEW cleanly-paired EEGs ----
    selected = set()
    def deficit_fill(df_new, kind, rowcol, target):
        cur = cell_counts(man_clean, kind)
        added = 0
        for keys, grp in df_new.groupby(rowcol, observed=True):
            r, c = keys if isinstance(keys, tuple) else (keys, None)
            have = int(cur.loc[r, c]) if (r in cur.index and c in cur.columns) else 0
            need = max(0, target - have)
            if need > 0:
                take = grp.head(need)
                selected.update(take.eeg_id.tolist()); added += len(take)
        return added

    nf = deficit_fill(new[new.is_focal].dropna(subset=["focal_region", "focal_band"]),
                      "focal_region_band", ["focal_region", "focal_band"], a.target)
    ns = deficit_fill(new[new.is_focal].dropna(subset=["focal_side", "focal_band"]),
                      "focal_side_band", ["focal_side", "focal_band"], a.target)
    ng = deficit_fill(new[new.is_gen].dropna(subset=["gen_topography", "gen_band"]),
                      "gen_topo_band", ["gen_topography", "gen_band"], a.target)
    # young age bins
    na = 0
    for ab in YOUNG:
        have = int((man_clean.assign(age_bin=pd.cut(pd.to_numeric(man_clean.age, errors="coerce"),
                    bins=AGE_BINS, labels=AGE_LAB, right=False)).age_bin == ab).sum())
        need = max(0, a.age_target - have)
        cand = new[(new.age_bin == ab) & (~new.eeg_id.isin(selected))].head(need)
        selected.update(cand.eeg_id.tolist()); na += len(cand)
        print(f"  age {ab}: cohort {have} + {len(cand)} -> {have+len(cand)}")

    bf = new[new.eeg_id.isin(selected)].copy()
    print(f"\nBACKFILL selected: {len(bf):,} NEW EEGs "
          f"(focal-region fill {nf}, side fill {ns}, gen fill {ng}, young-age fill {na})")

    keep = ["eeg_id", "pid", "date", "age", "SexDSC", "is_normal", "is_focal", "is_gen",
            "focal_region", "focal_side", "focal_band", "gen_topography", "gen_band",
            "clean_pair", "eeg_path", "ReportName", "impression", "reports"]
    bf[[k for k in keep if k in bf.columns]].rename(columns={"reports": "report_text", "impression": "report_impression",
                                                             "ReportName": "report_note_name", "SexDSC": "sex"}
        ).to_parquet(OUTDIR / "backfill_candidates_v1.parquet", index=False)
    print(f"wrote {OUTDIR/'backfill_candidates_v1.parquet'}")

    # combined coverage preview (cohort clean + backfill), 4-region
    comb = pd.concat([
        man_clean.assign(is_focal=man_clean.has_focal_slow == 1, is_gen=man_clean.has_gen_slow == 1)[
            ["is_focal", "is_gen", "focal_region", "focal_band", "focal_side", "gen_topography", "gen_band", "age"]],
        bf[["is_focal", "is_gen", "focal_region", "focal_band", "focal_side", "gen_topography", "gen_band", "age"]]],
        ignore_index=True)
    print("\n=== COMBINED focal region×band ===")
    print(cell_counts(comb, "focal_region_band").to_string())
    print("\n=== COMBINED gen topo×band ===")
    print(cell_counts(comb, "gen_topo_band").to_string())
    comb.to_parquet(OUTDIR / "coverage_combined_preview.parquet", index=False)


if __name__ == "__main__":
    main()
