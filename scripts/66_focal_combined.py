"""Focal v4 — COMBINE region-deviation features (in-domain strong) + finer per-channel raw contrasts
(external robust), de-confounded focal-specific target, trained on the full report cohort. Last hand-crafted
lever before morphology-at-scale. Tests region-only vs finer-only vs combined, in-domain (OccasionNoise) and
external (Sandor). Reuses scripts/53 (seg_feats), 55 (aggregate), 64 (finer feats + cohort).

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/66_focal_combined.py
"""
from __future__ import annotations
import os, importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

m55 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py"))
importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py").loader.exec_module(m55)
m54 = m55.m54; m46 = m54.m49.m46
m53b = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m53b", "scripts/53_single_model_features.py"))
importlib.util.spec_from_file_location("m53b", "scripts/53_single_model_features.py").loader.exec_module(m53b)
m53b.SEG_CAP = 10**9
m64 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m64", "scripts/64_focal_v2_experiment.py"))
importlib.util.spec_from_file_location("m64", "scripts/64_focal_v2_experiment.py").loader.exec_module(m64)

SM = "data/derived/segment_master"
SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100"); MR = SB_DIR / "Morgoth_results"
FOC_R = [f"{c}_{s}" for c in m55.FOC0 for s in ("mean", "p90", "max", "prev")] + ["age"]


def _region_one(args):
    eid, age = args
    sf = m53b.seg_feats(eid, age)
    if sf is None or sf.empty:
        return None
    sf["eeg_id"] = eid; sf["dataset"] = "x"; sf["split"] = "x"; sf["y_focal"] = 0; sf["y_gen"] = 0
    return sf


def region_build(ids_ages):
    with ThreadPoolExecutor(max_workers=14) as ex:
        parts = [p for p in ex.map(_region_one, ids_ages) if p is not None]
    R = m55.aggregate(pd.concat(parts, ignore_index=True))
    return R[[c for c in FOC_R if c in R.columns]]


def combined(ids_ages):
    reg = region_build(ids_ages); fin = m64.build(ids_ages)
    return reg.join(fin, rsuffix="_f", how="inner")


def under(y, s, wide):
    pts = m46.expert_points(wide)
    ok = np.isfinite(s) & np.isfinite(y)
    cur = m54.panel_curve(None, y[ok], np.asarray(s)[ok], pts, "#000", "x")
    return cur["auc"], cur["ur"]


def main():
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = lab[(lab.clean_pair == True) & lab.age.notna()].copy()                                   # noqa: E712
    foc = d.slowing_focal.fillna(False); gen = d.slowing_gen_pathologic.fillna(False); cn = d.clean_normal.fillna(False)
    d = d[(foc | cn | (gen & ~foc)) & (~d.eeg_id.astype(str).str.startswith(("MOE_", "ON_")))].copy()
    d["y"] = foc[d.index].astype(int).values
    d = d[[os.path.exists(f"{SM}/eeg_id={i}") for i in d.eeg_id]]
    tr = pd.concat([d[d.y == 1].sample(min(3000, int((d.y == 1).sum())), random_state=0),
                    d[d.y == 0].sample(min(3000, int((d.y == 0).sum())), random_state=0)])
    print(f"training {len(tr)} report recordings (focal-specific)")
    Rtr = combined(list(zip(tr.eeg_id, tr.age))).join(tr.set_index("eeg_id").y).dropna(subset=["y"])
    REG = [c for c in FOC_R if c in Rtr.columns]; FIN = [c for c in Rtr.columns if c not in REG + ["y"]]
    ALL = REG + FIN

    # OccasionNoise
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet"); occ = pd.read_parquet("data/derived/occasion_features.parquet")
    oage = occ[(occ.stage == "W") & (occ.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    wide = V.dropna(subset=["r1.FN"]).pivot_table(index="fid", columns="rater", values="r1.FN"); wide.index = [f"ON_{int(i)}" for i in wide.index]
    on = [(e, float(oage.get(int(e.split('_')[1]), np.nan))) for e in wide.index if os.path.exists(f"{SM}/eeg_id={e}")]
    Ron = combined(on); keep = wide.index.intersection(Ron.index); Ron = Ron.loc[keep]
    yon = (wide.loc[keep].mean(axis=1) >= 0.5).astype(int).values; won = wide.loc[keep]

    # Sandor
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    sage = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    sbn = lambda nm: int(nm.split("=")[1].split("_")[1])
    sb = [(o.name.split("=")[1], sage.get(f"ID{sbn(o.name):03d}", np.nan)) for o in sorted(Path(SM).glob("eeg_id=SB_*"))]
    Rsb = combined(sb); Rsb["key"] = [f"ID{int(i.split('_')[1]):03d}" for i in Rsb.index]
    ff = pd.read_excel(MR / "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); ff["key"] = ff.file_name.astype(str).str.strip()
    Rsb = Rsb.merge(ff, on="key"); ysb = Rsb.majority.astype(int).values
    wsb = Rsb.set_index("key")[[c for c in ff.columns if c.startswith("expert_")]].apply(pd.to_numeric, errors="coerce")

    print(f"\n{'feature set':22} | {'OccasionNoise (in-domain)':26} | {'Sandor (external)':20}")
    for name, cs in [("region-deviation", REG), ("finer per-channel", FIN), ("COMBINED", ALL)]:
        med = Rtr[cs].median(); h = m54.Head().fit(Rtr[cs].fillna(med).values, Rtr.y.astype(int).values)
        ao, uo = under(yon, h.score(Ron[cs].fillna(med).values), won)
        as_, us = under(ysb, h.score(Rsb[cs].fillna(med).values), wsb)
        print(f"{name:22} | AUROC {ao:.3f}  {uo:2.0f}% under        | AUROC {as_:.3f}  {us:2.0f}% under")
    print("\n(reference: current 6-region head OccasionNoise 0.923/47%, Sandor 0.736/0%; SCORE-AI Sandor 0.605/0%, Morgoth 0.609/7%)")


if __name__ == "__main__":
    main()
