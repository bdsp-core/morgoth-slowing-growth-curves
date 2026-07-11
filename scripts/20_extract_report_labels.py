"""Extract slowing labels (band, side, region, normal/abnormal) from the free-text EEG reports,
with full provenance, and evaluate our statements against them.

Source (kept LOCAL, not committed — sensitive text):
  Box: Brandon - PHI/Datasets/BDSP_deID/<site>/data_Unstructured/EEG_Reports_OtherSourceFiles/EEGs_And_Reports.csv
  (per-note originals: .../I0001_Neurology_Reports_1/<year>.zip, named by ReportName)

We PUBLISH the derived labels (results/report_extracted_labels.csv) — one row per recording with
the extracted labels + `source_note_name` + `source_box_path` for traceability. NOTE: the earlier
"raw text is NOT committed" rule was superseded 2026-07 — the reports are BDSP de-identified and MBW
confirmed the exposure is not reportable under the IRB/DUA, so de-id report text may be committed
(see docs/analysis_plan.md §11). This script still reads from the local source.

Run: python scripts/20_extract_report_labels.py <EEGs_And_Reports.csv> [site]
"""
from __future__ import annotations
import sys, re, importlib.util
from pathlib import Path
import numpy as np, pandas as pd

RES = Path("results")
BOX_SRC = ("Brandon - PHI/Datasets/BDSP_deID/I0001-MGB/data_Unstructured/"
           "EEG_Reports_OtherSourceFiles/EEGs_And_Reports.csv")
BOX_NOTES = "Brandon - PHI/Datasets/BDSP_deID/I0001-MGB/data_Unstructured/I0001_Neurology_Reports_1/<year>.zip"

# report parser now lives in src (lifted from the legacy scripts/18)
import sys as _sys; _sys.path.insert(0, "src")
from morgoth_slowing.report.parse import parse_report


# --- improved laterality/region extraction (v2) --------------------------------------------------
# The old parser (scripts/18 parse_report) restricted to sentences containing "slow", checked
# bilateral/diffuse FIRST (so any diffuse comment hijacked an explicit side), and ignored electrode
# names + R>L/L>R predominance. That dumped ~81% of slowing reports into "bilateral" and lost ~32k
# clearly-sided reports. v2 scopes per slowing-clause, maps 10-20 electrodes to a side/region, honors
# predominance, and lets a specific unilateral focal finding win over a diffuse background comment.
L_ELEC = r"\b(fp1|f7|f3|t1|t3|t5|c3|p3|o1|a1)\b"
R_ELEC = r"\b(fp2|f8|f4|t2|t4|t6|c4|p4|o2|a2)\b"
_REGION_PATS = [("temporal", r"temporal|\b(t1|t2|t3|t4|t5|t6|f7|f8)\b"),
                ("occipital", r"occipital|\b(o1|o2)\b"),
                ("parietal", r"parietal|\b(p3|p4)\b"),
                ("posterior", r"posterior"),        # reports often say "posterior" not occipital/parietal
                ("anterior", r"anterior"),
                ("frontal", r"frontal|\b(fp1|fp2|f3|f4)\b"),
                ("central", r"central|\b(c3|c4|cz)\b")]

# Coverage/label taxonomy = 4 regions (MBW 2026-07-11): occipital-theta focal slowing is genuinely rare
# (~113 in the whole 217k pool), so occipital+parietal+"posterior" fold into POSTERIOR; "anterior" -> frontal.
REGION4 = {"temporal": "temporal", "central": "central", "frontal": "frontal", "anterior": "frontal",
           "occipital": "posterior", "parietal": "posterior", "posterior": "posterior"}


def extract_region4(text):
    r = extract_region(text)
    return REGION4.get(r, r)


def _clauses(text):
    return [s for s in re.split(r"[.;\n)]|\d\)", (text or "").lower()) if "slow" in s]


def side_of(c):
    if re.search(r"\br\s*>\s*l\b", c): return "right"
    if re.search(r"\bl\s*>\s*r\b", c): return "left"
    hasL = bool(re.search(r"\bleft\b", c) or re.search(L_ELEC, c))
    hasR = bool(re.search(r"\bright\b", c) or re.search(R_ELEC, c))
    diffuse = bool(re.search(r"\b(bilateral|diffuse|generali[sz]ed|both hemisph|bihemispheric|independent)\b", c))
    if hasL and hasR: return "bilateral"
    if hasL: return "left"
    if hasR: return "right"
    if diffuse: return "bilateral"
    return None


