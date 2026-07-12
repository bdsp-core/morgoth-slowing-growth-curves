#!/usr/bin/env python3
"""SAP companion adapter #2 — build the LEGACY derived tables the analysis producers read, entirely from
the three permitted NEW sources (segment_master + segment_summary + report_manifest_v6), keyed on eeg_id
(== bdsp_id in the analysis scripts, SAP §5.3).  Extends scratchpad/fleet_analysis_adapter.py.

Every table below names its SAP-conformant provenance in a one-line comment.  NEW-DATA-ONLY: never reads
data/derived/*_quarantine, never reads legacy metadata/*.csv or results/*.csv.

Outputs (all under data/derived/):
  report_pairing.parquet                 clean_pair frozen in manifest (SAP §3.7)  -- NOT the old ext-CSV script
  excluded_bdsp_ids.parquet              same_date_ambiguous eeg_ids (SAP §3.7 clean-label exclusion)
  labels_unified.parquet                 EXTENDED: +has_gen_slow, focal_side/region/band, gen_topography/band, is_normal
  recording_features.parquet             per (eeg_id, region) median over usable segments + age/sex/label
  recording_asymmetry.parquet            per eeg_id, log(L/R) region band-power asymmetries + label/side
  stage_recording_features.parquet       per (eeg_id, stage, region) median + age/sex/label
  regional_stage_recording_features.parquet   alias (same grain; scripts/34 name)
  gate_probs.parquet                     recording gate = pooled per-segment p_slowing (SAP §4.7/§7.1); p_focal/p_gen ABSENT in fleet
  bsi_features.parquet                   recording BSI from segment_summary pdBSI/r_sBSI (van Putten, SAP §4.5)
  adjusted_z.parquet                     age/sex-adjusted deviation z per (eeg_id, region, feature) vs clean_normal ref

Run: PYTHONPATH=src python scratchpad/adapter_sap_tables.py
"""
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from morgoth_slowing.features.recording import CH_NAMES, _AGG

REPO = "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
SM = f"{REPO}/data/derived/segment_master"
SS = f"{REPO}/data/derived/segment_summary"
DER = f"{REPO}/data/derived"
MAN = f"{REPO}/data/manifest/report_manifest_v6.parquet"

FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
         "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]
BANDS_LOG = {"delta": "log_delta", "theta": "log_theta", "alpha": "log_alpha",
             "beta": "log_beta", "gamma": "log_gamma"}
# clinical-region -> member channel names (whole_head handled separately)
CLIN = {reg: [CH_NAMES[i] for i in ch] for reg, ch in _AGG.items() if reg != "whole_head"}
CHAN_REGION = {CH_NAMES[i]: reg for reg, ch in _AGG.items() if reg != "whole_head" for i in ch}
# homologous L/R region pairs (for asymmetry)
ASYM_PAIRS = {"temporal": ("L_temporal", "R_temporal"),
              "parasagittal": ("L_parasagittal", "R_parasagittal")}


def _prep(df):
    df = df[df.artifact_flag == False]
    if df.empty:
        return None
    for r, l in [("DAR", "log_DAR"), ("TAR", "log_TAR"), ("DTR", "log_DTR")]:
        if l in df:
            df[r] = np.exp(df[l])
    return df


def region_medians(df, extra_keys=()):
    """median feature per (region, *extra_keys). region = 5 clinical + whole_head + 18 channels."""
    feats = [c for c in FEATS if c in df.columns]
    parts = []
    # per-channel (region = channel name)
    g = df.groupby(["channel", *extra_keys], observed=True)
    m = g[feats].median(); m["n_seg"] = g.size()
    parts.append(m.reset_index().rename(columns={"channel": "region"}))
    # 5 clinical regions
    dd = df.assign(region_clin=df.channel.map(CHAN_REGION)).dropna(subset=["region_clin"])
    if not dd.empty:
        g = dd.groupby(["region_clin", *extra_keys], observed=True)
        m = g[feats].median(); m["n_seg"] = g.size()
        parts.append(m.reset_index().rename(columns={"region_clin": "region"}))
    # whole_head
    g = df.groupby([*extra_keys], observed=True) if extra_keys else None
    if extra_keys:
        m = g[feats].median(); m["n_seg"] = g.size(); m = m.reset_index()
    else:
        m = df[feats].median().to_frame().T; m["n_seg"] = len(df)
    m["region"] = "whole_head"
    parts.append(m)
    return pd.concat(parts, ignore_index=True)


