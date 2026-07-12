#!/usr/bin/env python3
"""SAP companion adapter #3 — (a) fast grid-based adjusted_z, (b) manifest-derived legacy CSVs so the
archived analysis scripts run on NEW-DATA-ONLY inputs (they hard-code metadata/cohort_metadata.csv and
results/report_extracted_labels.csv, which were STALE/absent). Both CSVs are regenerated purely from
report_manifest_v6 and keyed on eeg_id (== bdsp_id in the analysis scripts, SAP §5.3).

Run: PYTHONPATH=src python scratchpad/adapter_legacy_compat.py
"""
import numpy as np, pandas as pd
REPO = "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
DER = f"{REPO}/data/derived"
MAN = f"{REPO}/data/manifest/report_manifest_v6.parquet"


def grid_z(age_ref, v_ref, age_q, v_q, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    ok = np.isfinite(age_ref) & np.isfinite(v_ref)
    ar, vr = age_ref[ok], v_ref[ok]
    if len(ar) < 20:
        return np.full(len(v_q), np.nan)
    # weighted mean/sd on an age grid, then interpolate to each query age
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((ar - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * vr).sum() / sw
        mu[j] = m; sd[j] = np.sqrt(max((w * (vr - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    mq = np.interp(age_q, grid[good], mu[good], left=np.nan, right=np.nan)
    sq = np.interp(age_q, grid[good], sd[good], left=np.nan, right=np.nan)
    return (v_q - mq) / sq


def build_adjusted_z():
    rec = pd.read_parquet(f"{DER}/recording_features.parquet")
    feats = ["rel_delta", "DAR", "TAR", "log_delta"]
    rows = []
    for reg, g in rec.groupby("region", observed=True):
        ref = g[g.clean_normal == 1]
        for feat in feats:
            z = grid_z(ref.age.values.astype(float), ref[feat].values.astype(float),
                       g.age.values.astype(float), g[feat].values.astype(float))
            rows.append(pd.DataFrame({"bdsp_id": g.bdsp_id.values, "label": g.label.values,
                                      "region": reg, "feature": feat, "z": z}))
    az = pd.concat(rows, ignore_index=True)
    az.to_parquet(f"{DER}/adjusted_z.parquet", index=False)
    print(f"adjusted_z {az.shape}  (non-null z={az.z.notna().sum():,})")


def build_legacy_csvs():
    m = pd.read_parquet(MAN).drop_duplicates("eeg_id")
    m["sex"] = m["sex"].map({"Male": "M", "M": "M", "Female": "F", "F": "F"})
    def lab(r):
        if r.clean_normal == 1: return "normal"
        if r.has_focal_slow == 1: return "focal_slow"
        if r.has_gen_slow == 1: return "general_slow"
        if r.is_abnormal == 1: return "abnormal"
        return np.nan
    m["label"] = m.apply(lab, axis=1)
    # cohort_metadata.csv keyed on bdsp_id == eeg_id (SAP §5.3), from manifest only
    cm = pd.DataFrame({"bdsp_id": m.eeg_id, "session": m.patient_id, "eeg_datetime": m.eeg_datetime,
                       "label": m.label, "age": m.age, "age_valid": m.age.notna(), "sex": m.sex,
                       "lab_focal": (m.has_focal_slow == 1), "lab_gen": (m.has_gen_slow == 1),
                       "lab_clean_normal": (m.clean_normal == 1), "src": m.src})
    cm.to_csv(f"{REPO}/metadata/cohort_metadata.csv", index=False)
    # report_extracted_labels.csv: bdsp_id, label, side, region, band (from manifest report labels)
    side = m.focal_side.where(m.has_focal_slow == 1)
    rl = pd.DataFrame({"bdsp_id": m.eeg_id, "label": m.label, "side": side,
                       "region": m.focal_region, "band": m.focal_band,
                       "gen_topography": m.gen_topography, "gen_band": m.gen_band})
    import os; os.makedirs(f"{REPO}/results", exist_ok=True)
    rl.to_csv(f"{REPO}/results/report_extracted_labels.csv", index=False)
    print(f"cohort_metadata.csv {cm.shape} (keyed eeg_id); report_extracted_labels.csv {rl.shape}")


if __name__ == "__main__":
    build_legacy_csvs()
    build_adjusted_z()
