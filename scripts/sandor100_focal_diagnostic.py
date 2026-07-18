"""Diagnose why our FOCAL detector puts 0% of experts under its ROC on Sandor_100, despite AUROC 0.736.
Tests the leading hypotheses: (A) confound with generalized amount; (B) label overlap; (C) which feature
family carries focal (peak-amount vs focality vs asymmetry vs per-channel homologous asymmetry). Prints
AUROC, % experts under, and the high-specificity gap for several focal-score variants.

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/sandor100_focal_diagnostic.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

m55 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py"))
importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py").loader.exec_module(m55)
m54 = m55.m54; m53 = m54.m49; m46 = m54.m49.m46
m53b = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m53b", "scripts/53_single_model_features.py"))
importlib.util.spec_from_file_location("m53b", "scripts/53_single_model_features.py").loader.exec_module(m53b)
m53b.SEG_CAP = 10**9

SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100")
MR = SB_DIR / "Morgoth_results"; SM = Path("data/derived/segment_master")
AMT0, FOC0 = m55.AMT0, m55.FOC0
AGG = ("mean", "p90", "max", "prev")


def cols(prefixes):
    return [f"{c}_{s}" for c in FOC0 for s in AGG if any(c.startswith(p) for p in prefixes)] + ["age"]


def sb_features():
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    rows = []
    for out in sorted(SM.glob("eeg_id=SB_*")):
        eid = out.name.split("=")[1]; n = int(eid.split("_")[1])
        sf = m53b.seg_feats(eid, age.get(f"ID{n:03d}", np.nan))
        if sf is None or sf.empty:
            continue
        sf["eeg_id"] = eid; sf["dataset"] = "sb"; sf["split"] = "test"; sf["y_focal"] = 0; sf["y_gen"] = 0
        R = m55.aggregate(sf).reset_index(); R["key"] = f"ID{n:03d}"; rows.append(R)   # keep eeg_id as a column
    return pd.concat(rows, ignore_index=True)


def expert_under(y, s, wide):
    pts = m46.expert_points(wide)
    cur = m54.panel_curve(None, y, s, pts, "#000", "x")
    # high-specificity gap: experts' mean spec, our sensitivity there
    espec = np.mean([1 - p["fpr"] for p in pts.values()]); esens = np.mean([p["tpr"] for p in pts.values()])
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y, s); our_sens = float(np.interp(1 - espec, fpr, tpr))
    return cur["ur"], espec, esens, our_sens


def main():
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    Rtr = m55.aggregate(S[S.dataset == "report"]); Rtr = Rtr[Rtr.split == "train"]
    sb = sb_features()
    foc = pd.read_excel(MR / "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); foc["key"] = foc.file_name.astype(str).str.strip()
    gen = pd.read_excel(MR / "GenSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); gen["key"] = gen.file_name.astype(str).str.strip()
    m = sb.merge(foc[["key", "majority"] + [c for c in foc.columns if c.startswith("expert_")]], on="key") \
          .merge(gen[["key", "majority"]].rename(columns={"majority": "gen_majority"}), on="key")
    yf = m.majority.astype(int).values; yg = m.gen_majority.astype(int).values
    ecols = [c for c in foc.columns if c.startswith("expert_")]
    wide = m.set_index("key")[ecols].apply(pd.to_numeric, errors="coerce")
    print(f"n={len(m)}  focal+={yf.sum()}  gen+={yg.sum()}  both={int(((yf==1)&(yg==1)).sum())}  focal-only={int(((yf==1)&(yg==0)).sum())}")

    variants = {
        "current focal head (peak+foc+asym)": cols(("peak_", "foc_", "asym_")),
        "focality only (foc_)": cols(("foc_",)),
        "asymmetry only (asym_)": cols(("asym_",)),
        "foc + asym (drop peak amount)": cols(("foc_", "asym_")),
        "peak-amount only (peak_)": cols(("peak_",)),
        "whole-head AMOUNT (amt_)": [f"{c}_{s}" for c in AMT0 for s in AGG] + ["age"],
    }
    print(f"\n{'variant':40s} {'AUROC_foc':>9} {'%under':>7} {'confound_AUROC_gen':>18}")
    for name, cs in variants.items():
        cs = [c for c in cs if c in Rtr.columns and c in m.columns]
        med = Rtr[cs].median()
        h = m54.Head().fit(Rtr[cs].fillna(med).values, Rtr.y_focal.astype(int).values)
        s = h.score(m[cs].fillna(med).values)
        au = roc_auc_score(yf, s); auc_g = roc_auc_score(yg, s)     # confound: does the focal score track GEN?
        ur, espec, esens, our_sens = expert_under(yf, s, wide)
        print(f"{name:40s} {au:9.3f} {ur:6.0f}% {auc_g:18.3f}   (experts spec={espec:.2f} sens={esens:.2f}; our sens@that spec={our_sens:.2f})")

    # per-channel homologous asymmetry (finer than 6-region) — a direct focal sign, computed from segment_master
    print("\n[per-channel homologous asymmetry as a standalone focal score]")
    PAIRS = [("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"), ("T5-O1", "T6-O2"),
             ("Fp1-F3", "Fp2-F4"), ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("P3-O1", "P4-O2")]
    def chan_asym(eid):
        f = f"{SM}/eeg_id={eid}/part.parquet"
        try:
            d = pd.read_parquet(f, columns=["segment", "channel", "log_delta", "log_TAR", "artifact_flag"])
        except Exception:
            return np.nan
        d = d[~d.artifact_flag.astype(bool)]
        w = d.pivot_table(index="segment", columns="channel", values="log_delta", aggfunc="mean")
        best = 0.0
        for L, Rr in PAIRS:
            if L in w and Rr in w:
                best = max(best, float(np.nanquantile(np.abs(w[L] - w[Rr]), .9)))
        return best
    def chan_asym2(eid):
        """within-recording focal CONTRAST: how much the most-asymmetric pair stands out from the rest
        (shift-invariant -> robust to external montage/population)."""
        f = f"{SM}/eeg_id={eid}/part.parquet"
        try:
            d = pd.read_parquet(f, columns=["segment", "channel", "log_delta", "artifact_flag"])
        except Exception:
            return np.nan
        d = d[~d.artifact_flag.astype(bool)]
        w = d.pivot_table(index="segment", columns="channel", values="log_delta", aggfunc="mean")
        vals = [float(np.nanquantile(np.abs(w[L] - w[Rr]), .9)) for L, Rr in PAIRS if L in w and Rr in w]
        if len(vals) < 3:
            return np.nan
        vals = np.array(vals)
        return float(vals.max() - np.median(vals))                 # peak-pair minus typical-pair asymmetry
    m["ca"] = [chan_asym(e) for e in m.eeg_id]
    m["ca2"] = [chan_asym2(e) for e in m.eeg_id]
    # current head score for fusion
    cs = [c for c in cols(("peak_", "foc_", "asym_")) if c in Rtr.columns and c in m.columns]
    med = Rtr[cs].median(); m["hscore"] = m54.Head().fit(Rtr[cs].fillna(med).values, Rtr.y_focal.astype(int).values).score(m[cs].fillna(med).values)
    rk = lambda x: pd.Series(x).rank(pct=True).values
    tests = {"per-channel |L-R| delta p90 (raw)": m.ca.values,
             "within-recording focal CONTRAST (peak-median pair)": m.ca2.values,
             "fusion: head + Morgoth M_pred (rank avg)": rk(m.hscore.values) + rk(m.merge(foc[['key','M_pred']],on='key').M_pred.values),
             "fusion: contrast + head + Morgoth (rank avg)": rk(np.nan_to_num(m.ca2.values)) + rk(m.hscore.values) + rk(m.merge(foc[['key','M_pred']],on='key').M_pred.values)}
    for name, s in tests.items():
        ok = np.isfinite(s)
        au = roc_auc_score(yf[ok], s[ok]); ur, _, _, os_ = expert_under(yf[ok], s[ok], wide.loc[m.key.values[ok]])
        print(f"{name:52s} AUROC {au:.3f}  {ur:.0f}% under  our sens@expert spec={os_:.2f}")


if __name__ == "__main__":
    main()