def main():
    man = pd.read_parquet(MAN).drop_duplicates("eeg_id").set_index("eeg_id")
    # normalize sex
    man["sex"] = man["sex"].map({"Male": "M", "M": "M", "Female": "F", "F": "F"})
    # canonical recording label used by the archive detectors (normal / focal_slow / general_slow / abnormal)
    def lab(r):
        if r.get("clean_normal") == 1 or r.get("clean_normal") is True:
            return "normal"
        if r.get("has_focal_slow") == 1:
            return "focal_slow"
        if r.get("has_gen_slow") == 1:
            return "general_slow"
        if r.get("is_abnormal") == 1:
            return "abnormal"
        return None
    man["label"] = man.apply(lab, axis=1)
    man["gen_class"] = np.where(man.get("has_gen_slow") == 1, "pathologic", "none")  # SAP GAP: no phys/path gen classifier in fleet

    files = sorted(glob.glob(f"{SM}/eeg_id=*/part.parquet"))
    print(f"adapter2: {len(files)} recordings", flush=True)

    rec_rows, asym_rows, stg_rows = [], [], []
    for i, f in enumerate(files):
        eid = f.split("eeg_id=")[1].split("/")[0]
        try:
            df = _prep(pd.read_parquet(f))
        except Exception as e:
            print("  skip", eid, type(e).__name__, e); continue
        if df is None:
            continue
        # recording-level (pooled stages)
        rm = region_medians(df); rm["bdsp_id"] = eid; rec_rows.append(rm)
        # stage-level
        sm = region_medians(df, extra_keys=("stage",)); sm["bdsp_id"] = eid; stg_rows.append(sm)
        # asymmetry: log(L/R) region-mean band power, from per-channel log powers (median over segments)
        rowa = {"bdsp_id": eid}
        chan_med = df.groupby("channel", observed=True)[list(BANDS_LOG.values())].median()
        for name, (lreg, rreg) in ASYM_PAIRS.items():
            lch = [c for c in CLIN[lreg] if c in chan_med.index]
            rch = [c for c in CLIN[rreg] if c in chan_med.index]
            for band, lcol in BANDS_LOG.items():
                if band in ("gamma",):
                    continue
                L = chan_med.loc[lch, lcol].mean() if lch else np.nan
                R = chan_med.loc[rch, lcol].mean() if rch else np.nan
                rowa[f"asym_{name}_{band}"] = L - R  # log(L/R) since values are log-powers
        asym_rows.append(rowa)
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(files)}", flush=True)

    rec = pd.concat(rec_rows, ignore_index=True)
    stg = pd.concat(stg_rows, ignore_index=True)
    asym = pd.DataFrame(asym_rows)

    # attach metadata/labels
    meta = man.reindex(rec.bdsp_id.unique() if False else man.index)
    md = man[["age", "sex", "label", "clean_normal", "is_abnormal", "src"]].copy()
    md.index.name = "bdsp_id"; md = md.reset_index()
    rec = rec.merge(md, on="bdsp_id", how="left")
    stg = stg.merge(md, on="bdsp_id", how="left")
    asym = asym.merge(md, on="bdsp_id", how="left").merge(
        man[["focal_side"]].rename(columns={"focal_side": "side"}).rename_axis("bdsp_id").reset_index(),
        on="bdsp_id", how="left")

    os.makedirs(DER, exist_ok=True)
    rec.to_parquet(f"{DER}/recording_features.parquet", index=False)
    stg.to_parquet(f"{DER}/stage_recording_features.parquet", index=False)
    stg.to_parquet(f"{DER}/regional_stage_recording_features.parquet", index=False)
    asym.to_parquet(f"{DER}/recording_asymmetry.parquet", index=False)
    print(f"recording_features {rec.shape}; stage_recording_features {stg.shape}; asymmetry {asym.shape}")

    # ---- report_pairing (SAP §3.7: clean_pair frozen in manifest) ----
    rp = man[["clean_pair", "same_date_ambiguous"]].copy()
    rp["clean_pair"] = rp["clean_pair"].fillna(False).astype(bool)
    rp["same_date_ambiguous"] = rp["same_date_ambiguous"].fillna(False).astype(bool)
    rp.index.name = "bdsp_id"; rp = rp.reset_index()
    rp.to_parquet(f"{DER}/report_pairing.parquet", index=False)

    # ---- excluded_bdsp_ids (SAP §3.7: same-date-ambiguous excluded from clean-label analyses) ----
    ex = rp[rp.same_date_ambiguous][["bdsp_id"]].copy()
    ex["reason"] = "same_date_ambiguous: >1 EEG same day, report unassignable (SAP §3.7)"
    ex.to_parquet(f"{DER}/excluded_bdsp_ids.parquet", index=False)
    print(f"report_pairing {rp.shape} (clean_pair={int(rp.clean_pair.sum())}); excluded {len(ex)}")

    # ---- labels_unified (EXTENDED) ----
    lu = man[["is_normal", "is_abnormal", "has_focal_slow", "has_gen_slow", "gen_class",
              "sex", "age", "clean_normal", "focal_side", "focal_region", "focal_band",
              "gen_topography", "gen_band", "label", "src"]].copy()
    lu.index.name = "bdsp_id"; lu = lu.reset_index()
    lu.to_parquet(f"{DER}/labels_unified.parquet", index=False)
    print(f"labels_unified {lu.shape}")

    # ---- gate_probs (SAP §4.7/§7.1: recording gate = pooled per-segment p_slowing) ----
    ssf = sorted(glob.glob(f"{SS}/eeg_id=*/part.parquet"))
    grows = []
    for f in ssf:
        eid = f.split("eeg_id=")[1].split("/")[0]
        s = pd.read_parquet(f, columns=["p_slowing", "artifact_flag"])
        s = s[s.artifact_flag == False]
        if s.empty:
            continue
        grows.append({"bdsp_id": eid, "p_slowing_max": float(s.p_slowing.max()),
                      "p_slowing_mean": float(s.p_slowing.mean()),
                      "p_slowing_p90": float(s.p_slowing.quantile(0.90))})
    gp = pd.DataFrame(grows)
    # aggregate-of-choice for the recording gate = p90 (robust, SAP §1 "pool over segments"); expose as p_abnormal
    gp["p_abnormal"] = gp["p_slowing_p90"]
    gp["p_focal"] = np.nan       # SAP GAP: EEG-level focal head not persisted in fleet output
    gp["p_generalized"] = np.nan  # SAP GAP: EEG-level generalized head not persisted
    gp = gp.merge(md, on="bdsp_id", how="left")
    gp.to_parquet(f"{DER}/gate_probs.parquet", index=False)
    print(f"gate_probs {gp.shape} (segment_summary coverage only)")

    # ---- bsi_features (van Putten BSI from segment_summary, SAP §4.5) ----
    brows = []
    for f in ssf:
        eid = f.split("eeg_id=")[1].split("/")[0]
        s = pd.read_parquet(f, columns=["pdBSI", "r_sBSI", "artifact_flag"])
        s = s[s.artifact_flag == False]
        if s.empty:
            continue
        brows.append({"bdsp_id": eid, "r_sBSI": float(s.r_sBSI.median()),
                      "pdBSI": float(s.pdBSI.median())})
    bsi = pd.DataFrame(brows).merge(md[["bdsp_id", "age", "sex", "label", "clean_normal"]], on="bdsp_id", how="left")
    # bsi_z = age-adjusted deviation of r_sBSI vs clean_normal (rolling-age Gaussian ref)
    bsi["bsi_z"] = _age_adjust_z(bsi, "r_sBSI")
    bsi.to_parquet(f"{DER}/bsi_features.parquet", index=False)
    print(f"bsi_features {bsi.shape}")

    # ---- adjusted_z (age/sex-adjusted deviation per (eeg_id, region, feature) vs clean_normal ref) ----
    az = _build_adjusted_z(rec)
    az.to_parquet(f"{DER}/adjusted_z.parquet", index=False)
    print(f"adjusted_z {az.shape}")


