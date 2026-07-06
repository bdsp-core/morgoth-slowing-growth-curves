"""Bring the cohort's original .mat features into the SAME per-(recording, region, stage) schema the
fleet produces for the expansion — no shortcuts, no proxy regions. Parses each .mat's res table
(per-segment 18x31 channels×features), joins the real re-staging (segment_stages, aligned by segment
index), and aggregates to per-(recording, region, stage) medians for all 18 bipolar channels + the 6
clinical aggregate regions. Emits the uniform table so any region (e.g. central C3/C4) is derivable
identically for cohort and expansion.

Run: python scripts/69_cohort_mat_to_uniform.py <mat_dir> <segment_stages.parquet> <out.parquet>
"""
from __future__ import annotations
import sys, glob, os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import loadmat

MAT_DIR, SEG_STAGES, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
# 18 bipolar channels in .mat order (== config/channels_regions.yaml)
CH = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",
      "Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2", "Fz-Cz", "Cz-Pz"]
AGG = {"L_temporal": [0, 1, 2, 3], "R_temporal": [4, 5, 6, 7], "L_parasagittal": [8, 9, 10, 11],
       "R_parasagittal": [12, 13, 14, 15], "midline": [16, 17], "whole_head": list(range(18))}
# feature index in the 31 (extract.py features_31 col order): powers 0-5, rel 6-10, then ratios
#   11=d/th(DTR) 12=d/a(DAR) 13=d/be 14=d/g | 15=th/d 16=th/a(TAR) 17=th/be 18=th/g | ...
# BUGFIX 2026-07-06: TAR (theta/alpha) is index 16, NOT 17 (17 = theta/beta). The old 17 corrupted the
# cohort TAR column, making it disagree ~2-3x with the expansion TAR (which uses the same features_31).
FIDX = {"log_delta": 0, "log_theta": 1, "log_alpha": 2, "log_beta": 3, "log_gamma": 4, "log_total": 5}
RELIDX = {"rel_delta": 6, "rel_theta": 7, "rel_alpha": 8, "DTR": 11, "DAR": 12, "TAR": 16}
FEATS = list(FIDX) + list(RELIDX) + ["low_freq_rel"]
_stages = None


def _init(seg_path):
    global _stages
    st = pd.read_parquet(seg_path)
    _stages = {b: dict(zip(g.segment.values, g.stage.values)) for b, g in st.groupby("bdsp_id")}


def per_channel_frame(arr18x31):
    """arr: (n_seg, 18, 31) -> DataFrame (seg, channel_idx) x FEATS."""
    d = {}
    for name, i in FIDX.items():
        d[name] = np.log(np.clip(arr18x31[:, :, i], 1e-12, None))     # linear power -> log
    for name, i in RELIDX.items():
        d[name] = arr18x31[:, :, i]
    d["low_freq_rel"] = arr18x31[:, :, 6] + arr18x31[:, :, 7]         # (delta+theta)/total
    return d


def process(f):
    bid = os.path.basename(f).split("_")[0].replace("sub-", "")
    smap = _stages.get(bid)
    if not smap:
        return None
    m = loadmat(f)
    res = m["res"]; age = float(np.ravel(m["age"])[0])
    n = res.shape[0]
    arr = np.stack([np.asarray(res[i, 3], dtype=float) for i in range(n)])   # (n,18,31)
    stages = np.array([smap.get(i, "Other") for i in range(n)])
    feat = per_channel_frame(arr)                                    # dict name->(n,18)
    rows = []
    for region, idxs in list(AGG.items()) + [(c, [i]) for i, c in enumerate(CH)]:
        reg = {name: np.nanmean(v[:, idxs], axis=1) for name, v in feat.items()}   # mean over channels/seg
        df = pd.DataFrame(reg); df["stage"] = stages
        for stage, g in df.groupby("stage"):
            if stage == "Other" or len(g) < 1:
                continue
            r = {"bdsp_id": bid, "age": age, "region": region, "stage": stage, "n_seg": len(g)}
            r.update({name: float(np.nanmedian(g[name])) for name in FEATS})
            rows.append(r)
    return rows


def main():
    files = sorted(glob.glob(f"{MAT_DIR}/*.mat"))
    print(f"parsing {len(files)} cohort .mat files...")
    out = []
    with ProcessPoolExecutor(max_workers=8, initializer=_init, initargs=(SEG_STAGES,)) as ex:
        for i, rows in enumerate(ex.map(process, files, chunksize=16)):
            if rows:
                out.extend(rows)
            if (i + 1) % 1000 == 0:
                print(f"  {i+1}/{len(files)}")
    d = pd.DataFrame(out)
    # attach sex + label
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "sex"]].drop_duplicates("bdsp_id")
    d = d.merge(meta, on="bdsp_id", how="left")
    d["label"] = "normal"
    d.to_parquet(OUT)
    print(f"wrote {OUT}: {len(d)} rows, {d.bdsp_id.nunique()} recordings, "
          f"regions={d.region.nunique()}, stages={d.stage.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
