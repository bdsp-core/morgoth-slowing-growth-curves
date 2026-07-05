"""Inject the CORRECTED, clinically-consistent labels into the derived tables the analyses read.

Principle (from Brandon): a report called NORMAL cannot, by definition, have pathological slowing.
So slowing/abnormal OVERRIDE normal — the normal reference is CLEAN normal only:
    clean_normal = normal & ~abnormal & ~focal & ~gen
The old priority cascade (normal>focal>gen) did the opposite and contaminated the reference (~57%).

Redefines `label` (used everywhere as label=="normal"/"focal_slow"/"general_slow"):
    normal        -> clean_normal
    focal_slow    -> focal flag (may also be gen; focal takes precedence for the multiclass label)
    general_slow  -> gen & ~focal
    other_abnormal-> abnormal/other, no slowing flag  (excluded from normal AND slowing groups)
    unknown       -> no canonical label (no findings/report match) (excluded)
and adds NON-exclusive flags lab_focal, lab_gen, lab_clean_normal for proper one-vs-normal tasks.

Tables updated (label column + flags): recording_features(_py), recording_asymmetry(_py), gate_probs,
bsi_features, metadata/cohort_metadata.csv.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

DER = Path("data/derived")
lab = pd.read_parquet(DER / "labels_canonical.parquet")
lab["lab_clean_normal"] = ((lab.lab_normal == 1) & (lab.lab_abnormal == 0) &
                           (lab.lab_focal == 0) & (lab.lab_gen == 0)).astype(int)


def corrected_label(r):
    if r.lab_clean_normal == 1: return "normal"
    if r.lab_focal == 1: return "focal_slow"
    if r.lab_gen == 1: return "general_slow"
    if r.lab_abnormal == 1: return "other_abnormal"
    return "unknown"


lab["label_fixed"] = lab.apply(corrected_label, axis=1)
key = lab[["bdsp_id", "label_fixed", "lab_focal", "lab_gen", "lab_clean_normal"]].drop_duplicates("bdsp_id")
print("corrected label distribution:", key.label_fixed.value_counts().to_dict())


def patch(path, is_parquet=True):
    p = DER / path if is_parquet else Path(path)
    if not p.exists():
        print(f"  skip {path} (missing)"); return
    d = pd.read_parquet(p) if is_parquet else pd.read_csv(p)
    if "bdsp_id" not in d.columns:
        print(f"  skip {path} (no bdsp_id)"); return
    d = d.drop(columns=[c for c in ("lab_focal", "lab_gen", "lab_clean_normal", "label_fixed") if c in d.columns])
    m = d.merge(key, on="bdsp_id", how="left")
    m["label"] = m.label_fixed.fillna("unknown")             # override label with corrected semantics
    for c in ("lab_focal", "lab_gen", "lab_clean_normal"):
        m[c] = m[c].fillna(0).astype(int)
    m = m.drop(columns=["label_fixed"])
    (m.to_parquet(p) if is_parquet else m.to_csv(p, index=False))
    print(f"  patched {path}: {m.bdsp_id.nunique()} recordings, "
          f"normal={int((m.drop_duplicates('bdsp_id').label=='normal').sum())}")


for f in ["recording_features.parquet", "recording_features_py.parquet",
          "recording_asymmetry.parquet", "recording_asymmetry_py.parquet",
          "gate_probs.parquet", "bsi_features.parquet", "stage_recording_features.parquet"]:
    patch(f)
patch("metadata/cohort_metadata.csv", is_parquet=False)
print("done — normal reference is now CLEAN normal only")
