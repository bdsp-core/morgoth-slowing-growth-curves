"""Extract slowing labels (band, side, region, normal/abnormal) from the free-text EEG reports,
with full provenance, and evaluate our statements against them.

Source (kept LOCAL, not committed — sensitive text):
  Box: Brandon - PHI/Datasets/BDSP_deID/<site>/data_Unstructured/EEG_Reports_OtherSourceFiles/EEGs_And_Reports.csv
  (per-note originals: .../I0001_Neurology_Reports_1/<year>.zip, named by ReportName)

We PUBLISH only the derived labels (results/report_extracted_labels.csv) — one row per recording with
the extracted labels + `source_note_name` + `source_box_path` for traceability. Raw text is NOT
committed.

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

# reuse the report parser from scripts/18
_spec = importlib.util.spec_from_file_location("r18", "scripts/18_report_agreement.py")
_m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
parse_report = _m.parse_report


def parse_full(text):
    d = parse_report(text)
    t = (text or "").lower()
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
