"""Build the segment->stage table for the ABNORMAL recordings (their stages were produced separately and
live as per-recording stager CSVs). Uses the pipeline's canonical mapping (scripts/26:167): the stager emits
5-second windows, and each 15-s feature segment takes the window at its centre:
    segment i -> start=i*2800, end=i*2800+3000 samples @200Hz -> centre = 14i + 7.5 s -> wi = int((14i+7.5)/5)
pred_class 0..4 -> W/N1/N2/N3/REM (anything else -> Other, dropped).

Without this, severity/prevalence must be scored over ALL segments, which confounds the slowing score with
how much the patient slept — exactly the error this paper argues against.

Run: python scripts/87_build_abnormal_stages.py
"""
from __future__ import annotations
import glob, os
from pathlib import Path
import numpy as np, pandas as pd

SC = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/abn_stages"
MAP = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}
OUT = "data/derived/segment_stages_abnormal.parquet"


def main():
    seg = pd.read_parquet("data/derived/segment_features.parquet", columns=["bdsp_id", "region", "segment"])
    nseg = seg[seg.region == "whole_head"].groupby("bdsp_id").segment.max().add(1).to_dict()
    files = sorted(glob.glob(f"{SC}/*.csv"))
    print(f"abnormal stage CSVs: {len(files)}")
    rows = []
    for i, f in enumerate(files):
        bid = os.path.basename(f).split("_")[0]
        n = nseg.get(bid)
        if n is None:
            continue
        try:
            pred = pd.read_csv(f, usecols=["pred_class"]).pred_class.to_numpy()
        except Exception:
            continue
        idx = np.arange(int(n))
        wi = ((14.0 * idx + 7.5) / 5.0).astype(int)
        ok = wi < len(pred)
        if not ok.any():
            continue
        st = pd.Series(pred[wi[ok]]).map(MAP)
        rows.append(pd.DataFrame({"bdsp_id": bid, "segment": idx[ok], "stage": st.values}))
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(files)}", flush=True)
    d = pd.concat(rows, ignore_index=True).dropna(subset=["stage"])
    d.to_parquet(OUT)
    print(f"wrote {OUT}: {len(d):,} segment-stages over {d.bdsp_id.nunique():,} abnormal recordings")
    print("stage mix:", d.stage.value_counts(normalize=True).round(3).to_dict())


if __name__ == "__main__":
    main()