def extract_side(text):
    sides = [s for s in (side_of(c) for c in _clauses(text)) if s]
    uni = [s for s in sides if s in ("left", "right")]
    if uni and len(set(uni)) == 1: return uni[0]         # consistent single side across findings
    if uni: return "bilateral"                            # left AND right foci -> bilateral/multifocal
    if sides: return "bilateral"
    return None


def extract_band(text):
    cl = _clauses(text)
    if not cl:
        return None
    ctx = " ".join(cl)
    hd, ht = bool(re.search(r"delta", ctx)), bool(re.search(r"theta", ctx))
    return "mixed" if (hd and ht) else ("delta" if hd else ("theta" if ht else None))


def extract_region(text):
    regs = []
    for c in _clauses(text):
        for name, pat in _REGION_PATS:
            if re.search(pat, c):
                regs.append(name); break
    if not regs: return None
    return max(set(regs), key=regs.count)                # most-mentioned region across slowing clauses


def parse_full(text):
    d = parse_report(text)
    t = (text or "").lower()
    d["side"] = extract_side(text)                        # v2 overrides the old side/region/band
    d["region"] = extract_region(text)
    d["band"] = extract_band(text)
    d["report_normal"] = int(bool(re.search(r"\bnormal (eeg|study|awake)|this is a normal\b", t)) and
                             not re.search(r"abnormal", t))
    d["report_abnormal"] = int(bool(re.search(r"\babnormal\b", t)))
    return d


def main(csv, site="I0001"):
    cols = ["SiteID", "BDSPPatientID", "StartTime", "ReportName", "impression", "reports"]
    df = pd.read_csv(csv, usecols=lambda c: c in cols, low_memory=False, dtype=str)
    df["text"] = df.get("impression", "").fillna("") + " || " + df.get("reports", "").fillna("")
    parsed = df.text.map(parse_full)
    P = pd.json_normalize(parsed)
    df = pd.concat([df.reset_index(drop=True), P], axis=1)
    df["pid"] = df.BDSPPatientID.str.replace(r"\.0$", "", regex=True)  # strip float ".0" suffix
    df["date"] = pd.to_datetime(df.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    df = df.dropna(subset=["date"]).drop_duplicates(["pid", "date"])

    # join to cohort
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["pid"] = meta.bdsp_id.str.replace(r"^S000\d", "", regex=True); meta["date"] = meta.eeg_datetime.str[:8]
    j = meta.merge(df, on=["pid", "date"], how="inner")
    print(f"cohort recordings matched to a report with text: {len(j)} / {len(meta)}")
    print("report mentions slowing:", int(j.mentions_slowing.sum()),
          "| band stated:", int(j.band.notna().sum()),
          "| side stated:", int(j.side.notna().sum()), "| region stated:", int(j.region.notna().sum()))

    # publish derived labels + provenance
    out = j[["bdsp_id", "eeg_datetime", "label", "mentions_slowing", "band", "side", "region",
             "report_normal", "report_abnormal"]].copy()
    out["source_note_name"] = j.ReportName.values
    out["source_box_path"] = BOX_SRC
    out["source_note_archive"] = BOX_NOTES
    out.to_csv(RES / "report_extracted_labels.csv", index=False)
    print("wrote results/report_extracted_labels.csv", out.shape)

    # evaluate OUR statements vs report (where report states band/side/region)
    fr = pd.read_parquet("data/derived/final_report.parquet")
    ours = fr.report.map(parse_report); O = pd.json_normalize(ours); O["bdsp_id"] = fr.bdsp_id.values
    cmp = j.merge(O, on="bdsp_id", suffixes=("_rep", "_ours"))
    lines = ["\n## band/location agreement (our generated statement vs report), where report states it\n"]
    for k in ["band", "side", "region"]:
        both = cmp.dropna(subset=[f"{k}_rep", f"{k}_ours"])
        acc = (both[f"{k}_rep"] == both[f"{k}_ours"]).mean() if len(both) else float("nan")
        lines.append(f"- {k}: agreement {acc:.3f} on n={len(both)}\n")
    print("".join(lines))
    with open(RES / "report_agreement.md", "a") as fh:
        fh.write("\n## Part B — band/location from report TEXT (source: Box "
                 f"{BOX_SRC})\n" + "".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "I0001")
