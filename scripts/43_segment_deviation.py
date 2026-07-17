#!/usr/bin/env python3
"""SECTION 2 — materialize the PER-SEGMENT deviation field.

Every segment gets, for every feature × region, a deviation z scored against ITS OWN (sleep-stage, age)
normal curve — the same norms the descriptor grid uses (data/derived/grid_norm.json, built by scripts/115:
BCT for positive rel_* features, robust normal-in-log-age for the real-line log_* features). So "abnormal"
always means abnormal FOR THIS AGE AND THIS SLEEP STAGE.

Sign convention: RAW signed z. Positive = the feature is ABOVE its stage/age-matched normal median (in
robust-SD units). No abnormality re-orientation here (rel_alpha is NOT flipped) — downstream code orients as
needed; UP-features abnormal when z>0, rel_alpha abnormal when z<0.

Output: data/derived/segment_deviation/eeg_id=<id>/part.parquet
  columns: segment, t_start_s, stage, age, and z__<region>__<feature> for every region × feature.
Grain: one row per (eeg_id, segment). Partitioned by eeg_id, so it joins segment_gate / segment_summary
1:1 on (eeg_id, segment).

Run: PYTHONPATH=src python3 scripts/43_segment_deviation.py [--limit N]
"""
from __future__ import annotations
import argparse, json, os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import t as _tdist, norm as _norm

SM = "data/derived/segment_master"
OUT = Path("data/derived/segment_deviation")
NORM_JSON = "data/derived/grid_norm.json"
A0 = 1.0 / 12.0

UP = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR"]
DOWN = ["rel_alpha"]
FEATS = UP + DOWN
ANT = ["Fp1-F7", "F7-T3", "Fp1-F3", "F3-C3", "Fp2-F8", "F8-T4", "Fp2-F4", "F4-C4", "Fz-Cz"]
POS = ["T3-T5", "T5-O1", "C3-P3", "P3-O1", "T4-T6", "T6-O2", "C4-P4", "P4-O2", "Cz-Pz"]
LOBES = {"L_temporal": ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"],
         "R_temporal": ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],
         "L_parasagittal": ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"],
         "R_parasagittal": ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"]}
REGIONS = {"whole_head": None, "anterior": ANT, "posterior": POS, **LOBES}

NORM = None                                                     # (stage,region,feat) -> (t,mu,sigma,nu,tau,fam)


def a2t(age):
    return np.log10(np.asarray(age, float) + A0)


def bct_z(y, mu, sigma, nu, tau):
    y = np.asarray(y, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(np.abs(nu) > 1e-8, ((y / mu) ** nu - 1.0) / (nu * sigma), np.log(y / mu) / sigma)
    F = _tdist.cdf(z, df=tau)
    F0 = np.where(nu > 0, _tdist.cdf(-1.0 / (sigma * np.abs(nu)), df=tau), 0.0)
    Ft = np.where(nu < 0, _tdist.cdf(1.0 / (sigma * np.abs(nu)), df=tau), 1.0)
    cdf = np.clip((F - F0) / (Ft - F0), 1e-12, 1 - 1e-12)
    return _norm.ppf(cdf)


def z_of(n, age, val):
    tg, mu, sg, nu, ta, fam = n
    t = a2t(age)
    mu_i, sg_i = np.interp(t, tg, mu), np.interp(t, tg, sg)
    val = np.asarray(val, float)
    if fam == "NO":
        return (val - mu_i) / sg_i
    return bct_z(val, mu_i, sg_i, np.interp(t, tg, nu), np.interp(t, tg, ta))


def _init():
    global NORM
    raw = json.load(open(NORM_JSON))
    NORM = {tuple(k.split("|")): tuple(np.array(a) if i < 5 else a for i, a in enumerate(v))
            for k, v in raw.items()}


def _one(args):
    eid, age = args
    f = f"{SM}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        return None
    try:
        d = pd.read_parquet(f, columns=["segment", "t_start_s", "stage", "artifact_flag", "channel"] + FEATS)
    except Exception:
        return None
    d = d[~d.artifact_flag.astype(bool)]
    if d.empty:
        return None
    seg_idx = d.groupby("segment", observed=True).agg(t_start_s=("t_start_s", "first"),
                                                      stage=("stage", "first"))
    stages = seg_idx.stage.values.astype(object)
    res = pd.DataFrame({"segment": seg_idx.index.values, "t_start_s": seg_idx.t_start_s.values,
                        "stage": stages, "age": age})
    for reg, chans in REGIONS.items():
        s = d if chans is None else d[d.channel.isin(chans)]
        if s.empty:
            continue
        agg = s.groupby("segment", observed=True)[FEATS].mean().reindex(seg_idx.index)
        for ft in FEATS:
            z = np.full(len(seg_idx), np.nan)
            vals = agg[ft].values
            for st in pd.unique(stages):
                key = (st, reg, ft)
                if key not in NORM:
                    continue
                m = stages == st
                z[m] = z_of(NORM[key], age, vals[m])
            res[f"z__{reg}__{ft}"] = z.astype(np.float32)
    od = OUT / f"eeg_id={eid}"
    od.mkdir(parents=True, exist_ok=True)
    res.to_parquet(od / "part.parquet", index=False)
    return eid


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    ages = dict(zip(lab.eeg_id, lab.age))
    ids = [(i, ages[i]) for i in lab.eeg_id if pd.notna(ages.get(i)) and os.path.exists(f"{SM}/eeg_id={i}")]
    if a.limit:
        ids = ids[:a.limit]
    print(f"materializing per-segment deviation for {len(ids):,} recordings "
          f"({len(REGIONS)} regions x {len(FEATS)} features) ...", flush=True)
    done = 0
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2), initializer=_init) as ex:
        for k, r in enumerate(ex.map(_one, ids, chunksize=16)):
            done += r is not None
            if (k + 1) % 2000 == 0:
                print(f"   {k+1:,}/{len(ids):,}", flush=True)
    print(f"wrote {done:,} partitions to {OUT}/  (grain: eeg_id x segment; cols z__<region>__<feature>)")


if __name__ == "__main__":
    main()
