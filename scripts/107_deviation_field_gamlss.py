"""Deviation field — SAP §6.1 + §6.3, done properly.

REPLACES the Gaussian-kernel mean/SD path in scripts/107_deviation_field.py, which computed a
normal-theory z = (x - mean)/sd. That is wrong for these features: EEG slowing measures are strongly
right-skewed and the skew VARIES with age (far more skewed in young children), so a symmetric model
(a) biases the normative median high in kids and (b) makes every emitted centile (norm.cdf(z)) wrong.

Here: GAMLSS/BCT (Box-Cox-t) per (stage x region x feature), with mu/sigma/nu(skew)/tau smooth in age,
fit on `clean_normal` ONLY (SAP §3.4), with **k-fold cross-fitting** (SAP §6.3) so a normal recording's
own z uses OUT-OF-FOLD parameters (no self-normalisation optimism). Folds are split by **patient_id**
(SAP §3.3) so a patient's several EEGs cannot straddle train/test.

Reads only new-run tables: data/derived/channel_stage_features.parquet + labels_unified.parquet.
Writes data/derived/deviation_field.parquet  (bdsp_id, patient_id, stage, region, feature, z)
Run: PYTHONPATH=src python scripts/107_deviation_field_gamlss.py [--features a,b] [--regions x,y] [--k 5]
"""
from __future__ import annotations
import argparse, os, subprocess, tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd

RSCRIPT = os.environ.get("RSCRIPT", os.path.expanduser("~/micromamba/envs/r/bin/Rscript"))
RZ = "scripts/gamlss_zscore.R"
OUT = Path("data/derived/deviation_field.parquet")
# SAP's discriminating slowing features; regions = the 6 clinical units (channels handled by lateralisation)
FEATURES = ["rel_delta", "TAR", "DAR", "log_delta"]
REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal", "midline"]


def t_of_age(age):
    return np.log10(np.asarray(age, dtype=float) + 1.0 / 12.0)


def run_r(fit_df, score_df):
    """Fit BCT on fit_df (stage,t,val) and return BCT z for score_df (id,stage,t,val)."""
    with tempfile.TemporaryDirectory() as td:
        f, s, o = f"{td}/fit.csv", f"{td}/score.csv", f"{td}/out.csv"
        fit_df[["stage", "t", "val"]].to_csv(f, index=False)
        score_df[["id", "stage", "t", "val"]].to_csv(s, index=False)
        r = subprocess.run([RSCRIPT, RZ, f, s, o], capture_output=True, text=True)
        if not os.path.exists(o):
            return pd.DataFrame(columns=["id", "stage", "z"])
        return pd.read_csv(o)


def one_cell(args):
    """One (region, feature): cross-fitted z for normals + full-fit z for everyone else."""
    region, feat, d, k = args
    d = d[np.isfinite(d.val) & (d.val > 0)].copy()
    if d.empty:
        return pd.DataFrame()
    norm = d[d.clean_normal == True]
    if len(norm) < 200:
        return pd.DataFrame()

    out = []
    # --- normals: k-fold cross-fitting, folds by PATIENT (SAP §3.3/§6.3) ---
    pats = np.asarray(norm.patient_id.dropna().unique(), dtype=object)
    rng = np.random.default_rng(0); rng.shuffle(pats)
    folds = {p: i % k for i, p in enumerate(pats)}
    norm = norm.assign(_f=norm.patient_id.map(folds))
    for i in range(k):
        tr = norm[norm._f != i]; te = norm[norm._f == i]
        if len(tr) < 100 or te.empty:
            continue
        out.append(run_r(tr, te))
    # --- everyone else (abnormals etc.): scored against the FULL normal reference ---
    rest = d[d.clean_normal != True]
    if not rest.empty:
        out.append(run_r(norm, rest))

    if not out:
        return pd.DataFrame()
    z = pd.concat(out, ignore_index=True)
    z["region"] = region; z["feature"] = feat
    return z.rename(columns={"id": "bdsp_id"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=",".join(FEATURES))
    ap.add_argument("--regions", default=",".join(REGIONS))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    feats = [f for f in a.features.split(",") if f]
    regs = [r for r in a.regions.split(",") if r]

    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[["bdsp_id", "patient_id", "clean_normal"]]
    d = d.drop(columns=[c for c in ("patient_id", "clean_normal") if c in d.columns]).merge(lu, on="bdsp_id", how="left")
    d = d[d.region.isin(regs)]
    d["t"] = t_of_age(d.age)
    d = d[np.isfinite(d.t)]

    jobs = []
    for region in regs:
        dr = d[d.region == region]
        if dr.empty: continue
        for feat in feats:
            if feat not in dr.columns: continue
            sub = dr[["bdsp_id", "patient_id", "stage", "t", "clean_normal", feat]].rename(columns={feat: "val"})
            sub = sub.assign(id=sub.bdsp_id)
            jobs.append((region, feat, sub, a.k))

    print(f"deviation field: {len(jobs)} (region x feature) cells, k={a.k}, jobs={a.jobs}", flush=True)
    res = []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for i, r in enumerate(ex.map(one_cell, jobs), 1):
            if not r.empty: res.append(r)
            print(f"  {i}/{len(jobs)} cells done", flush=True)

    if not res:
        print("NO CELLS FIT — check R/gamlss"); return
    z = pd.concat(res, ignore_index=True)
    z = z.merge(lu[["bdsp_id", "patient_id"]], on="bdsp_id", how="left")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    z.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {z.shape}  ({z.bdsp_id.nunique():,} recordings, "
          f"{z.feature.nunique()} features x {z.region.nunique()} regions x {z.stage.nunique()} stages)")
    print(f"  z finite: {100*np.isfinite(z.z).mean():.1f}%  | median |z| normals vs rest:")
    m = z.merge(lu[["bdsp_id", "clean_normal"]], on="bdsp_id", how="left")
    print(m.groupby("clean_normal").z.median().round(3).to_dict())


if __name__ == "__main__":
    main()
