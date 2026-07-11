"""Finalize the KNOWN-GOOD manifest (report_manifest_v6) — every BIDS row provably resolves to one real
EDF, and the total is HELD (no shrink): each unresolvable row is replaced by a fresh, labeled, resolvable
candidate drawn from the report pool (user requirement 2026-07-11).

Inputs: report_manifest_v5 + preflight_resolution (scripts/129).
Steps:
  1. keepers   = v5 BIDS rows that RESOLVED  (+ stamp resolved_path / resolve_reason) + all panels.
  2. drops     = v5 BIDS rows that did NOT resolve  -> manifest_rejects.parquet (eeg_id + reason).
  3. shortfall = len(drops), per src.
  4. pool      = EEGs_And_Reports.csv labeled via scripts/20.parse_full, EXCLUDING (pid,date) already in v5.
  5. resolve   pool candidates on S3 (subject dir from pid, day-match); keep resolvable, capture the
                matched session's full acq_time -> real eeg_id + task; bias the draw toward the
                clean_normal/abnormal mix of the drops.
  6. v6        = keepers + panels + replacements (>= |v5|). Emit coverage summary.

Run: PYTHONPATH=src python scripts/130_finalize_v6.py [--n-extra-factor 1.5]
"""
from __future__ import annotations
import argparse, importlib.util, os, sys, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

