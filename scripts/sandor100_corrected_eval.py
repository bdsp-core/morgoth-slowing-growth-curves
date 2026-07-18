"""Sandor_100 focal + generalized, evaluated against the CORRECTED ground truth (the actual 14-expert vote
majority; the workbook `majority` column is corrupted for the focal sheet — 23/100 disagreements). Compares
the baseline focal head (scripts/55), the de-confounded combined head (scripts/66), the Morgoth gate, and
SCORE-AI, with % experts under and bootstrap CIs. Decides which focal head to keep in production.

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/sandor100_corrected_eval.py
"""
from __future__ import annotations
import os, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

m55 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py"))
importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py").loader.exec_module(m55)
m54 = m55.m54; m46 = m54.m49.m46; m53 = m54.m49
m66 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py"))
importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py").loader.exec_module(m66)
m53b = m66.m53b

SM = "data/derived/segment_master"
SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100"); MR = SB_DIR / "Morgoth_results"
FOC_R = [f"{c}_{s}" for c in m55.FOC0 for s in ("mean", "p90", "max", "prev")] + ["age"]


def baseline_focal_head():
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    Rtr = m55.aggregate(S[S.dataset == "report"]); Rtr = Rtr[Rtr.split == "train"]
    med = Rtr[FOC_R].median()
    return m54.Head().fit(Rtr[FOC_R].fillna(med).values, Rtr.y_focal.astype(int).values), med


def sandor_baseline_scores(head, med):
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    rows = []
    for out in sorted(Path(SM).glob("eeg_id=SB_*")):
        eid = out.name.split("=")[1]; key = f"ID{int(eid.split('_')[1]):03d}"
        sf = m53b.seg_feats(eid, age.get(key, np.nan))
        if sf is None or sf.empty:
            continue
        sf["eeg_id"] = eid; sf["dataset"] = "sb"; sf["split"] = "test"; sf["y_focal"] = 0; sf["y_gen"] = 0
        R = m55.aggregate(sf)
        rows.append({"eid": eid, "key": key, "base": float(head.score(R[FOC_R].fillna(med).values)[0])})
    return pd.DataFrame(rows)


def under(y, s, wide):
    ok = np.isfinite(s) & np.isfinite(y)
    cur = m54.panel_curve(None, y[ok], np.asarray(s)[ok], m46.expert_points(wide), "#000", "x")
    lo, hi = m54.boot_ci(y[ok], np.asarray(s)[ok])
    return cur["auc"], lo, hi, cur["ur"]


def main():
    bh, bmed = baseline_focal_head()
    base = sandor_baseline_scores(bh, bmed)
    ff = pd.read_excel(MR / "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); ff["key"] = ff.file_name.astype(str).str.strip()
    m = base.merge(ff, on="key")
    ec = [c for c in ff.columns if c.startswith("expert_")]
    wide = m.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    y_corr = (wide.mean(axis=1).values >= 0.5).astype(int)                 # CORRECTED ground truth
    y_stated = m.majority.astype(int).values
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    comb = m66.focal_score(list(zip(m.eid, [age.get(k, np.nan) for k in m.key]))); m["comb"] = m.eid.map(comb).values

    print(f"n={len(m)}  focal+ (corrected expert vote)={int(y_corr.sum())}  focal+ (stated corrupted)={int(y_stated.sum())}\n")
    print(f"{'FOCAL model':34} {'vs CORRECTED label':28} {'vs stated (corrupt)':20}")
    for name, s in [("ours: baseline head (55)", m.base.values), ("ours: de-confounded combined (66)", m.comb.values),
                    ("Morgoth gate", m.M_pred.values), ("SCORE-AI", m.S_pred.values)]:
        a, lo, hi, ur = under(y_corr, s, wide); a2 = roc_auc_score(y_stated, s)
        print(f"{name:34} AUROC {a:.3f} [{lo:.2f}-{hi:.2f}] {ur:3.0f}% under   AUROC {a2:.3f}")


if __name__ == "__main__":
    main()
