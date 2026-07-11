"""Definitive test of the manuscript claim: does conditioning norms on SEX change our ability to DETECT
abnormalities? Fit central rel_delta norms on clean-normal cohort recordings (sex-conditional vs pooled),
score every recording's abnormality z, and compare AUC for separating pathologic-slowing / abnormal from
normal. Equal AUC => sex is dispensable and we justify dropping it.

Run: PYTHONPATH=src python scripts/73_sex_detection_auc.py
"""
from __future__ import annotations
import subprocess, tempfile
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

CENTRAL = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
def A2T(age): return np.log10(np.asarray(age, float) + 1/12)


def auc_ci(y, s, n=1000):
    y, s = np.asarray(y), np.asarray(s)
    a = roc_auc_score(y, s); idx = np.arange(len(y)); rng = np.random.default_rng(0)
    bs = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if y[j].sum() in (0, len(j)): continue
        bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    cc = pd.read_parquet("data/derived/cohort_channel_stage.parquet")
    c = cc[cc.region.isin(CENTRAL)].groupby(["bdsp_id", "stage"]).agg(
        val=("rel_delta", "mean"), age=("age", "first"), sex=("sex", "first")).reset_index()
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "is_abnormal", "clean_normal", "has_focal_slow", "gen_class"]]
    c = c.merge(lu, on="bdsp_id", how="left")
    c["sex"] = c.sex.astype(str).str[0].str.upper()
    c = c[c.sex.isin(["M", "F"]) & c.age.between(0, 100) & c.val.between(0, 1)]
    c["t"] = A2T(c.age)
    c["is_train"] = (c.clean_normal == True).astype(int)
    c["pos_patho"] = (((c.gen_class == "pathologic") | (c.has_focal_slow == True))).astype(int)
    c["pos_genpatho"] = (c.gen_class == "pathologic").astype(int)   # generalized only — what central sees
    c["pos_focal"] = (c.has_focal_slow == True).astype(int)
    c["pos_abn"] = (c.is_abnormal == True).astype(int)

    with tempfile.TemporaryDirectory() as td:
        inp, outp = f"{td}/in.csv", f"{td}/z.csv"
        c[["stage", "sex", "t", "val", "is_train", "pos_patho", "pos_genpatho",
           "pos_focal", "pos_abn"]].to_csv(inp, index=False)
        r = subprocess.run(["Rscript", "scripts/sex_auc.R", inp, outp], capture_output=True, text=True)
        print(r.stdout); print(r.stderr[-800:] if r.returncode else "")
        z = pd.read_csv(outp)

    for tgt, name in [("pos_genpatho", "GENERALIZED pathologic slowing (central should see)"),
                      ("pos_focal", "FOCAL slowing (central should NOT see)"),
                      ("pos_patho", "any pathologic slowing (gen+focal)"),
                      ("pos_abn", "any abnormal")]:
        print(f"\n=== target: {name} — AUC of central rel_delta z (higher=slower) vs clean-normal ===")
        print(f"{'stage':<8}{'n+':>5}{'n-':>6}{'AUC sex-cond':>22}{'AUC pooled':>22}{'dAUC':>9}")
        for st in ["W", "N1", "N2", "N3", "REM", "ALL"]:
            m = z[(z[tgt] == 1) | (z.is_train == 1)]
            if st != "ALL": m = m[m.stage == st]
            y = m[tgt].values
            if y.sum() < 8: continue
            a1, l1, h1 = auc_ci(y, m.z_sex.values); a0, l0, h0 = auc_ci(y, m.z_nosex.values)
            print(f"{st:<8}{int(y.sum()):>5}{int((y==0).sum()):>6}"
                  f"{a1:>10.3f} [{l1:.3f},{h1:.3f}]{a0:>10.3f} [{l0:.3f},{h0:.3f}]{a1-a0:>+9.4f}")
    print("\nPer stage, |dAUC| ~ 0 => sex-conditioning does not improve detection; drop sex and justify.")


if __name__ == "__main__":
    main()
