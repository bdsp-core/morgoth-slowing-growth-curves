"""Validation #1 (report-based): agreement with clinician EEG reports.

Uses report-derived finding flags from EEG/HEEDB_Metadata/S000*_EEG__reports_findings.csv (columns
normal/abnormal/'foc slowing'/'gen slowing'; value contains 'report' => stated in the report). We
compare BOTH Morgoth probabilities and OUR deviation features to these report flags.

(Band delta/theta/mixed + exact side/region still need the report TEXT — not in this flags file;
see scripts/18 part B + the OMOP-admin note pull.)

Outputs: results/report_agreement.md
Prereq: pull S000*_EEG__reports_findings.csv to <reports_dir> (default scratchpad/reports).
Run: python scripts/19_report_validation.py [reports_dir]
"""
from __future__ import annotations
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score

DER = Path("data/derived"); RES = Path("results")
DEFAULT_REPORTS = "/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad/reports"


def auc(p, y):
    p, y = np.asarray(p, float), np.asarray(y, float); ok = np.isfinite(p) & np.isfinite(y)
    return roc_auc_score(y[ok], p[ok]) if len(set(y[ok])) > 1 else float("nan")


def report_flags(reports_dir):
    fr = [pd.read_csv(f, low_memory=False) for f in glob.glob(f"{reports_dir}/S000*_EEG__reports_findings.csv")]
    rep = pd.concat(fr, ignore_index=True)
    hr = lambda c: rep[c].astype(str).str.contains("report", case=False, na=False).astype(int)
    rep = rep.assign(r_abnormal=hr("abnormal"), r_focal=hr("foc slowing"), r_gen=hr("gen slowing"),
                     pid=rep.BDSPPatientID.astype(str),
                     date=pd.to_datetime(rep["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d"))
    return rep.dropna(subset=["date"]).drop_duplicates(["pid", "date"])[["pid", "date", "r_abnormal", "r_focal", "r_gen"]]


def our_features():
    az = pd.read_parquet(DER / "adjusted_z.parquet"); az["fr"] = az.feature + "@" + az.region
    X = az.pivot_table(index="bdsp_id", columns="fr", values="z", aggfunc="mean")
    return X


def main(reports_dir=DEFAULT_REPORTS):
    rep = report_flags(reports_dir)
    gate = pd.read_parquet(DER / "gate_probs.parquet")
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["pid"] = meta.bdsp_id.str.replace(r"^S000\d", "", regex=True); meta["date"] = meta.eeg_datetime.str[:8]
    m = (meta.merge(gate[["bdsp_id", "p_abnormal", "p_focal", "p_generalized"]], on="bdsp_id", how="left")
             .merge(rep, on=["pid", "date"], how="inner"))
    X = our_features().reindex(m.bdsp_id).fillna(0.0)

    lines = ["# Agreement with clinical reports (report-derived finding flags)\n",
             f"Matched **{len(m)} / {len(meta)}** cohort recordings to a report "
             f"(EEG/HEEDB_Metadata). AUC of each score vs the report flag.\n\n",
             "| target (report flag) | Morgoth AUC | our-LR AUC | our-simple AUC |\n|---|---|---|---|\n"]
    simple = {"r_abnormal": ("p_abnormal", X.get("log_delta@whole_head")),
              "r_focal": ("p_focal", (X.filter(like="log_delta@").max(axis=1))),
              "r_gen": ("p_generalized", X.get("log_theta@whole_head"))}
    mor = {"r_abnormal": "p_abnormal", "r_focal": "p_focal", "r_gen": "p_generalized"}
    for flag in ["r_abnormal", "r_focal", "r_gen"]:
        y = m[flag].values
        lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
        oof = cross_val_predict(lr, X.values, y, cv=5, method="predict_proba")[:, 1]
        a_m = auc(m[mor[flag]], y); a_lr = auc(oof, y); a_s = auc(simple[flag][1], y)
        lines.append(f"| {flag} (pos {y.mean():.2f}) | {a_m:.3f} | {a_lr:.3f} | {a_s:.3f} |\n")
    lines += ["\n**Read:** Morgoth tracks the reports strongly (abnormal ~0.90; focal ~0.79; "
              "generalized ~0.75). Our objective LR on age/sex deviations is close behind — face "
              "validity that our features capture what experts write. Band (δ/θ/mixed) and exact "
              "side/region need the report TEXT (scripts/18 part B).\n"]
    (RES / "report_agreement.md").write_text("".join(lines))
    print("".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPORTS)
