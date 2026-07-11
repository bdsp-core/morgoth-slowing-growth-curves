"""DEFINITIVE sex-ablation on the REAL detector. scripts/06 computes a sex-CONDITIONAL normal-referenced
z (normal_z loops over sex) and gets AUC ~0.80-0.82 (TAR) for normal-vs-general slowing. Here we recompute
the identical z but with a sex-POOLED normal reference (both sexes in one kernel), and compare AUC on the
same recording_features / labels. If AUC is unchanged, sex-conditioning adds nothing to detection and we
drop sex in the manuscript.

Run: PYTHONPATH=src python scripts/74_sex_ablation_discrim.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

OUT = Path("data/derived")
FEATURES = ["TAR", "DAR", "log_delta", "rel_delta", "low_freq_rel"]
REGIONS = ["whole_head", "L_parasagittal", "R_parasagittal", "L_temporal", "R_temporal"]
PAIRS = {"normal_vs_general": ("normal", "general_slow"), "normal_vs_focal": ("normal", "focal_slow")}


def normal_z(values, ages, sexes, normal_df, feat, use_sex, bw=5.0):
    """Gaussian age-kernel z vs normal mean/sd. use_sex=True -> reference is sex-matched normals
    (the scripts/06 detector); use_sex=False -> reference is ALL normals pooled (sex ablated)."""
    z = np.full(len(values), np.nan)
    groups = ["M", "F"] if use_sex else ["_ALL_"]
    for g in groups:
        nrm = normal_df if g == "_ALL_" else normal_df[normal_df.sex == g]
        na, nv = nrm.age.values, nrm[feat].values
        ok = np.isfinite(na) & np.isfinite(nv); na, nv = na[ok], nv[ok]
        idx = np.where((np.isfinite(values) & np.isfinite(ages)) if g == "_ALL_"
                       else (sexes == g) & np.isfinite(values) & np.isfinite(ages))[0]
        for i in idx:
            w = np.exp(-0.5 * ((na - ages[i]) / bw) ** 2); sw = w.sum()
            if sw < 1: continue
            mu = np.sum(w * nv) / sw
            sd = np.sqrt(max(np.sum(w * (nv - mu) ** 2) / sw, 1e-9))
            z[i] = (values[i] - mu) / sd
    return z


def boot_dauc(y, s1, s0, n=1000):
    y = np.asarray(y); m = np.isfinite(s1) & np.isfinite(s0)
    y, s1, s0 = y[m], np.asarray(s1)[m], np.asarray(s0)[m]
    a1, a0 = roc_auc_score(y, s1), roc_auc_score(y, s0)
    rng = np.random.default_rng(0); idx = np.arange(len(y)); d = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if y[j].sum() in (0, len(j)): continue
        d.append(roc_auc_score(y[j], s1[j]) - roc_auc_score(y[j], s0[j]))
    return a1, a0, np.percentile(d, 2.5), np.percentile(d, 97.5)


def main():
    feat_df = pd.read_parquet(OUT / "recording_features.parquet")
    feat_df = feat_df[feat_df.age.between(0, 120) & feat_df.sex.isin(["M", "F"])]
    print(f"{'feature':<12}{'region':<16}{'pair':<20}{'AUC sex-cond':>13}{'AUC pooled':>12}"
          f"{'dAUC':>9}{'95% CI':>20}")
    rows = []
    for region in REGIONS:
        sub = feat_df[feat_df.region == region].copy()
        normal = sub[sub.label == "normal"]
        for feat in FEATURES:
            z1 = normal_z(sub[feat].values, sub.age.values, sub.sex.values.astype(str), normal, feat, True)
            z0 = normal_z(sub[feat].values, sub.age.values, sub.sex.values.astype(str), normal, feat, False)
            lab = sub.label.values
            for pair, (a, b) in PAIRS.items():
                mask = np.isin(lab, [a, b]); y = (lab[mask] == b).astype(int)
                if y.sum() < 10: continue
                A1, A0, lo, hi = boot_dauc(y, z1[mask], z0[mask])
                rows.append((feat, region, pair, A1, A0, A1 - A0, lo, hi))
    rows.sort(key=lambda r: -max(r[3], r[4]))   # show strongest detectors first
    for feat, region, pair, A1, A0, d, lo, hi in rows:
        print(f"{feat:<12}{region:<16}{pair:<20}{A1:>13.3f}{A0:>12.3f}{d:>+9.4f}   [{lo:+.4f},{hi:+.4f}]")
    dd = np.array([r[5] for r in rows])
    print(f"\nAcross {len(rows)} detector settings: mean dAUC={dd.mean():+.4f}, "
          f"max|dAUC|={np.abs(dd).max():.4f}. dAUC>0 favors sex-conditioning.")
    print("If max|dAUC| is small and CIs straddle 0 -> sex adds nothing to detection; drop it.")


if __name__ == "__main__":
    main()
