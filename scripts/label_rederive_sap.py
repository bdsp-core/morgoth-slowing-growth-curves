"""Re-derive slowing labels per SAP §3.4/§3.5 — CORRECTING a real labelling bug.

THE BUG (found 2026-07-12): `scripts/20_extract_report_labels.py:118` regexes the IMPRESSION
CONCATENATED WITH THE WHOLE REPORT BODY (`impression + " || " + reports`). So `has_gen_slow` fires on any
mention of slowing anywhere — including a purely descriptive body line such as
    "occasional bursts of generalized slowing, likely related to intermittent drowsiness"
which is PHYSIOLOGIC (drowsiness/sleep) slowing in a NORMAL study. Treating `has_gen_slow` as "pathologic"
therefore drags thousands of physiologic normals into the abnormal/positive class and corrupts every
detection and dose-response analysis.

THE RULE (MBW, 2026-07-12):
  * FOCAL slowing is ALWAYS pathologic — no physiologic/pathologic split needed.
  * GENERALIZED slowing is pathologic ONLY IF the reader lists it as one of the abnormalities (i.e. it
    appears in the impression / "abnormal EEG due to ..." list). Otherwise it is physiologic.
  * An EEG can be ABNORMAL WITHOUT SLOWING (e.g. epileptiform discharges). Those are NOT slowing-positive
    and are NOT clean_normal — they are their own stratum (`abnormal_no_slowing`), which is exactly the
    middle tier the dose-response wants.
  * Look in the IMPRESSION first (the usual, easiest place the reader states the conclusion); when absent,
    fall back to the report DETAIL (report_text).

Outputs data/derived/recording_labels_sap.parquet (one row per eeg_id):
  slowing_focal (bool)          focal slowing — always pathologic
  slowing_gen_pathologic (bool) generalized slowing named as an abnormality
  slowing_gen_physiologic(bool) generalized slowing attributed to drowsiness/sleep, or in a normal study
  slowing_positive (bool)       focal OR gen-pathologic  -> the DETECTION POSITIVE class
  abnormal_no_slowing (bool)    abnormal, but slowing not among the abnormalities
  clean_normal (bool)           unchanged (impression-normal is ground truth)
  label_source                  'impression' | 'report_detail' | 'none'
Run: PYTHONPATH=src python scripts/label_rederive_sap.py
"""
from __future__ import annotations
import re
import numpy as np, pandas as pd
from pathlib import Path

MAN = "data/manifest/report_manifest_v6.parquet"
OUT = Path("data/derived/recording_labels_sap.parquet")

SLOW = re.compile(r"\b(slow|slowing|delta|theta)\b", re.I)
# the reader's conclusion section, when it is embedded in the body
IMP_SECTION = re.compile(r"(?:impression|interpretation|summary)\s*:?\s*(.{0,1200})", re.I | re.S)
# a slowing mention attributed to a NORMAL state -> physiologic
PHYSIO_CTX = re.compile(
    r"(drows|asleep|sleep|hypnagog|arousal|state change|photic|hyperventilat|normal variant|"
    r"expected for (?:age|state)|consistent with (?:drowsiness|sleep))", re.I)
# the construction that lists what makes the study abnormal
ABN_DUE = re.compile(r"abnormal[^.]{0,60}?(?:due to|because of|secondary to|characterized by|consisting of)", re.I)
NEGATED = re.compile(r"\b(no|without|absent|denies)\b[^.]{0,40}\b(slow|slowing|delta|theta)\b", re.I)


def sentences(t: str):
    return [s for s in re.split(r"[.;\n]", t or "") if s.strip()]


def slowing_named_as_abnormality(imp: str) -> bool:
    """Slowing appears in the reader's conclusion as one of the abnormalities (not negated, not
    attributed to a normal state)."""
    if not imp:
        return False
    for s in sentences(imp):
        if not SLOW.search(s):
            continue
        if NEGATED.search(s):            # "no focal slowing"
            continue
        if PHYSIO_CTX.search(s):         # "slowing related to drowsiness"
            continue
        return True
    return False


def physiologic_slowing(text: str) -> bool:
    """A slowing mention explicitly attributed to a normal state (drowsiness/sleep)."""
    for s in sentences(text):
        if SLOW.search(s) and not NEGATED.search(s) and PHYSIO_CTX.search(s):
            return True
    return False


