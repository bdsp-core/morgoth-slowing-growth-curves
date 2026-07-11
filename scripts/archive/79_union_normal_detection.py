"""Does using the UNION of both cohorts as 'normal' (a broader, conservative standard) hurt our ability to
detect abnormal? Build the normal reference three ways and compare abnormal-vs-normal AUROC:
  (A) UNION      = routine clean-normal + overnight report-normal
  (B) ROUTINE    = routine clean-normal only
  (C) OVERNIGHT  = overnight report-normal only
For each, compute an age-adjusted deviation z of whole-head rel_delta (pipeline-consistent) from the
reference, then AUROC separating cohort PATHOLOGIC generalized slowing (positives) from HELD-OUT routine
normals (negatives). Held-out split keeps the negatives out of every reference so the comparison is fair.
If UNION AUROC ~ ROUTINE AUROC, the conservative broad-normal costs little detection power -> justified.

Run: PYTHONPATH=src python scripts/79_union_normal_detection.py
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

FEATURE = "rel_delta"; REGION = "whole_head"
STAGES = ["W", "N1", "N2", "N3", "REM"]
rng = np.random.default_rng(0)


def normal_z(vals, ages, ref_vals, ref_ages, bw=5.0):
    """age-local z vs a normal reference (Gaussian age kernel mean/sd), unbounded (scripts/06 style)."""
    z = np.full(len(vals), np.nan)
    ra, rv = np.asarray(ref_ages), np.asarray(ref_vals)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    for i in range(len(vals)):
        if not (np.isfinite(vals[i]) and np.isfinite(ages[i])): continue
        w = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = w.sum()
        if sw < 5: continue
        mu = (w * rv).sum() / sw; sd = np.sqrt(max((w * (rv - mu) ** 2).sum() / sw, 1e-9))
        z[i] = (vals[i] - mu) / sd
    return z


def auc_ci(y, s, n=500):
    y, s = np.asarray(y), np.asarray(s); m = np.isfinite(s)
    y, s = y[m], s[m]; a = roc_auc_score(y, s); idx = np.arange(len(y)); bs = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    df = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[["bdsp_id", "gen_class", "is_abnormal"]]
    d = df[df.region == REGION].groupby(["bdsp_id", "stage"]).agg(
        val=(FEATURE, "mean"), age=("age", "first"), src=("src", "first"),
        clean=("clean_normal", "first")).reset_index().merge(lu, on="bdsp_id", how="left")
    d = d[d.age.between(0, 95) & d.val.between(0, 1)]

    # split routine normals -> reference-train (70%) vs test-negatives (30%)
    rn_ids = d[(d.src == "cohort") & (d.clean == True)].bdsp_id.unique()
    test_ids = set(rng.choice(rn_ids, int(0.3 * len(rn_ids)), replace=False))
    train_ids = set(rn_ids) - test_ids

    print(f"{'stage':<6}{'n+':>5}{'n-':>6}{'AUROC union':>22}{'AUROC routine':>22}{'AUROC overnight':>22}")
    for st in STAGES:
        s = d[d.stage == st]
        pos = s[(s.src == "cohort") & (s.gen_class == "pathologic")]                 # abnormal to detect
        neg = s[s.bdsp_id.isin(test_ids)]                                            # held-out routine normals
        refR = s[s.bdsp_id.isin(train_ids)]                                          # routine normal reference
        refO = s[(s.src == "expansion") & (s.clean == True)]                         # overnight normal reference
        refU = pd.concat([refR, refO])                                               # union reference
        if len(pos) < 8 or len(neg) < 20:
            print(f"{st:<6}{len(pos):>5}{len(neg):>6}   (too few positives/negatives)"); continue
        test = pd.concat([pos.assign(y=1), neg.assign(y=0)])
        out = []
        for ref in (refU, refR, refO):
            z = normal_z(test.val.values, test.age.values, ref.val.values, ref.age.values)
            out.append(auc_ci(test.y.values, z))
        print(f"{st:<6}{len(pos):>5}{len(neg):>6}"
              + "".join(f"{a:>10.3f} [{lo:.2f},{hi:.2f}]" for a, lo, hi in out))
    print("\nIf UNION AUROC is within ~CI of ROUTINE AUROC, the broad/conservative normal barely costs "
          "detection -> justified. Wake (W/N1) is where the union widens the band most.")


if __name__ == "__main__":
    main()
