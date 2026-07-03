"""Map morgoth2 sleep-staging output to the 15-s Growth_curves feature segments.

morgoth2 writes one CSV per recording (class_0..4_prob, pred_class) at a fixed step (we use 5 s),
row i => window starting at i*step seconds from recording start. Growth_curves `res` segments are
15 s (3000 samp @ 200 Hz), stepping 14 s, spanning the same 600 s. We majority-vote the staging
windows overlapping each segment. Stage codes: 0=W 1=N1 2=N2 3=N3 4=REM.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

STAGE = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}
FS = 200.0


def segment_stages(staging_csv, seg_starts, seg_ends, step_sec=5.0, fs=FS):
    """Return list of stage strings, one per feature segment (aligned to res rows).

    seg_starts/seg_ends: sample indices from res (cols 2,3). Majority pred_class over the staging
    windows whose start-time falls within the segment's [start,end] seconds; ties -> earliest.
    """
    df = pd.read_csv(staging_csv)
    pred = df["pred_class"].to_numpy()
    win_t = np.arange(len(pred)) * step_sec               # window start times (s)
    out = []
    for s, e in zip(seg_starts, seg_ends):
        s_sec, e_sec = (s - 1) / fs, e / fs
        m = (win_t >= s_sec) & (win_t < e_sec)
        if not m.any():                                    # nearest window fallback
            m = np.array([np.argmin(np.abs(win_t - (s_sec + e_sec) / 2))])
            vals = pred[m]
        else:
            vals = pred[m]
        code = int(np.bincount(vals).argmax())
        out.append(STAGE.get(code, "Other"))
    return out


def build_segment_stage_table(staging_dir, growth_raw_dir, out_path):
    """For every staged recording, map to its res segments -> parquet (bdsp_id, segment, stage)."""
    from scipy.io import loadmat
    from morgoth_slowing.io import segments as seg_io
    rows = []
    for csv in sorted(Path(staging_dir).glob("sub-*.csv")):
        bid = seg_io.parse_filename(csv)["bdsp_id"]
        # find matching feature file for its segment start/end
        feat = None
        for lbl in ("normal", "focal_slow", "general_slow"):
            cand = list((Path(growth_raw_dir) / "features" / lbl).glob(f"{csv.stem}*.mat"))
            if cand:
                feat = cand[0]; break
        if feat is None:
            continue
        res = loadmat(feat, squeeze_me=True, struct_as_record=False)["res"]
        starts = [int(r[1]) for r in res]; ends = [int(r[2]) for r in res]
        stages = segment_stages(csv, starts, ends)
        for i, st in enumerate(stages):
            rows.append({"bdsp_id": bid, "segment": i, "stage": st})
    df = pd.DataFrame(rows)
    df.to_parquet(out_path)
    return df
