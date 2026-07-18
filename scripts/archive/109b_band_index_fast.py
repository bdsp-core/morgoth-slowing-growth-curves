"""Fast band-index test on EXISTING data (no re-extraction): which band feature best recovers the report
band word (delta vs theta)? This tests MBW's principle ("pick the feature most correlated with the report
band word") and the excess-power reformulation. It does NOT test the 7-8 Hz edge (that needs re-extraction;
scripts/109). Uses the current theta=4-7 band powers in segment_features.

Run: PYTHONPATH=src python scripts/109b_band_index_fast.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

GRID = np.arange(0, 101, 2.0); BW = 5.0
rng = np.random.default_rng(0)


def kmean(age, val):
    W = np.exp(-0.5 * ((GRID[:, None] - age[None, :]) / BW) ** 2); sw = W.sum(1); ok = sw >= 30
    m = np.full(len(GRID), np.nan); m[ok] = (W[ok] @ val) / sw[ok]
    return m


def auc_ci(y, x, n=2000):
    m = np.isfinite(x); y, x = y[m], x[m]
    a = roc_auc_score(y, x); bs = []
    for _ in range(n):
        j = rng.integers(0, len(y), len(y))
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], x[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    seg = pd.read_parquet("data/derived/segment_features.parquet",
                          columns=["bdsp_id", "region", "segment", "log_delta", "log_theta", "rel_delta", "rel_theta"])
    stg = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    abn = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    st = pd.concat([stg, abn]).drop_duplicates(["bdsp_id", "segment"])
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "gen_band", "focal_band"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]].drop_duplicates("bdsp_id")

    d = seg[seg.region == "whole_head"].merge(st, on=["bdsp_id", "segment"]).merge(lu, on="bdsp_id").merge(cp, on="bdsp_id")
    d = d[d.stage.isin(["W", "N1"]) & (d.clean_pair == True)].copy()
    d["Pd"] = np.exp(d.log_delta); d["Pt"] = np.exp(d.log_theta)
    rec = d.groupby("bdsp_id").agg(age=("age", "first"), Pd=("Pd", "mean"), Pt=("Pt", "mean"),
                                   logd=("log_delta", "mean"), logt=("log_theta", "mean"),
                                   reld=("rel_delta", "mean"), relt=("rel_theta", "mean"),
                                   clean_normal=("clean_normal", "first"),
                                   gen_band=("gen_band", "first"), focal_band=("focal_band", "first")).reset_index()

    nrm = rec[rec.clean_normal == True]
    aP = nrm.age.to_numpy()
    muPd = kmean(aP, nrm.Pd.to_numpy()); muPt = kmean(aP, nrm.Pt.to_numpy())
    muld = kmean(aP, nrm.logd.to_numpy()); mult = kmean(aP, nrm.logt.to_numpy())
    ra = rec.age.to_numpy()
    rec["dPd"] = rec.Pd.to_numpy() - np.interp(ra, GRID, muPd)
    rec["dPt"] = rec.Pt.to_numpy() - np.interp(ra, GRID, muPt)
    rec["zd"] = rec.logd.to_numpy() - np.interp(ra, GRID, muld)
    rec["zt"] = rec.logt.to_numpy() - np.interp(ra, GRID, mult)

    rec["BI_zdiff"] = rec.zt - rec.zd
    rec["BI_excess"] = rec.dPt / (rec.dPd.abs() + rec.dPt.abs() + 1e-9)
    rec["BI_reldiff"] = rec.relt - rec.reld
    rec["band"] = rec.gen_band.where(rec.gen_band.isin(["delta", "theta"]),
                                     rec.focal_band.where(rec.focal_band.isin(["delta", "theta"])))
    t = rec.dropna(subset=["band"])
    y = (t.band == "theta").astype(int).to_numpy()

    out = ["# Band index — which feature recovers the report band word? (no 7–8 Hz fix yet)\n",
           f"{len(t)} report-band-labelled recordings (clean-paired, W/N1): theta {int(y.sum())}, "
           f"delta {int((1 - y).sum())}. Band power uses the current theta = 4–7 Hz.\n",
           "| band feature | AUROC vs report word [95% CI] |", "|---|---|"]
    for c, lab in [("BI_zdiff", "z_θ − z_δ (old, deprecated)"),
                   ("BI_reldiff", "rel_θ − rel_δ"),
                   ("BI_excess", "ΔP_θ / (|ΔP_δ|+|ΔP_θ|) — excess-power share"),
                   ("dPt", "θ excess power ΔP_θ alone"),
                   ("zt", "z_θ alone"),
                   ("zd", "z_δ alone (expect < 0.5: delta→delta-word)")]:
        a, lo, hi = auc_ci(y, t[c].to_numpy())
        out.append(f"| {lab} | **{a:.3f}** [{lo:.3f}, {hi:.3f}] |")
    out.append("\nExpert–expert ceiling for band (MoE, exact δ-vs-θ match): 0.576 focal / 0.434 generalized "
               "(`results/moe_band_vs_ours.md`). The 7–8 Hz edge fix is tested separately (scripts/109).")
    Path("results/band_index_fast.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
