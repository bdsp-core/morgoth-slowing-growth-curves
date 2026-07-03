"""Phase E: which features discriminate normal / focal / generalized — AGE & SEX ADJUSTED.

For each recording we compute a z vs the normal age x sex growth curve (empirical percentile -> z),
then AUC for each group pair on that adjusted z. Raw (unadjusted) AUC is also reported to show how
much of any signal is just the age confound.

Outputs: results/discrimination.md, data/derived/adjusted_z.parquet, figures/discrimination_auc.png
Run: python scripts/06_discrimination.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

from morgoth_slowing.norms import growth

OUT = Path("data/derived"); RES = Path("results"); FIG = Path("figures")
RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
FEATURES = ["rel_delta", "rel_theta", "log_delta", "log_theta", "DAR", "TAR", "DTR", "low_freq_rel"]
REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
PCTL = growth.DEFAULT_PCTL


def normal_z(values, ages, sexes, normal_df, feat, bw=5.0):
    """Parametric age/sex-local z: (value - weighted_normal_mean) / weighted_normal_sd.

    Weighted by a Gaussian age kernel around each subject. Unbounded (unlike an empirical
    percentile->z, which saturates at ~3.7 with ~5k controls) so it differentiates severe cases.
    log-power features are ~Gaussian, so this is well behaved (feature_spec §4)."""
    z = np.full(len(values), np.nan)
    for sex in ["M", "F"]:
        nrm = normal_df[normal_df.sex == sex]
        na, nv = nrm.age.values, nrm[feat].values
        ok = np.isfinite(na) & np.isfinite(nv); na, nv = na[ok], nv[ok]
        idx = np.where((sexes == sex) & np.isfinite(values) & np.isfinite(ages))[0]
        for i in idx:
            w = np.exp(-0.5 * ((na - ages[i]) / bw) ** 2)
            sw = w.sum()
            if sw < 1:
                continue
            mu = np.sum(w * nv) / sw
            sd = np.sqrt(max(np.sum(w * (nv - mu) ** 2) / sw, 1e-9))
            z[i] = (values[i] - mu) / sd
    return z


def auc(scores, y):
    m = np.isfinite(scores)
    if len(np.unique(y[m])) < 2:
        return np.nan
    return roc_auc_score(y[m], scores[m])


def main():
    feat_df = pd.read_parquet(OUT / "recording_features.parquet")
    feat_df = feat_df[feat_df.age.between(0, 120) & feat_df.sex.isin(["M", "F"])]
    rows, zrows = [], []
    for region in REGIONS:
        sub = feat_df[feat_df.region == region].copy()
        normal = sub[sub.label == "normal"]
        for feat in FEATURES:
            z = normal_z(sub[feat].values, sub.age.values, sub.sex.values.astype(str), normal, feat)
            sub_z = sub[["bdsp_id", "label"]].copy(); sub_z["z"] = z
            sub_z["feature"] = feat; sub_z["region"] = region; zrows.append(sub_z)
            lab = sub.label.values
            for pair, (a, b) in {"normal_vs_focal": ("normal", "focal_slow"),
                                 "normal_vs_general": ("normal", "general_slow"),
                                 "focal_vs_general": ("focal_slow", "general_slow")}.items():
                mask = np.isin(lab, [a, b])
                y = (lab[mask] == b).astype(int)
                rows.append({"feature": feat, "region": region, "pair": pair,
                             "auc_adj": auc(z[mask], y), "auc_raw": auc(sub[feat].values[mask], y),
                             "n": int(mask.sum())})
        print("done", region)

    res = pd.DataFrame(rows)
    pd.concat(zrows, ignore_index=True).to_parquet(OUT / "adjusted_z.parquet")

    # add asymmetry features (|asym| vs normal, for focal especially)
    asym = pd.read_parquet(OUT / "recording_asymmetry.parquet")
    asym = asym[asym.age.between(0, 120) & asym.sex.isin(["M", "F"])]
    acols = [c for c in asym.columns if c.startswith("asym_")]
    arows = []
    for c in acols:
        normal = asym[asym.label == "normal"]
        z = normal_z(asym[c].abs().values, asym.age.values, asym.sex.values.astype(str),
                     normal.assign(**{c: normal[c].abs()}), c)
        lab = asym.label.values
        for pair, (a, b) in {"normal_vs_focal": ("normal", "focal_slow"),
                             "normal_vs_general": ("normal", "general_slow")}.items():
            mask = np.isin(lab, [a, b]); y = (lab[mask] == b).astype(int)
            arows.append({"feature": "|"+c+"|", "region": "asym", "pair": pair,
                          "auc_adj": auc(z[mask], y), "auc_raw": np.nan, "n": int(mask.sum())})
    res = pd.concat([res, pd.DataFrame(arows)], ignore_index=True)

    res["discrim"] = (res.auc_adj - 0.5).abs()
    res = res.sort_values("discrim", ascending=False)
    res.to_parquet(OUT / "discrimination.parquet")

    # write markdown: top features per pair
    with open(RES / "discrimination.md", "w") as fh:
        fh.write("# Discrimination results (age & sex adjusted)\n\n")
        fh.write("AUC of each feature's normal-referenced z for separating groups. 0.5 = no signal; "
                 ">0.5 means the group has higher z (more slowing/asymmetry). `auc_raw` = unadjusted "
                 "(age-confounded) for comparison.\n\n")
        for pair in ["normal_vs_focal", "normal_vs_general", "focal_vs_general"]:
            top = res[res.pair == pair].head(12)
            fh.write(f"## {pair}\n\n| feature | region | AUC (adj) | AUC (raw) | n |\n|---|---|---|---|---|\n")
            for _, r in top.iterrows():
                fh.write(f"| {r.feature} | {r.region} | {r.auc_adj:.3f} | "
                         f"{'' if pd.isna(r.auc_raw) else format(r.auc_raw,'.3f')} | {r.n} |\n")
            fh.write("\n")
    # bar chart of top-15 overall
    top = res.head(15)[::-1]
    plt.figure(figsize=(9, 6))
    plt.barh([f"{r.feature}·{r.region}·{r.pair}" for _, r in top.iterrows()], top.auc_adj, color="#2c7fb8")
    plt.axvline(0.5, color="k", lw=1); plt.xlabel("AUC (age/sex-adjusted)"); plt.tight_layout()
    plt.savefig(FIG / "discrimination_auc.png", dpi=110); plt.close()
    print("wrote results/discrimination.md and figures/discrimination_auc.png")
    print(res.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
