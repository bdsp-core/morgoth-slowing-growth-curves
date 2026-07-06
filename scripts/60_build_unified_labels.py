"""Build the UNIFIED label table for the whole cohort, re-derived from raw reports + structured
findings, with provenance. Replaces the scattered logic in scripts 18/20/52.

One row per recording:
  Identity     bdsp_id, site, pid, eeg_datetime, age, sex
  Report link  has_report, report_note_name, n_report_chars
  Class        is_normal, is_abnormal, has_focal_slow, has_gen_slow  (0/1, non-exclusive)
               group ∈ {normal, abnormal, no_report}
               clean_normal (0/1), report_stratum ∈ {N, A0, Ag, Af}
  Focal        focal_band, focal_side, focal_region
  Generalized  gen_band, gen_topography{anterior,posterior,unspec}, gen_state{wake,sleep,unspec},
               gen_class{pathologic,physiologic,none}, p_gen_pathologic
  Provenance   class_source{finding_flag,report_text,both}, focal_trigger, gen_trigger

Outputs:
  data/derived/labels_unified.parquet + results/labels_unified.csv
  results/label_diff.md        how the new labels differ from the current ones
  results/label_coverage.md     coverage of every label across the 12,379 cohort
Run: python scripts/60_build_unified_labels.py
"""
from __future__ import annotations
import re, glob, json, importlib.util
from pathlib import Path
import numpy as np, pandas as pd, joblib

DER = Path("data/derived"); RES = Path("results")
REP = "data/reports_raw/MGB_EEGs_And_Reports.csv"

# reuse v2 focal extractors (side/region/band) from scripts/20
_s20 = importlib.util.spec_from_file_location("s20", "scripts/20_extract_report_labels.py")
s20 = importlib.util.module_from_spec(_s20); _s20.loader.exec_module(s20)
# reuse cue lexicons + gen-slowing detector from scripts/61
_s61 = importlib.util.spec_from_file_location("s61", "scripts/61_build_gen_labeling_set.py")
s61 = importlib.util.module_from_spec(_s61); _s61.loader.exec_module(s61)

FLAGS = {"nrm_flag": "normal", "abn_flag": "abnormal", "foc_flag": "foc slowing", "gen_flag": "gen slowing"}


def imp_normal(imp):
    """Normal impression = ground-truth normal (Brandon's rule), BUT guard the truncated
    'ABnormal eeg ... due to [findings]' artifact where 'abnormal' was cut to 'normal'. A genuine
    normal impression states a reason for abnormality via 'due to' — so 'normal ... due to' (in any
    word order) is a corrupted abnormal, not a normal."""
    t = (imp or "").lower()
    if re.search(r"\babnormal\b", t):
        return False
    # truncated-abnormal: 'normal ... <reason connector> [findings]' within the same clause
    if re.search(r"\bnormal\b[^.]{0,70}\b(due to|because of|secondary to|caused by|attributable to)\b", t):
        return False
    return bool(re.search(r"\bnormal (eeg|study|awake)|within normal limits|this is a normal\b", t))


# ---- generalized topography (anterior/posterior) + state (wake/sleep), from gen/diffuse clauses ----
def _gen_clauses(text):
    return [c for c in re.split(r"[.;\n]", (text or "").lower())
            if "slow" in c and re.search(r"gener|diffuse|bilateral|background", c)]

def gen_topography(text):
    ctx = " ".join(_gen_clauses(text))
    ant = bool(re.search(r"anterior|frontal|firda|frontally predominant", ctx))
    post = bool(re.search(r"posterior|occipital|oirda|posteriorly predominant", ctx))
    return "anterior" if (ant and not post) else ("posterior" if (post and not ant) else "unspec")

def gen_state(text):
    ctx = " ".join(_gen_clauses(text))
    wake = bool(re.search(r"\bawake|wakefulness|while awake", ctx))
    sleep = bool(re.search(r"drows|asleep|\bsleep\b|somnolen", ctx))
    return "wake" if (wake and not sleep) else ("sleep" if (sleep and not wake) else "unspec")

def gen_trigger(text):
    c = _gen_clauses(text)
    return re.sub(r"\s+", " ", c[0])[:160] if c else ""

def focal_trigger(text):
    c = [s for s in re.split(r"[.;\n]", (text or "").lower())
         if "slow" in s and not re.search(r"gener|diffuse|bilateral", s)]
    return re.sub(r"\s+", " ", c[0])[:160] if c else ""