def get_conclusion(imp_field: str, body: str):
    """Impression FIRST (the usual place); else the impression/interpretation section parsed out of the
    report detail; else '' (we then fall back to the detail as a whole, flagged as lower confidence)."""
    if imp_field and imp_field.strip():
        return imp_field, "impression"
    m = IMP_SECTION.search(body or "")
    if m:
        return m.group(1), "report_detail"
    return "", "none"


def main():
    m = pd.read_parquet(MAN)
    imp_f = m.get("report_impression", pd.Series("", index=m.index)).fillna("").astype(str)
    body = m.get("report_text", pd.Series("", index=m.index)).fillna("").astype(str)

    concl, src = [], []
    for a, b in zip(imp_f, body):
        c, s = get_conclusion(a, b)
        concl.append(c); src.append(s)
    concl = pd.Series(concl, index=m.index); src = pd.Series(src, index=m.index)

    is_abn = m.get("is_abnormal") == True
    clean_norm = m.get("clean_normal") == True
    has_gen = m.get("has_gen_slow") == True
    has_foc = m.get("has_focal_slow") == True

    # slowing named as an abnormality — in the conclusion when we have one, else in the detail (flagged)
    named = pd.Series([slowing_named_as_abnormality(c) for c in concl], index=m.index)
    fallback = src.eq("none") & is_abn
    if fallback.any():
        # no conclusion section at all: accept the "abnormal ... due to ... slowing" construction in detail
        named.loc[fallback] = [
            bool(ABN_DUE.search(t) and slowing_named_as_abnormality(t)) for t in body[fallback]
        ]

    physio = pd.Series([physiologic_slowing(t) for t in body], index=m.index)

    # ---- the SAP labels ----
    slowing_focal = has_foc & is_abn                       # focal is ALWAYS pathologic
    gen_path = has_gen & is_abn & named                    # gen pathologic only if listed as abnormality
    gen_phys = has_gen & ~gen_path                         # else physiologic (incl. all normals)
    slowing_positive = slowing_focal | gen_path
    abnormal_no_slowing = is_abn & ~slowing_positive       # abnormal for OTHER reasons (spikes etc.)

    out = pd.DataFrame({
        "eeg_id": m.eeg_id, "patient_id": m.patient_id,
        "clean_normal": clean_norm, "is_abnormal": is_abn,
        "slowing_focal": slowing_focal, "slowing_gen_pathologic": gen_path,
        "slowing_gen_physiologic": gen_phys, "slowing_positive": slowing_positive,
        "abnormal_no_slowing": abnormal_no_slowing,
        "focal_side": m.get("focal_side"), "focal_band": m.get("focal_band"),
        "gen_topography": m.get("gen_topography"), "gen_band": m.get("gen_band"),
        "clean_pair": m.get("clean_pair"), "age": m.get("age"), "sex": m.get("sex"),
        "label_source": src, "slowing_named_in_conclusion": named, "physio_attribution": physio,
    })
    # NORMALISE SEX. The manifest carries TWO encodings: cohort/replacement rows use "F"/"M" while
    # backfill/expansion rows use "Female"/"Male". Any analysis filtering on sex=="F" silently drops
    # ~12.8k recordings. Collapse to F / M / unknown here so nothing downstream can hit that trap.
    if "sex" in out.columns:
        out["sex"] = (out.sex.astype(str).str.strip().str[:1].str.upper()
                        .map({"F": "F", "M": "M"}).fillna("unknown"))
        print("  sex normalised:", dict(out.sex.value_counts()))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)

    n = len(out)
    print(f"wrote {OUT}  ({n:,} recordings)")
    print(f"  label_source: {src.value_counts().to_dict()}")
    print(f"  clean_normal            : {int(clean_norm.sum()):,}")
    print(f"  slowing_positive        : {int(slowing_positive.sum()):,}   <- DETECTION POSITIVES")
    print(f"    focal (always path)   : {int(slowing_focal.sum()):,}")
    print(f"    gen pathologic        : {int(gen_path.sum()):,}")
    print(f"  gen PHYSIOLOGIC         : {int(gen_phys.sum()):,}   <- were being mislabelled pathologic")
    print(f"  abnormal_no_slowing     : {int(abnormal_no_slowing.sum()):,}   <- own stratum (not normal, not positive)")
    bad = int((clean_norm & slowing_positive).sum())
    print(f"  SANITY clean_normal & slowing_positive = {bad}  (must be 0)")


if __name__ == "__main__":
    main()
