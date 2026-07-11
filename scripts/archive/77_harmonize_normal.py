"""(A) HARMONIZE THE NORMAL DEFINITION across cohorts, then re-test the cohort-vs-overnight gap.
The routine cohort uses strict clean_normal (report-normal & no focal slowing & no pathologic gen slowing;
physiologic gen slowing retained). The overnight manifest used a looser filter (report 'normal' mentioned,
rfoc/rgen hardcoded 0). Here we re-derive the SAME strict standard for the overnight set from its own
findings CSVs and re-compute the central rel_delta offset per stage. If the gap persists under the identical
normal definition, the normal-definition asymmetry is NOT the explanation (points to state/population).

Run: PYTHONPATH=src python scripts/77_harmonize_normal.py
"""
from __future__ import annotations
import pandas as pd, numpy as np

CEN = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
FIND = {"S0001": "data/findings/S0001_EEG__reports_findings.csv",
        "S0002": "data/findings/S0002_EEG__reports_findings.csv",
        "I0003": "data/findings/I0003_EEG__reports_findings.csv"}


def findings_flags():
    fs = []
    for s, path in FIND.items():
        try:
            f = pd.read_csv(path, dtype=str, low_memory=False)
        except FileNotFoundError:
            print(f"  (no findings for {s})"); continue
        f["pid"] = f.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
        f["date"] = pd.to_datetime(f["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
        for col in ["normal", "abnormal", "foc slowing", "gen slowing"]:
            f[col.replace(" ", "_")] = (f[col].astype(str).str.contains("report", case=False, na=False)
                                        if col in f else False)
        f["site"] = s
        fs.append(f[["site", "pid", "date", "normal", "abnormal", "foc_slowing", "gen_slowing"]])
    return pd.concat(fs, ignore_index=True)


def main():
    df = pd.read_parquet("data/derived/channel_stage_features.parquet")
    c = df[df.region.isin(CEN)].groupby(["bdsp_id", "stage", "src"]).agg(
        val=("rel_delta", "mean"), age=("age", "first"), clean=("clean_normal", "first")).reset_index()
    # parse site/pid/date from expansion bdsp_id (S0001{pid}_{date})
    exp = c[c.src == "expansion"].copy()
    exp["site"] = exp.bdsp_id.str[:5]
    rest = exp.bdsp_id.str[5:].str.split("_", n=1, expand=True)
    exp["pid"] = rest[0]; exp["date"] = rest[1].str[:8]
    F = findings_flags()
    exp = exp.merge(F, on=["site", "pid", "date"], how="left")
    matched = exp.dropna(subset=["normal"]).bdsp_id.nunique()
    print(f"overnight recs matched to findings: {matched}/{exp.bdsp_id.nunique()}")
    # STRICT standard (same as cohort clean_normal): report-normal, not abnormal, no focal slowing.
    exp["strict"] = (exp.normal == True) & (exp.abnormal != True) & (exp.foc_slowing != True)
    # ultra-strict: also drop ANY generalized slowing mention (upper bound on the definition effect)
    exp["ultra"] = exp.strict & (exp.gen_slowing != True)

    coh = c[(c.src == "cohort") & (c.clean == True)]
    print(f"\n{'stage':<6}{'window':<7}{'routine(clean)':>16}{'overnight(loose)':>18}"
          f"{'overnight(strict)':>19}{'overnight(ultra)':>18}")
    for st in ["W", "N1", "N2", "N3", "REM"]:
        for lo, hi, tag in [(1, 12, "peds"), (20, 60, "adult")]:
            co = coh[(coh.stage == st) & coh.age.between(lo, hi)].val
            e = exp[(exp.stage == st) & exp.age.between(lo, hi)]
            loose = e[e.clean == True].val          # what we used before (blanket clean)
            strict = e[e.strict == True].val
            ultra = e[e.ultra == True].val
            if len(co) < 15 or len(loose) < 15: continue
            print(f"{st:<6}{tag:<7}{co.median():>10.3f}(n{len(co)}){loose.median():>12.3f}(n{len(loose)})"
                  f"{strict.median():>13.3f}(n{len(strict)}){ultra.median():>12.3f}(n{len(ultra)})")
    print("\nIf overnight(strict/ultra) stays far above routine(clean), the normal DEFINITION is not the "
          "cause — the gap is state (drowsy overnight wake) + population (disjoint inpatient cohort).")


if __name__ == "__main__":
    main()