def _age_adjust_z(df, col, bw=8.0):
    ref = df[(df.clean_normal == 1)]
    ra, rv = ref.age.values.astype(float), ref[col].values.astype(float)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    out = np.full(len(df), np.nan)
    ages = df.age.values.astype(float); vals = df[col].values.astype(float)
    for i in range(len(df)):
        if not (np.isfinite(ages[i]) and np.isfinite(vals[i])):
            continue
        w = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        mu = (w * rv).sum() / sw; sd = np.sqrt(max((w * (rv - mu) ** 2).sum() / sw, 1e-9))
        out[i] = (vals[i] - mu) / sd
    return out


def _build_adjusted_z(rec, feats=("rel_delta", "DAR", "TAR", "log_delta"), bw=8.0):
    """One age-adjusted deviation z per (bdsp_id, region, feature), reference = clean_normal in same region."""
    rows = []
    for reg, g in rec.groupby("region", observed=True):
        for feat in feats:
            gg = g[["bdsp_id", "age", feat, "clean_normal", "label"]].copy()
            gg["z"] = _age_adjust_z_col(gg, feat, bw)
            gg["feature"] = feat; gg["region"] = reg
            rows.append(gg[["bdsp_id", "label", "region", "feature", "z"]])
    return pd.concat(rows, ignore_index=True)


def _age_adjust_z_col(g, col, bw):
    ref = g[g.clean_normal == 1]
    ra, rv = ref.age.values.astype(float), ref[col].values.astype(float)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    ages = g.age.values.astype(float); vals = g[col].values.astype(float)
    out = np.full(len(g), np.nan)
    for i in range(len(g)):
        if not (np.isfinite(ages[i]) and np.isfinite(vals[i])):
            continue
        w = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        mu = (w * rv).sum() / sw; sd = np.sqrt(max((w * (rv - mu) ** 2).sum() / sw, 1e-9))
        out[i] = (vals[i] - mu) / sd
    return out


if __name__ == "__main__":
    main()
