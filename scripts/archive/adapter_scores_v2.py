#!/usr/bin/env python3
"""SAP companion adapter #5 — scores_v2.parquet (stage-accentuation descriptor, SAP §7.2 item 6 "ALLOWED").

Estimand: for each recording, WHICH sleep stage most accentuates its pathological slowing, i.e. the stage
whose whole-head slowing deviation (vs age- AND stage-matched clean-normals) is largest. Built from
stage_recording_features (new data) — the legacy scores_v2 came from the retired scripts/11 chain.

Writes data/derived/scores_v2.parquet [bdsp_id, label, accentuated_stage, z_<stage>...]
Run: PYTHONPATH=src python scratchpad/adapter_scores_v2.py
"""
import numpy as np, pandas as pd

REPO = "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
DER = f"{REPO}/data/derived"
STAGES = ["W", "N1", "N2", "N3", "REM"]
FEATS = ["log_delta", "DAR", "TAR"]


def grid_z(age_ref, v_ref, age_q, v_q, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    ok = np.isfinite(age_ref) & np.isfinite(v_ref); ar, vr = age_ref[ok], v_ref[ok]
    if len(ar) < 20:
        return np.full(len(v_q), np.nan)
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((ar - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * vr).sum() / sw; mu[j] = m; sd[j] = np.sqrt(max((w * (vr - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (v_q - np.interp(age_q, grid[good], mu[good], np.nan, np.nan)) / \
           np.interp(age_q, grid[good], sd[good], np.nan, np.nan)


def main():
    srf = pd.read_parquet(f"{DER}/stage_recording_features.parquet")
    wh = srf[(srf.region == "whole_head") & srf.stage.isin(STAGES) & srf.age.between(0, 100)].copy()
    wh = wh[wh.n_seg >= 3]
    out = []
    for st, g in wh.groupby("stage", observed=True):
        ref = g[g.clean_normal == 1]                      # stage-matched clean-normal reference
        z = np.zeros(len(g))
        for f in FEATS:                                   # summed deviation over the 3 slowing features
            z = z + np.nan_to_num(grid_z(ref.age.values.astype(float), ref[f].values.astype(float),
                                         g.age.values.astype(float), g[f].values.astype(float)))
        out.append(pd.DataFrame({"bdsp_id": g.bdsp_id.values, "label": g.label.values,
                                 "stage": st, "z": z / len(FEATS)}))
    Z = pd.concat(out, ignore_index=True)
    piv = Z.pivot_table(index="bdsp_id", columns="stage", values="z")
    piv["accentuated_stage"] = piv[[s for s in STAGES if s in piv.columns]].idxmax(axis=1)
    lab = Z.drop_duplicates("bdsp_id").set_index("bdsp_id").label
    piv["label"] = lab
    piv = piv.reset_index()
    piv.to_parquet(f"{DER}/scores_v2.parquet", index=False)
    print(f"scores_v2 {piv.shape}")
    print("accentuated_stage among ABNORMAL:")
    print(piv[piv.label.isin(["focal_slow", "general_slow"])].accentuated_stage.value_counts().to_string())


if __name__ == "__main__":
    main()