def main():
    # ---------- sources ----------
    rep = pd.read_csv(REP, usecols=lambda c: c in
                      ["SiteID", "BDSPPatientID", "StartTime", "ReportName", "impression", "reports"],
                      low_memory=False, dtype=str)
    rep["pid"] = rep.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    rep["date"] = pd.to_datetime(rep.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    rep["impression"] = rep.impression.fillna(""); rep["reports"] = rep.reports.fillna("")
    rep = rep.dropna(subset=["date"]).drop_duplicates(["pid", "date"])

    fnd = pd.concat([pd.read_csv(f, low_memory=False, dtype=str)
                     for f in glob.glob("data/findings/S000*_EEG__reports_findings.csv")], ignore_index=True)
    fnd["pid"] = fnd.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    fnd["date"] = pd.to_datetime(fnd["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    for out, col in FLAGS.items():
        fnd[out] = (~fnd[col].astype(str).str.lower().isin(["nan", ""])).astype(int)
    fnd = fnd.dropna(subset=["date"]).drop_duplicates(["pid", "date"])

    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["pid"] = meta.bdsp_id.str.replace(r"^S000\d", "", regex=True); meta["date"] = meta.eeg_datetime.str[:8]
    meta["site"] = np.where(meta.bdsp_id.str.startswith("S0001"), "MGH", "BWH")

    df = meta.merge(rep, on=["pid", "date"], how="left").merge(
        fnd[["pid", "date", *FLAGS]], on=["pid", "date"], how="left")
    for c in FLAGS: df[c] = df[c].fillna(0).astype(int)
    df["has_report"] = df.impression.notna() & (df.impression.fillna("").str.len() > 0) | \
                       df.reports.fillna("").str.len().gt(0)
    df["impression"] = df.impression.fillna(""); df["reports"] = df.reports.fillna("")
    df["full"] = (df.impression + " || " + df.reports)
    df["n_report_chars"] = df.full.str.len()

    # ---------- class reconciliation ----------
    df["imp_normal"] = df.impression.map(imp_normal)
    df["text_abnormal"] = df.full.str.contains(r"\babnormal\b", case=False, regex=True)
    df["gen_text"] = df.full.str.contains(s61.GEN_SLOW_TEXT).fillna(False)
    df["foc_text"] = df.full.str.contains(
        r"focal[^.;]{0,30}slow|slow[^.;]{0,30}focal|(?:left|right|[lr]\s*>\s*[lr])[^.;]{0,40}slow", case=False, regex=True).fillna(False)

    has_rep = df.has_report
    # Trust the INDEPENDENT structured abnormal/focal flags over a possibly-truncated 'normal'
    # impression (the 'ABnormal eeg ... [findings]' -> 'normal ...' corruption). A genuine normal
    # impression may still carry a physiologic GENERALIZED slowing flag (drowsy/HV), so gen_flag
    # alone does NOT contradict a normal read.
    df["is_abnormal"] = (((df.abn_flag == 1) | df.text_abnormal) & has_rep).astype(int)
    trusted_normal = df.imp_normal & (df.abn_flag == 0) & (df.foc_flag == 0) & has_rep
    df["is_normal"] = ((trusted_normal | ((df.nrm_flag == 1) & (df.is_abnormal == 0))) & has_rep).astype(int)
    df.loc[df.is_abnormal == 1, "is_normal"] = 0                      # abnormal wins ties

    df["has_focal_slow"] = (((df.foc_flag == 1) | df.foc_text) & has_rep & ~trusted_normal).astype(int)
    df["has_gen_slow"] = (((df.gen_flag == 1) | df.gen_text) & has_rep).astype(int)

    # gen_class from the distilled classifier (physiologic vs pathologic); 'none' where no gen slowing.
    # A trusted-normal impression forces its generalized slowing to physiologic (ground-truth rule).
    gen = df.has_gen_slow == 1
    clf = joblib.load("models/gen_classifier.joblib")
    text = (df.impression + " . " + df.reports).str.lower().map(lambda t: re.sub(r"\s+", " ", t)[:4000])
    p = clf["model"].predict_proba(text)[:, 1] if clf["kind"] == "text" else \
        clf["model"].predict_proba(df[clf["cues"]].fillna(0).astype(float).values)[:, 1]
    p = np.where(trusted_normal, np.minimum(p, 0.05), p)
    df["p_gen_pathologic"] = np.where(gen, p.round(3), np.nan)
    df["gen_class"] = np.where(gen, np.where(p >= 0.5, "pathologic", "physiologic"), "none")

    # clean-normal = reader-normal with NO pathological finding. Physiologic generalized slowing is
    # allowed (it is the expected drowsy/HV finding in a normal study); pathologic gen or any focal is not.
    df["clean_normal"] = ((df.is_normal == 1) & (df.is_abnormal == 0) & (df.has_focal_slow == 0) &
                          ~((df.has_gen_slow == 1) & (df.gen_class == "pathologic"))).astype(int)
    df["group"] = np.where(~has_rep, "no_report",
                    np.where(df.clean_normal == 1, "normal", "abnormal"))
    df["report_stratum"] = np.where(~has_rep, "none",
                            np.where(df.clean_normal == 1, "N",
                              np.where(df.has_focal_slow == 1, "Af",
                                np.where((df.has_gen_slow == 1) & (df.gen_class == "pathologic"), "Ag", "A0"))))

    # class provenance
    def src(r):
        f = (r.foc_flag or r.gen_flag or r.abn_flag or r.nrm_flag)
        t = (r.foc_text or r.gen_text or r.text_abnormal or r.imp_normal)
        return "both" if (f and t) else ("finding_flag" if f else ("report_text" if t else "none"))
    df["class_source"] = df.apply(src, axis=1)

    # ---------- focal detail ----------
    foc = df.has_focal_slow == 1
    df["focal_band"] = np.where(foc, df.full.map(s20.extract_band), None)
    df["focal_side"] = np.where(foc, df.full.map(s20.extract_side), None)
    df["focal_region"] = np.where(foc, df.full.map(s20.extract_region), None)
    df["focal_trigger"] = np.where(foc, df.full.map(focal_trigger), "")

    # ---------- generalized detail (topography/state/band) ----------
    df["gen_band"] = np.where(gen, df.full.map(s20.extract_band), None)
    df["gen_topography"] = np.where(gen, df.full.map(gen_topography), None)
    df["gen_state"] = np.where(gen, df.full.map(gen_state), None)
    df["gen_trigger"] = np.where(gen, df.full.map(gen_trigger), "")

    # ---------- emit ----------
    cols = ["bdsp_id", "site", "pid", "eeg_datetime", "age", "sex", "has_report", "ReportName",
            "n_report_chars", "is_normal", "is_abnormal", "has_focal_slow", "has_gen_slow",
            "group", "clean_normal", "report_stratum", "focal_band", "focal_side", "focal_region",
            "gen_band", "gen_topography", "gen_state", "gen_class", "p_gen_pathologic",
            "class_source", "focal_trigger", "gen_trigger"]
    df["age"] = df.get("age"); out = df.rename(columns={"ReportName": "report_note_name"})
    cols = [c if c != "ReportName" else "report_note_name" for c in cols]
    U = out[[c for c in cols if c in out.columns]].copy()
    DER.mkdir(parents=True, exist_ok=True)
    U.to_parquet(DER / "labels_unified.parquet")
    U.drop(columns=["focal_trigger", "gen_trigger"]).to_csv(RES / "labels_unified.csv", index=False)
    # evidence sidecar (provenance triggers)
    with open(DER / "labels_unified_evidence.jsonl", "w") as fh:
        for r in out.itertuples():
            if r.has_focal_slow or r.has_gen_slow:
                fh.write(json.dumps({"bdsp_id": r.bdsp_id, "focal_trigger": r.focal_trigger,
                                     "gen_trigger": r.gen_trigger}) + "\n")
    print(f"wrote labels_unified: {len(U)} recordings")

    # ---------- legacy report_extracted_labels.csv (keeps report panels 18/35/37/39/40-46 working) ----------
    # side/region/band from the SAME v2 extractors on full text (unchanged); label = corrected semantics
    # (general_slow = PATHOLOGIC generalized only, matching scripts/53).
    def corrected(r):
        if r.clean_normal == 1: return "normal"
        if r.has_focal_slow == 1: return "focal_slow"
        if r.has_gen_slow == 1 and r.gen_class == "pathologic": return "general_slow"
        if r.is_abnormal == 1: return "other_abnormal"
        return "unknown"
    leg = pd.DataFrame({
        "bdsp_id": df.bdsp_id, "eeg_datetime": df.eeg_datetime,
        "label": df.apply(corrected, axis=1),
        "mentions_slowing": df.full.str.contains("slow", case=False),
        "band": df.full.map(s20.extract_band), "side": df.full.map(s20.extract_side),
        "region": df.full.map(s20.extract_region),
        "report_normal": df.is_normal.astype(int), "report_abnormal": df.is_abnormal.astype(int),
    })
    leg["source_note_name"] = df.ReportName.values
    leg = leg[df.has_report.values]  # only recordings with a report
    leg.to_csv(RES / "report_extracted_labels.csv", index=False)
    print(f"wrote results/report_extracted_labels.csv ({len(leg)} rows, new labels)")

    write_coverage(U)
    write_diff(U)


def write_coverage(U):
    n = len(U)
    L = [f"# Unified label coverage (cohort n={n})\n\n"]
    hr = int(U.has_report.sum())
    L.append(f"- has matching report: **{hr}** ({100*hr/n:.1f}%) | no_report: {n-hr}\n\n## Groups\n")
    for g, c in U.group.value_counts().items(): L.append(f"- {g}: {c} ({100*c/n:.0f}%)\n")
    L.append("\n## Report strata\n")
    for s, c in U.report_stratum.value_counts().items(): L.append(f"- {s}: {c}\n")
    L.append(f"\n## Class flags (non-exclusive)\n")
    for c in ["is_normal", "is_abnormal", "has_focal_slow", "has_gen_slow", "clean_normal"]:
        L.append(f"- {c}: {int(U[c].sum())}\n")
    foc = U[U.has_focal_slow == 1]
    L.append(f"\n## Focal resolution (n={len(foc)})\n")
    L.append(f"- band stated: {int(foc.focal_band.notna().sum())} ({100*foc.focal_band.notna().mean():.0f}%) {foc.focal_band.value_counts().to_dict()}\n")
    L.append(f"- side stated: {int(foc.focal_side.notna().sum())} ({100*foc.focal_side.notna().mean():.0f}%) {foc.focal_side.value_counts().to_dict()}\n")
    L.append(f"- region stated: {int(foc.focal_region.notna().sum())} ({100*foc.focal_region.notna().mean():.0f}%) {foc.focal_region.value_counts().to_dict()}\n")
    gen = U[U.has_gen_slow == 1]
    L.append(f"\n## Generalized resolution (n={len(gen)})\n")
    L.append(f"- gen_class: {gen.gen_class.value_counts().to_dict()}\n")
    L.append(f"- topography: {gen.gen_topography.value_counts(dropna=False).to_dict()}\n")
    L.append(f"- state: {gen.gen_state.value_counts(dropna=False).to_dict()}\n")
    L.append(f"- band: {gen.gen_band.value_counts(dropna=False).to_dict()}\n")
    (RES / "label_coverage.md").write_text("".join(L))
    print("wrote results/label_coverage.md")


def write_diff(U):
    """Compare the unified labels to the current canonical labels + old report-text labels."""
    L = ["# Label diff — unified (new) vs current\n\n"]
    U2 = U.set_index("bdsp_id")
    # vs labels_canonical.parquet (class flags + clean normal)
    try:
        old = pd.read_parquet(DER / "labels_canonical.parquet").drop_duplicates("bdsp_id").set_index("bdsp_id")
        j = U2.join(old[["lab_normal", "lab_abnormal", "lab_focal", "lab_gen", "side", "region", "band"]],
                    how="inner", rsuffix="_old")
        L.append(f"## vs labels_canonical.parquet (n={len(j)} shared)\n\n")
        old_cn = int(((j.lab_normal == 1) & (j.lab_focal == 0) & (j.lab_gen == 0)).sum())
        L.append(f"- clean-normal: old **{old_cn}** → new **{int(j.clean_normal.sum())}** "
                 f"(Δ {int(j.clean_normal.sum())-old_cn:+d})\n")
        for new_c, old_c, name in [("has_focal_slow", "lab_focal", "focal"), ("has_gen_slow", "lab_gen", "generalized")]:
            flipped = int((j[new_c] != j[old_c]).sum())
            L.append(f"- {name}: {int(j[old_c].sum())} → {int(j[new_c].sum())} "
                     f"({flipped} recordings changed flag)\n")
        # side/region/band changes among focal
        for k in ["side", "region", "band"]:
            nk = {"side": "focal_side", "region": "focal_region", "band": "focal_band"}[k]
            both = j[j[nk].notna() & j[k].notna()]
            chg = int((both[nk] != both[k]).sum())
            L.append(f"- focal {k}: {chg}/{len(both)} changed vs old (new resolves "
                     f"{int(j[nk].notna().sum())} total)\n")
    except Exception as e:
        L.append(f"(labels_canonical compare skipped: {e})\n")
    # the new generalized phys/path split — brand new information
    gen = U[U.has_gen_slow == 1]
    L.append(f"\n## New: generalized phys/path split (n={len(gen)})\n")
    L.append(f"- pathologic **{int((gen.gen_class=='pathologic').sum())}** "
             f"({100*(gen.gen_class=='pathologic').mean():.0f}%), physiologic "
             f"**{int((gen.gen_class=='physiologic').sum())}** — the old labels called ALL of these "
             f"'generalized slowing' with no physiologic/pathologic distinction.\n")
    (RES / "label_diff.md").write_text("".join(L))
    print("wrote results/label_diff.md")


if __name__ == "__main__":
    main()
