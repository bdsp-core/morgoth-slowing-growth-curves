#!/usr/bin/env python3
"""ONE Morgoth-free model — step 1: cohort, patient-stratified split, per-segment features.

Trains on the SINGLE-SCORED report data; MoE and OccasionNoise are held-out EXTERNAL test sets (never seen in
training). The model is segment-level: each 15 s segment -> stage-matched deviation features (same norm,
grid_norm.json / grid_anorm.json, used everywhere). Two heads (focal, generalized).

  amount (generalized): whole-head deviation z per feature (stage+age matched)
  focal localization: per-region z -> peak z, focality (peak - median region), asymmetry z

Report cohort: clean_pair, age known, segment_master present. Split by PATIENT (no leakage, SAP §3.3),
stratified on age-band x class {control, focal_only, gen_only, both, other-abnormal}. Segments are capped per
recording (stratified by stage) to bound size; sizes via env (N_TRAIN, N_TEST, SEG_CAP).

Writes data/derived/single_model_segfeats.parquet (per-segment rows: eeg_id, segment, stage, dataset, split,
patient_id, age, y_focal, y_gen, <features>) and data/derived/single_model_eeg.parquet (per-eeg labels).
Run: PYTHONPATH=src python3 scripts/53_single_model_features.py
"""
from __future__ import annotations
import importlib.util, os
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd

m49 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py"))
importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py").loader.exec_module(m49)
m45 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m45", "scripts/45_moe_section0.py"))
importlib.util.spec_from_file_location("m45", "scripts/45_moe_section0.py").loader.exec_module(m45)
m43 = m49.m43
SM = "data/derived/segment_master"
FEATS = m49.FEATS; FOC_F = m49.FOC_F; LOC_REGIONS = m49.LOC_REGIONS; REG_CH = m49.REG_CH; PAIRS = m49.PAIRS
NORM = m49.NORM; ANORM = m49.ANORM
SEG_CAP = int(os.environ.get("SEG_CAP", "80"))
N_TRAIN = int(os.environ.get("N_TRAIN", "6000")); N_TEST = int(os.environ.get("N_TEST", "3000"))
AMT = [f"amt_{ft}" for ft in FEATS]
FOC = [f"{p}_{ft}" for ft in FOC_F for p in ("peak", "foc", "asym")]


