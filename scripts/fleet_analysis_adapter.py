#!/usr/bin/env python3
"""Adapter: canonical segment_master (per eeg_id, segment, channel) -> the LEGACY analysis tables the
SAP scripts expect, WITHOUT editing those scripts:
  data/derived/channel_stage_features.parquet  (one row per bdsp_id x region x stage, segment-median)
      region = each of the 18 bipolar channels (for scripts/76 central curves) + whole_head + 5 clinical
      regions (for scripts/85 Table 1 / detection). features incl. raw DAR/TAR/DTR (=exp of log_*).
  data/derived/labels_unified.parquet          (one row per bdsp_id)
Iterates one eeg_id partition at a time -> memory-safe at full (27k / ~45GB) scale.
Run: PYTHONPATH=src python fleet_analysis_adapter.py"""
import pandas as pd, numpy as np, glob, os, sys
sys.path.insert(0, "src")
from morgoth_slowing.features.recording import CH_NAMES, _AGG

# path-portable: repo root = this file's parent dir (override with REPO env). The previous hardcoded
# "/Users/mbwest/Desktop/..." meant the analysis could only run on one machine.
REPO=os.environ.get("REPO", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SM=f"{REPO}/data/derived/segment_master"
OUTF=f"{REPO}/data/derived/channel_stage_features.parquet"
OUTL=f"{REPO}/data/derived/labels_unified.parquet"
CHAN_REGION={CH_NAMES[i]:reg for reg,ch in _AGG.items() if reg!="whole_head" for i in ch}
FEATS=["log_delta","log_theta","log_alpha","log_beta","log_gamma","log_total",
       "rel_delta","rel_theta","rel_alpha","DAR","TAR","DTR","low_freq_rel"]

def agg_one(f):
    df=pd.read_parquet(f)
    df=df[df.artifact_flag==False]
    if df.empty: return None
    for r,l in [("DAR","log_DAR"),("TAR","log_TAR"),("DTR","log_DTR")]:
        if l in df: df[r]=np.exp(df[l])
    feats=[c for c in FEATS if c in df.columns]
    eid=f.split("eeg_id=")[1].split("/")[0]
    df["region_chan"]=df.channel
    df["region_clin"]=df.channel.map(CHAN_REGION)
    parts=[]
    # per-channel rows (region = channel name) -> for the central-electrode growth curves (76)
    g=df.groupby(["channel","stage"],observed=True); m=g[feats].median(); m["n_seg"]=g.size()
    m=m.reset_index().rename(columns={"channel":"region"}); parts.append(m)
    # 5 clinical regions
    dd=df.dropna(subset=["region_clin"])
    if not dd.empty:
        g=dd.groupby(["region_clin","stage"],observed=True); m=g[feats].median(); m["n_seg"]=g.size()
        parts.append(m.reset_index().rename(columns={"region_clin":"region"}))
    # whole_head (all 18 channels)
    g=df.groupby("stage",observed=True); m=g[feats].median(); m["n_seg"]=g.size()
    m=m.reset_index(); m["region"]="whole_head"; parts.append(m)
    out=pd.concat(parts,ignore_index=True); out["bdsp_id"]=eid
    return out

files=sorted(glob.glob(f"{SM}/eeg_id=*/part.parquet"))
print(f"adapter: {len(files)} recordings", flush=True)
rows=[]
for i,f in enumerate(files):
    try:
        r=agg_one(f)
        if r is not None: rows.append(r)
    except Exception as e:
        print("  skip", f.split('eeg_id=')[1].split('/')[0], type(e).__name__, e)
    if (i+1)%500==0: print(f"  {i+1}/{len(files)}", flush=True)
feat=pd.concat(rows,ignore_index=True)

# per-recording metadata + labels from the manifest (keyed eeg_id == bdsp_id here)
man=pd.read_parquet(f"{REPO}/data/manifest/report_manifest_v6.parquet").set_index("eeg_id")
# AUTHORITATIVE AGE (do NOT use the manifest's). The manifest's `age` is a WHOLE NUMBER of years and is
# partly wrong (7 negatives; errors up to 10 y vs the true age). The corrected ages — OMOP birth_datetime
# derived, 99.6% exact, >89 binned to 90 for HIPAA Safe Harbor — are committed to metadata/ages_v6.parquet.
# Overriding here means rebuilding this table can NEVER silently revert to the bad integer ages.
import os as _os
_AGES = f"{REPO}/metadata/ages_v6.parquet"
if _os.path.exists(_AGES):
    _a = pd.read_parquet(_AGES).set_index("eeg_id")
    man["age"] = _a["age"].reindex(man.index)
    print(f"adapter: age <- {_AGES} ({int(man.age.notna().sum()):,} recordings, authoritative)", flush=True)
else:
    print("adapter: WARNING metadata/ages_v6.parquet MISSING -> manifest INTEGER ages (known bad)", flush=True)
ids=feat.bdsp_id.unique()
meta=man.reindex(ids)
meta["src"]=np.where(meta["bids_task"].eq("rEEG"),"cohort","expansion")   # routine vs overnight
# SAP §3.5/§3.7 require gen_class (pathologic vs PHYSIOLOGIC generalized slowing). It is MISSING from the
# frozen v6 manifest. Physiologic drowsiness/sleep slowing is exactly what a normal report describes, so
# equating has_gen_slow with "pathologic" would sweep 3,045 clean-normals into the abnormal class.
# Defensible derivation (data supports a clean split: clean_normal & has_gen_slow has ZERO is_abnormal):
#   pathologic  = has_gen_slow AND is_abnormal
#   physiologic = has_gen_slow AND NOT is_abnormal
# FLAGGED: the SAP intends this from a report-text phys/path classifier, not this proxy — see report.
_gs = meta.get("has_gen_slow") == True
_ab = meta.get("is_abnormal") == True
meta["gen_class"] = np.where(_gs & _ab, "pathologic", np.where(_gs & ~_ab, "physiologic", "none"))
# SAP §3.3: patient_id is REQUIRED — CIs/CV splits are patient-clustered (a patient may have several EEGs).
# SAP §3.3 PITFALL 1: clean_pair is REQUIRED — all label-dependent analyses must filter to it.
CARRY=["age","sex","src","clean_normal","is_abnormal","patient_id","clean_pair"]
md=meta[[c for c in CARRY if c in meta.columns]].copy(); md.index.name="bdsp_id"
feat=feat.merge(md.reset_index(),on="bdsp_id",how="left")
os.makedirs(os.path.dirname(OUTF),exist_ok=True)
feat.to_parquet(OUTF,index=False)

# labels: + patient_id, clean_pair, and the abnormal DETAIL the SAP Table 1 / localization need
LCOLS=["patient_id","clean_pair","is_normal","is_abnormal","has_focal_slow","has_gen_slow","gen_class",
       "focal_side","focal_region","focal_band","gen_topography","gen_band","sex","age","clean_normal"]
lu=meta[[c for c in LCOLS if c in meta.columns]].copy()
lu.index.name="bdsp_id"; lu=lu.reset_index()
lu.to_parquet(OUTL,index=False)
print("carried: patient_id=%s clean_pair=%s focal_side=%s gen_topography=%s"%(
    "patient_id" in lu, "clean_pair" in lu, "focal_side" in lu, "gen_topography" in lu))
print("clean_pair TRUE: %d / %d (SAP: label-dependent analyses filter to this)"%(
    int((lu.get("clean_pair")==True).sum()) if "clean_pair" in lu else -1, len(lu)))
print("patients: %d unique across %d recordings"%(lu.patient_id.nunique() if "patient_id" in lu else -1, len(lu)))
print(f"wrote {OUTF}: {feat.shape} | regions={feat.region.nunique()} | recs={feat.bdsp_id.nunique()}")
print(f"wrote {OUTL}: {lu.shape}")
print("label counts:", lu.assign(lab=np.where(lu.is_normal==True,'normal',np.where(lu.has_focal_slow==True,'focal',np.where(lu.gen_class=='pathologic','gen',np.where(lu.is_abnormal==True,'abn-other','unlabeled'))))).lab.value_counts().to_dict())
