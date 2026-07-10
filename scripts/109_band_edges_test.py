"""Band test: does closing the 7-8 Hz hole rescue the band descriptor, and what is the best band feature?

Our band edges leave a hole: theta = 4-7, alpha = 8-13. Clinical theta runs to 8 Hz, so 7-7.9 Hz slowing is
discarded. And the old band index (z_theta - z_delta) is a difference of collinear z's (r=0.87). MBW's primary
principle: pick the feature MOST CORRELATED WITH THE REPORT BAND WORD.

This recomputes whole-head band powers from raw EEG for a labelled subset, both ways, and compares band
descriptors against the report band word (delta vs theta):
  theta_47  : theta = 4-7 Hz (current)
  theta_48  : theta = 4-8 Hz (alpha starts at 8)
  BI_z      : z_theta - z_delta            (old, deprecated)
  BI_excess : dP_theta / (dP_delta + dP_theta), excess power over the age/stage normal mean (linear units)

Selection = recordings with a report band word (gen_band / focal_band in {delta, theta}), clean_pair.

Run: PYTHONPATH=src python scripts/109_band_edges_test.py [N]
"""
from __future__ import annotations
import os, sys, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, "src")
from morgoth_slowing.features import extract as ex, artifact as af
from morgoth_slowing.io.edf import load_edf_referential

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
RC = os.environ.get("RCLONE_BIN", str(Path.home() / ".local/bin/rclone"))
REPO = "s3:bdsp-opendata-repository/EEG/bids"
CKPT = "data/derived/band_test_features.parquet"
GRID = np.arange(0, 101, 2.0); BW = 5.0


def band_power(freqs, psd, lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return np.trapz(psd[:, m], freqs[m], axis=1)


def edf_path(bid, date):
    site = "S0001" if bid.startswith("S0001") else "S0002"
    base = f"bdsp-opendata-repository/EEG/bids/{site}/sub-{bid}"
    r = subprocess.run([RC, "lsf", f"s3:{base}/", "--recursive", "--include", "*.edf"],
                       capture_output=True, text=True)
    cands = [x for x in r.stdout.strip().split("\n") if x]
    if not cands: return None
    hit = [x for x in cands if date and date[:8] in x] or cands
    return f"{base}/{hit[0]}"


def main():
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "eeg_datetime", "gen_band", "focal_band", "gen_class", "has_focal_slow"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]].drop_duplicates("bdsp_id")
    ex_ids = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    lu = lu.merge(cp, on="bdsp_id").query("clean_pair == True")
    lu = lu[~lu.bdsp_id.isin(ex_ids)]
    lu["band"] = lu.gen_band.where(lu.gen_band.isin(["delta", "theta"]),
                                   lu.focal_band.where(lu.focal_band.isin(["delta", "theta"])))
    lab = lu.dropna(subset=["band"]).copy()
    # balance delta/theta, cap at N
    lab = pd.concat([g.sample(min(len(g), N // 2), random_state=0) for _, g in lab.groupby("band")])
    print(f"labelled subset: {len(lab)} recordings ({lab.band.value_counts().to_dict()})", flush=True)

    done = set()
    rows = []
    if os.path.exists(CKPT):
        prev = pd.read_parquet(CKPT); rows = prev.to_dict("records"); done = set(prev.bdsp_id)
        print(f"resume: {len(done)} already computed", flush=True)

    work = Path(tempfile.mkdtemp())
    for i, r in enumerate(lab.itertuples()):
        if r.bdsp_id in done: continue
        try:
            ep = edf_path(r.bdsp_id, str(r.eeg_datetime))
            if not ep: continue
            for f in work.glob("*.edf"): f.unlink()
            subprocess.run([RC, "copy", f"s3:{ep}", str(work)], check=True, capture_output=True, timeout=180)
            src = next(work.glob("*.edf"))
            data, chs, fs = load_edf_referential(str(src))
            bip = ex.to_bipolar(ex.preprocess(data.astype(np.float32), fs), chs)
            segidx = ex.segment_indices(bip.shape[0])
            mask, _ = af.usable_mask(bip, segidx, fs)
            dp = th47 = th48 = ap = 0.0; nseg = 0
            for k, (s, e) in enumerate(segidx):
                if not mask[k]: continue
                fr, psd = ex.multitaper_psd(bip[s:e].T, fs)   # (18, nf)
                whole = psd.mean(0, keepdims=True)             # whole-head PSD
                dp += band_power(fr, whole, 1, 4)[0]
                th47 += band_power(fr, whole, 4, 7)[0]
                th48 += band_power(fr, whole, 4, 8)[0]
                ap += band_power(fr, whole, 8, 13)[0]
                nseg += 1
            if nseg < 5: continue
            rows.append(dict(bdsp_id=r.bdsp_id, band=r.band, dp=dp / nseg, th47=th47 / nseg,
                             th48=th48 / nseg, ap=ap / nseg, nseg=nseg))
            if len(rows) % 25 == 0:
                pd.DataFrame(rows).to_parquet(CKPT)
                print(f"  {len(rows)} computed", flush=True)
        except Exception as exn:
            print(f"  skip {r.bdsp_id}: {type(exn).__name__}", flush=True)
            continue
    pd.DataFrame(rows).to_parquet(CKPT)
    print(f"done: {len(rows)} recordings -> {CKPT}")


if __name__ == "__main__":
    main()