def seg_feats(eid, age):
    """per-segment stage-matched feature rows for one recording."""
    f = f"{SM}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f) or not np.isfinite(age):
        return None
    d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel"] + FEATS)
    d = d[(~d.artifact_flag.astype(bool)) & d.stage.isin(["W", "N1", "N2", "N3", "REM"])]
    if d.empty:
        return None
    if d.segment.nunique() > SEG_CAP:                       # cap segments, stratified by stage
        keep = (d.drop_duplicates("segment")[["segment", "stage"]]
                .groupby("stage", group_keys=False).apply(lambda g: g.sample(min(len(g), max(1, SEG_CAP // 5)),
                                                                              random_state=0)).segment)
        d = d[d.segment.isin(set(keep))]
    rows = d.drop_duplicates("segment")[["segment", "stage"]].set_index("segment")
    out = pd.DataFrame(index=rows.index); out["stage"] = rows.stage
    wh = d.groupby(["segment", "stage"], observed=True)[FEATS].mean()
    for ft in FEATS:
        z = np.full(len(rows), np.nan)
        for st in rows.stage.unique():
            key = (st, "whole_head", ft)
            if key in NORM:
                m = rows.stage.values == st
                vals = wh.xs(st, level="stage")[ft].reindex(rows.index[m]).values
                zz = m43.z_of(NORM[key], age, vals); z[m] = -zz if ft == "rel_alpha" else zz
        out[f"amt_{ft}"] = z
    reg = {r: d[d.channel.isin(ch)].groupby(["segment", "stage"], observed=True)[FOC_F].mean() for r, ch in REG_CH.items()}
    for ft in FOC_F:
        Z = {}
        for r in LOC_REGIONS:
            z = np.full(len(rows), np.nan)
            if r in reg:
                for st in rows.stage.unique():
                    key = (st, r, ft)
                    if key in NORM:
                        m = rows.stage.values == st
                        try:
                            vals = reg[r].xs(st, level="stage")[ft].reindex(rows.index[m]).values
                        except KeyError:
                            continue
                        z[m] = m43.z_of(NORM[key], age, vals)
            Z[r] = z
        M = np.vstack([Z[r] for r in LOC_REGIONS])
        with np.errstate(all="ignore"):
            out[f"peak_{ft}"] = np.nanmax(M, axis=0)
            out[f"foc_{ft}"] = np.nanmax(M, axis=0) - np.nanmedian(M, axis=0)
        asym = np.full(len(rows), np.nan)
        for L, R in PAIRS:
            if L in reg and R in reg:
                for st in rows.stage.unique():
                    key = (st, f"{L}|{R}", ft)
                    if key in ANORM:
                        m = rows.stage.values == st
                        try:
                            dv = (reg[L].xs(st, level="stage")[ft] - reg[R].xs(st, level="stage")[ft]).reindex(rows.index[m]).values
                        except KeyError:
                            continue
                        mu, sd = ANORM[key]; a = np.abs((dv - mu) / (sd or 1.0))
                        asym[m] = np.fmax(asym[m], a) if not np.all(np.isnan(asym[m])) else a
        out[f"asym_{ft}"] = asym
    out = out.reset_index(); out["eeg_id"] = eid; out["age"] = age
    return out


def report_cohort():
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = lab[(lab.clean_pair == True) & lab.age.notna() & lab.patient_id.notna() &  # noqa: E712
            (~lab.eeg_id.astype(str).str.startswith(("MOE_", "ON_")))].copy()
    d = d[[os.path.exists(f"{SM}/eeg_id={i}") for i in d.eeg_id]]
    foc = d.slowing_focal.fillna(False).astype(bool); gen = d.slowing_gen_pathologic.fillna(False).astype(bool)
    cn = d.clean_normal.fillna(False).astype(bool)
    d["cls"] = np.select([cn, foc & gen, foc & ~gen, ~foc & gen], ["control", "both", "focal_only", "gen_only"], "other")
    d["y_focal"] = foc.astype(int); d["y_gen"] = gen.astype(int)
    d["ageband"] = pd.cut(d.age, [0, 2, 18, 40, 65, 200], labels=["inf", "child", "ya", "adult", "elder"])
    # patient-level split, stratified on the patient's (cls, ageband) [first recording as the stratum proxy]
    d["ageband"] = d.ageband.astype(str)
    pat = d.sort_values("eeg_id").groupby("patient_id").agg(cls=("cls", "first"), ageband=("ageband", "first"))
    rng = np.random.default_rng(0)
    pat["split"] = "train"
    for (c, a), grp in pat.groupby(["cls", "ageband"], observed=True):
        te = rng.choice(grp.index, int(0.3 * len(grp)), replace=False)
        pat.loc[te, "split"] = "test"
    d["split"] = d.patient_id.map(pat.split)
    # stratified sample of recordings per split (bound compute)
    def samp(sub, n):
        return sub.groupby("cls", group_keys=False).apply(
            lambda g: g.sample(min(len(g), max(1, int(n * len(g) / len(sub)))), random_state=0))
    tr = samp(d[d.split == "train"], N_TRAIN); te = samp(d[d.split == "test"], N_TEST)
    return pd.concat([tr, te])


def main():
    rep = report_cohort()
    print(f"report cohort: {len(rep):,} recordings | train {int((rep.split=='train').sum()):,} "
          f"test {int((rep.split=='test').sum()):,}", flush=True)
    print("  class x split:\n", pd.crosstab(rep.cls, rep.split), flush=True)
    # external test sets
    onlab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    occ = pd.read_parquet("data/derived/occasion_features.parquet")
    occ_age = occ[(occ.stage == "W") & (occ.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    occ_ids = [(f"ON_{int(fid)}", float(occ_age[fid])) for fid in occ_age.index if os.path.exists(f"{SM}/eeg_id=ON_{int(fid)}")]
    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id")
    moe_ids = [(e, float(onlab.age.get(e, np.nan))) for e in head.eeg_id if str(e).startswith("MOE_")]

    jobs = [(r.eeg_id, r.age, "report", r.split, r.patient_id, r.y_focal, r.y_gen) for _, r in rep.iterrows()]
    jobs += [(e, a, "occasion", "test", e, np.nan, np.nan) for e, a in occ_ids]
    jobs += [(e, a, "moe", "test", e, np.nan, np.nan) for e, a in moe_ids]
    print(f"extracting per-segment features for {len(jobs):,} recordings (report+occasion+moe) ...", flush=True)

    def work(j):
        eid, age, ds, split, pat, yf, yg = j
        r = seg_feats(eid, age)
        if r is None:
            return None
        r["dataset"] = ds; r["split"] = split; r["patient_id"] = pat; r["y_focal"] = yf; r["y_gen"] = yg
        return r
    with ThreadPoolExecutor(max_workers=14) as ex:
        parts = [p for p in ex.map(work, jobs) if p is not None]
    S = pd.concat(parts, ignore_index=True)
    for c in AMT + FOC:
        if c not in S.columns:
            S[c] = np.nan
    S.to_parquet("data/derived/single_model_segfeats.parquet", index=False)
    eeg = S.drop_duplicates("eeg_id")[["eeg_id", "dataset", "split", "patient_id", "age", "y_focal", "y_gen"]]
    eeg.to_parquet("data/derived/single_model_eeg.parquet", index=False)
    print(f"wrote single_model_segfeats.parquet: {len(S):,} segment rows, {S.eeg_id.nunique():,} recordings")
    print("  by dataset:", S.drop_duplicates('eeg_id').dataset.value_counts().to_dict())


if __name__ == "__main__":
    main()
