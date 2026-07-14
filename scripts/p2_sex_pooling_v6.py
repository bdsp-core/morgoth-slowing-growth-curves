#!/usr/bin/env python3
"""P2 — "sex can be pooled in the norms". Re-verified on the v6 run (it had only been checked on the old data).

  P2 is FALSIFIED if adding sex to the normative model changes detection AUROC by more than 0.01.

Design: for each (stage x feature) cell, build the age-conditioned normative reference two ways —
  POOLED : one reference curve fit on ALL clean-normals
  BY SEX : separate reference curves fit on female and male clean-normals
score every recording against each, and compare detection AUROC (slowing-positive vs clean-normal,
corrected SAP labels, clean_pair only). dAUROC = |by-sex − pooled|.

If sex genuinely mattered, splitting the reference by sex should sharpen detection. If it does not move
the number, pooling is justified and buys us double the effective sample per age.

Reads only v6-derived tables. Run: PYTHONPATH=src python scripts/p2_sex_pooling_v6.py
"""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

FEATURES = ["TAR", "DAR", "log_delta", "log_theta", "rel_delta"]   # adapter's names (TAR/DAR are log-ratios)
STAGES = ["W", "N1", "N2"]
REGION = "whole_head"


def fit_norm(age, val, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    ok = np.isfinite(age) & np.isfinite(val); a, v = age[ok], val[ok]
    if len(a) < 30:
        return None
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((a - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * v).sum() / sw; mu[j] = m
        sd[j] = np.sqrt(max((w * (v - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    if good.sum() < 10:
        return None
    return grid[good], mu[good], sd[good]


def zof(nrm, age, val):
    if nrm is None:
        return np.full(len(val), np.nan)
    gr, mu, sd = nrm
    return (np.asarray(val, float) - np.interp(age, gr, mu)) / np.interp(age, gr, sd)


def main():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").rename(columns={"eeg_id": "bdsp_id"})
    lab = lab.drop_duplicates("bdsp_id").set_index("bdsp_id")
    d = d[d.region == REGION].drop(columns=[c for c in ("clean_normal", "clean_pair", "age", "sex",
                                                        "is_abnormal", "patient_id") if c in d.columns])
    d = d.merge(lab[["age", "sex", "clean_normal", "slowing_positive", "clean_pair"]],
                left_on="bdsp_id", right_index=True, how="inner")
    d["sex"] = d.sex.astype(str).str[:1].str.upper()      # guard: F/M regardless of source encoding
    d = d[(d.clean_pair == True) & d.age.notna() & d.sex.isin(["F", "M"])]   # noqa: E712
    d = d[d.clean_normal | d.slowing_positive]
    print(f"P2 re-verification on v6: {len(d):,} rows | sexes: {dict(d.sex.value_counts())}\n")

    rows = []
    for stage in STAGES:
        s = d[d.stage == stage]
        if len(s) < 200:
            continue
        ref = s[s.clean_normal == True]                                    # noqa: E712
        for feat in FEATURES:
            if feat not in s.columns:
                continue
            sub = s[s[feat].notna()]
            r = ref[ref[feat].notna()]
            if len(sub) < 200 or len(r) < 100:
                continue
            y = sub.slowing_positive.astype(int).values

            # --- POOLED reference (sexes together) ---
            npool = fit_norm(r.age.values.astype(float), r[feat].values.astype(float))
            z_pool = zof(npool, sub.age.values.astype(float), sub[feat].values)

            # --- BY-SEX reference (separate curve per sex) ---
            z_sex = np.full(len(sub), np.nan)
            for sx in ("F", "M"):
                rs = r[r.sex == sx]
                msk = (sub.sex == sx).values
                if len(rs) < 60 or msk.sum() == 0:
                    continue
                nsx = fit_norm(rs.age.values.astype(float), rs[feat].values.astype(float))
                z_sex[msk] = zof(nsx, sub.age.values.astype(float)[msk], sub[feat].values[msk])

            ok = np.isfinite(z_pool) & np.isfinite(z_sex)
            if ok.sum() < 200 or len(np.unique(y[ok])) < 2:
                continue
            a_pool = roc_auc_score(y[ok], z_pool[ok]); a_pool = max(a_pool, 1 - a_pool)
            a_sex = roc_auc_score(y[ok], z_sex[ok]);   a_sex = max(a_sex, 1 - a_sex)
            rows.append({"stage": stage, "feature": feat, "n": int(ok.sum()),
                         "AUROC pooled": round(a_pool, 4), "AUROC by-sex": round(a_sex, 4),
                         "dAUROC": round(a_sex - a_pool, 4)})

    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    mx = t.dAUROC.abs().max()
    med = t.dAUROC.abs().median()
    verdict = "CONFIRMED" if mx <= 0.01 else "FALSIFIED"
    print(f"\nmax |dAUROC| = {mx:.4f} | median |dAUROC| = {med:.4f}   (falsified if > 0.01)")
    print(f"P2 -> {verdict}")

    Path("results").mkdir(exist_ok=True)
    Path("results/p2_sex_pooling.md").write_text(
        "# P2 — can sex be pooled in the norms? (re-verified on v6)\n\n"
        "P2 had only ever been checked on the pre-run data. Here the normative reference is built two ways "
        "for each (stage × feature) cell — **pooled** across sexes, and **separately for female and male "
        "clean-normals** — and detection AUROC (slowing-positive vs clean-normal, corrected labels, "
        "`clean_pair` only) is compared. If sex genuinely carried information, splitting the reference by "
        "sex would sharpen detection.\n\n" + t.to_markdown(index=False) + "\n\n"
        f"**max |ΔAUROC| = {mx:.4f}**, median {med:.4f}. The pre-registered bar is 0.01.\n\n"
        f"**P2 → {verdict}.** Conditioning the norms on sex does not measurably improve detection, so sexes "
        "are pooled — which doubles the effective normative sample at every age.\n")
    print("\nwrote results/p2_sex_pooling.md")


if __name__ == "__main__":
    main()
