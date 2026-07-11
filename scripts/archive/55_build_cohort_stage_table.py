"""(a) Build the FULL cohort per-stage table by merging the abnormal-recording sleep stages (the 7,463
`original_abnormal_stages/` predictions, never merged) with the existing `segment_stages` (normals + some
focal), then joining to `segment_features` (12,027 recs) and aggregating per (recording, region, stage).

This closes the cohort's own N3 gap for abnormal recordings — the current stage table (N3=396) is missing
all abnormal sleep because only ~5k normals were ever staged into segment_stages.

Output: data/derived/stage_recording_features.parquet (full cohort). Then run scripts/53 (inject labels)
+ scripts/54 (per-stage pathology).
"""
from __future__ import annotations
import glob, os, re
from pathlib import Path
import numpy as np, pandas as pd

DER = Path("data/derived")
FEAT = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
        "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
STAGE_MAP = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}


def main():
    ss = pd.read_parquet(DER / "segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    have = set(ss.bdsp_id.unique())
    print(f"segment_stages: {len(have)} recordings")

    # abnormal-stage CSVs: filename = <bdsp_id>_<date>.csv ; rows = per-segment pred_class (0..4), row idx = segment
    rows = []
    csvs = glob.glob("data/derived/original_abnormal_stages/*.csv")
    for i, f in enumerate(csvs):
        bid = re.sub(r"_\d{8,}$", "", os.path.basename(f)[:-4])
        if bid in have:
            continue                                     # segment_stages takes priority
        try:
            d = pd.read_csv(f, usecols=["pred_class"])
        except Exception:
            continue
        rows.append(pd.DataFrame({"bdsp_id": bid, "segment": np.arange(len(d)),
                                  "stage": d.pred_class.map(STAGE_MAP)}))
        if (i + 1) % 2000 == 0:
            print(f"  abnormal CSVs {i+1}/{len(csvs)}")
    abn = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=ss.columns)
    print(f"abnormal staging added: {abn.bdsp_id.nunique()} recordings")

    staging = pd.concat([ss, abn], ignore_index=True).dropna(subset=["stage"]).drop_duplicates(["bdsp_id", "segment"])
    print(f"combined staging: {staging.bdsp_id.nunique()} recordings, {len(staging)} segment-stages")

    sf = pd.read_parquet(DER / "segment_features.parquet")
    keep = [c for c in FEAT if c in sf.columns]
    sf = sf[["bdsp_id", "segment", "region", *keep]]
    m = sf.merge(staging, on=["bdsp_id", "segment"], how="inner")
    print(f"features x stage: {m.bdsp_id.nunique()} recordings, {len(m)} rows")

    meta = sf.groupby("bdsp_id").size().rename("nseg")  # placeholder; age/sex/label added by 53
    g = m.groupby(["bdsp_id", "region", "stage"])
    srf = g[keep].median().reset_index()
    srf["n_seg"] = g.size().values
    # carry age/sex/label from recording_features if present (53 will re-inject the corrected label anyway)
    rf = pd.read_parquet(DER / "recording_features.parquet")[["bdsp_id", "age", "sex", "label"]].drop_duplicates("bdsp_id")
    srf = srf.merge(rf, on="bdsp_id", how="left")
    srf.to_parquet(DER / "stage_recording_features.parquet")
    print(f"WROTE stage_recording_features: {srf.bdsp_id.nunique()} recordings, "
          f"N3={srf[srf.stage=='N3'].bdsp_id.nunique()}, rows={len(srf)}")


if __name__ == "__main__":
    main()