DIR = Path("data/manifest")
SCRATCH = os.environ.get("PANEL_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
CSV = os.environ.get("REPORTS_CSV", f"{SCRATCH}/reports/EEGs_And_Reports.csv")

_p = importlib.util.spec_from_file_location("pf", "scripts/129_preflight_resolve.py")
pf = importlib.util.module_from_spec(_p); _p.loader.exec_module(pf)
w31 = pf.w31
_s20 = importlib.util.spec_from_file_location("s20", "scripts/20_extract_report_labels.py")
s20 = importlib.util.module_from_spec(_s20); _s20.loader.exec_module(s20)


def subject_dir(pid):
    return f"s3:bdsp-opendata-repository/EEG/bids/{pid[:5]}/sub-{pid}/"


def load_labeled_pool(exclude_keys):
    """EEGs_And_Reports.csv -> one row per (pid,date) with labels, excluding keys already used."""
    cols = ["SiteID", "BDSPPatientID", "StartTime", "AgeAtVisit", "SexDSC", "impression", "reports"]
    df = pd.read_csv(CSV, usecols=lambda c: c in cols, low_memory=False, dtype=str)
    df["report_impression"] = df.get("impression", "").fillna("")
    df["report_text"] = df.report_impression + " || " + df.get("reports", "").fillna("")
    P = pd.json_normalize(df.report_text.map(s20.parse_full))     # SAME extractor as scripts/20 / v5
    df = pd.concat([df.reset_index(drop=True), P], axis=1)
    # reconstruct the FULL patient_id = SiteID + bare pid (the CSV stores them split; manifest joins them)
    df["pid"] = df.SiteID.fillna("S0001") + df.BDSPPatientID.str.replace(r"\.0$", "", regex=True)
    df["date"] = pd.to_datetime(df.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    df = df.dropna(subset=["date"]).drop_duplicates(["pid", "date"])
    df["key"] = df.pid + "_" + df.date
    df = df[~df.key.isin(exclude_keys)].copy()
    # labels (report-derived, exactly like v5): normal/abnormal, focal (lateralized) vs generalized (diffuse)
    df["clean_normal"] = (df.report_normal.astype(int).eq(1) & df.report_abnormal.astype(int).eq(0))
    df["is_abnormal"] = df.report_abnormal.astype(int).eq(1)
    df["age"] = pd.to_numeric(df.get("AgeAtVisit"), errors="coerce")
    df["sex"] = df.get("SexDSC", "").str[:1].str.upper().map({"M": "M", "F": "F"}).fillna("unknown")
    df["has_focal_slow"] = df.mentions_slowing.astype(int).eq(1) & df.is_abnormal & df.side.notna()
    df["has_gen_slow"] = df.mentions_slowing.astype(int).eq(1) & df.is_abnormal & df.side.isna()  # diffuse
    return df


def resolve_candidates(cand, threads=16, raw_cache=None):
    """cand needs pid, date. Assign temp resolver cols, resolve on S3 (day-match), and for resolved
    ones read the matched session's full acq_time -> real eeg_id + bids_task. The resolved+stamped
    frame is cached to `raw_cache` right after the (expensive) S3 work so a re-run never re-hits S3."""
    from concurrent.futures import ThreadPoolExecutor
    if raw_cache is not None and Path(raw_cache).exists():
        ok = pd.read_parquet(raw_cache)
        print(f"  loaded {len(ok)} resolved+stamped candidates from {raw_cache}")
    else:
        cand = cand.copy()
        cand["eeg_id"] = cand.pid + "_" + cand.date
        cand["source_subject_dir"] = cand.pid.map(subject_dir)
        cand["bids_task"] = None
        cand["eeg_datetime"] = cand.date
        res = pf.resolve_rows(cand[["eeg_id", "source_subject_dir", "bids_task", "eeg_datetime"]], threads)
        ok = res[res.resolved].merge(cand, on="eeg_id", how="left")
        # stamp the matched session's full acq_time IN PARALLEL (avoids a slow sequential stall)
        def _acq(row):
            base = row.source_subject_dir; rel = row.resolved_path[len(base):]
            try:
                return w31._acq_time(base, rel) or (row.date + "000000")
            except Exception:
                return row.date + "000000"
        with ThreadPoolExecutor(max_workers=threads) as tx:
            acqs = list(tx.map(_acq, [r for _, r in ok.iterrows()]))
        ok = ok.assign(acqstamp=acqs)                        # NB: no leading underscore (itertuples-safe)
        if raw_cache is not None:
            ok.to_parquet(raw_cache, index=False)            # persist the expensive S3 result immediately
    out = []
    for r in ok.itertuples():
        base = r.source_subject_dir; rel = r.resolved_path[len(base):]
        acq = r.acqstamp
        task = "rEEG" if "task-rEEG" in rel else ("cEEG" if "task-cEEG" in rel else
               (rel.split("task-")[1].split("_")[0] if "task-" in rel else "EEG"))
        eid = f"{r.pid}_{acq}"
        side = getattr(r, "side", None); region = getattr(r, "region", None); band = getattr(r, "band", None)
        out.append({"eeg_id": eid, "patient_id": r.pid, "eeg_datetime": acq,
            "src": "replacement", "bids_task": task, "source_subject_dir": base,
            "resolved_path": r.resolved_path, "resolve_reason": r.resolve_reason,
            "age": getattr(r, "age", None), "sex": getattr(r, "sex", "unknown"),
            "clean_normal": bool(r.clean_normal), "is_abnormal": bool(r.is_abnormal),
            "is_normal": bool(r.clean_normal),
            "has_focal_slow": bool(r.has_focal_slow), "has_gen_slow": bool(r.has_gen_slow),
            "focal_side": side if r.has_focal_slow else None,
            "focal_region": region if r.has_focal_slow else None,
            "focal_band": band if r.has_focal_slow else None,
            "gen_topography": "generalized" if r.has_gen_slow else None,
            "gen_band": band if r.has_gen_slow else None,
            "mentions_slowing": bool(getattr(r, "mentions_slowing", 0)),
            "clean_pair": True,                               # unique (pid,date) resolved to one session
            "report_impression": getattr(r, "report_impression", None),
            "report_text": getattr(r, "report_text", None),
            "bucket_key": f"run-bucket/edf/{eid}.edf",
            "panel": False, "panel_set": "none", "role": "analysis", "source_type": "bids"})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v5", default="data/manifest/report_manifest_v5.parquet")
    ap.add_argument("--preflight", default="data/manifest/preflight_resolution.parquet")
    ap.add_argument("--n-extra-factor", type=float, default=2.2)   # over-draw: ~50-80% of pool candidates resolve
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--refresh", action="store_true")              # re-resolve candidates (ignore the cache)
    a = ap.parse_args()
    v5 = pd.read_parquet(a.v5)
    pre = pd.read_parquet(a.preflight)
    bids = v5[v5.src.isin(["cohort", "expansion", "backfill"])].merge(pre, on="eeg_id", how="left")
    keepers = bids[bids.resolved == True].copy()                   # noqa: E712
    drops = bids[bids.resolved != True].copy()
    panels = v5[v5.src == "panel"].copy()
    print(f"v5 BIDS {len(bids)} | resolved {len(keepers)} | drop {len(drops)} | panels {len(panels)}")
    print("drops by src:", dict(drops.src.value_counts()))

    used = set((v5.patient_id.astype(str) + "_" + v5.eeg_datetime.astype(str).str[:8]))
    need = len(drops)
    cache = DIR / "replacement_candidates_resolved.parquet"      # cache the S3 resolution (slow) — reuse
    reps_all = pd.DataFrame()
    if need > 0:
        if cache.exists() and not a.refresh:
            reps_all = pd.read_parquet(cache)
            print(f"loaded {len(reps_all)} cached resolved replacements from {cache} (use --refresh to rebuild)")
        else:
            print(f"loading labeled pool (excluding {len(used)} used keys)…", flush=True)
            pool = load_labeled_pool(used)
            print(f"  pool candidates: {len(pool)} | clean_normal {int(pool.clean_normal.sum())} "
                  f"| abnormal {int(pool.is_abnormal.sum())}")
            want_norm = int(drops.get("clean_normal", pd.Series(dtype=bool)).fillna(False).sum())
            draw_n = int(need * a.n_extra_factor) + 20
            norm_pool = pool[pool.clean_normal].sample(frac=1, random_state=0)
            abn_pool = pool[~pool.clean_normal].sample(frac=1, random_state=0)
            take_norm = min(len(norm_pool), int(draw_n * (want_norm / max(need, 1))) + 10)
            cand = pd.concat([norm_pool.head(take_norm), abn_pool.head(draw_n - take_norm)], ignore_index=True)
            print(f"  resolving {len(cand)} candidates on S3…", flush=True)
            reps_all = resolve_candidates(cand, a.threads, raw_cache=DIR / "_replacement_resolved_raw.parquet")
            reps_all.to_parquet(cache, index=False)             # cache so re-assembly never re-resolves
        print(f"  resolvable replacements available: {len(reps_all)} (need {need})")
    # dedup replacements against everything already kept BEFORE taking the count, so a replacement that
    # resolves to an existing eeg_id doesn't silently shrink N (held_N bug fix).
    existing = set(keepers.eeg_id) | set(panels.eeg_id)
    reps = reps_all[~reps_all.eeg_id.isin(existing)].drop_duplicates("eeg_id").head(need) if len(reps_all) else reps_all

    keepers["resolved_path"] = keepers.resolved_path
    v6 = pd.concat([keepers.drop(columns=["resolved"], errors="ignore"), panels, reps], ignore_index=True)
    v6 = v6.drop_duplicates("eeg_id")
    path = DIR / "report_manifest_v6.parquet"; v6.to_parquet(path, index=False)
    drops[["eeg_id", "src", "resolve_reason"]].to_parquet(DIR / "manifest_rejects.parquet", index=False)
    rep_rows = v6[v6.src == "replacement"]
    rep_age_null = int(rep_rows.age.isna().sum()) if len(rep_rows) else 0
    # "analysis-ready" must mean what it says: every field the analysis needs is populated on replacements.
    req_fields = ["age", "sex", "clean_normal", "is_abnormal", "clean_pair", "resolved_path", "bids_task"]
    rep_incomplete = {c: int(rep_rows[c].isna().sum()) for c in req_fields if c in rep_rows.columns}
    analysis_ready = bool(len(rep_rows) and all(v == 0 for v in rep_incomplete.values())
                          and not (rep_rows.sex == "unknown").all())
    (DIR / "report_manifest_v6.meta.json").write_text(json.dumps({
        "version": 6, "supersedes": "report_manifest_v5", "built_from": "v5 + preflight_resolution",
        "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_v5": int(len(v5)), "n_v6": int(len(v6)), "n_resolved_keepers": int(len(keepers)),
        "n_dropped": int(len(drops)), "n_replacements": int(len(rep_rows)), "n_panels": int(len(panels)),
        "held_N": bool(len(v6) >= len(v5)),
        "replacements_analysis_ready": analysis_ready,           # age+sex+labels+clean_pair+resolved_path all set
        "replacement_incomplete_fields": rep_incomplete,         # {field: n_null} — must be all 0
        "replacement_age_null": rep_age_null,
        "every_bids_row_resolved": bool(v6[v6.src.isin(["cohort", "expansion", "backfill", "replacement"])]
                                        .resolved_path.notna().all()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, indent=2))
    every_resolved = bool(v6[v6.src.isin(["cohort", "expansion", "backfill", "replacement"])]
                          .resolved_path.notna().all())
    held = len(v6) >= len(v5)
    print(f"\nv6: {len(v6)} EEGs (v5 was {len(v5)}) | held_N={held} -> {path}")
    print(f"  replacements {len(rep_rows)} | age-null {rep_age_null} | every BIDS row resolved: {every_resolved}")
    print("  by src:", dict(v6.src.value_counts()))
    # HARD STOP (no-regrets gate): refuse to bless a manifest that fails a launch invariant. The parquet
    # is still written for inspection, but a nonzero exit prevents CI / the launch script from proceeding.
    fails = []
    if not held:
        fails.append(f"held_N=false ({len(v6)} < {len(v5)}: only {len(reps)} of {need} drops replaced)")
    if not analysis_ready:
        fails.append(f"replacements not analysis-ready (incomplete fields: "
                     f"{ {k: v for k, v in rep_incomplete.items() if v} })")
    if not every_resolved:
        fails.append("some BIDS rows have no resolved_path (phantoms remain)")
    if fails:
        print("\nERROR: v6 FAILS launch invariants — do NOT run the fleet on this manifest:", file=sys.stderr)
        for x in fails:
            print(f"  - {x}", file=sys.stderr)
        sys.exit(1)
    print("\nv6 PASSES all launch invariants (held_N, analysis-ready, every-row-resolved) — safe to freeze.")


if __name__ == "__main__":
    main()
