"""Re-derive a CANONICAL, NON-EXCLUSIVE label table for the analyzed cohort, fixing the flag under-count
(a finding is present if its structured-findings cell is any non-empty value — 'report'/'verified'/
'annotation' — not only when it contains 'report'), and join the v2 report-text labels (side/region/band)
+ demographics. Also emits label counts and count-vs-age curves.

Outputs:
  data/derived/labels_canonical.parquet   one row per cohort recording: bdsp_id, age, sex,
      lab_normal, lab_abnormal, lab_focal, lab_gen  (each 0/1, NON-exclusive) + side, region, band
  results/label_counts.md                 counts of every label type
  results/figs/label_inventory.png        count-vs-age curves per label type
"""
from __future__ import annotations
import glob, os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

SC = os.environ.get("PILOT_SCRATCH", "/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad")
FIND = glob.glob(f"{SC}/findings/*_EEG__reports_findings.csv")
FLAGS = {"lab_normal": "normal", "lab_abnormal": "abnormal", "lab_focal": "foc slowing", "lab_gen": "gen slowing"}


def main():
    # 1. corrected, NON-exclusive class flags from the structured findings (present = any non-empty cell)
    fnd = pd.concat([pd.read_csv(f, low_memory=False) for f in FIND], ignore_index=True)
    fnd["pid"] = fnd.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    fnd["date"] = pd.to_datetime(fnd["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    fnd["age"] = pd.to_numeric(fnd.AgeAtVisit, errors="coerce")
    fnd["sex"] = fnd.SexDSC.astype(str)
    for out, col in FLAGS.items():
        v = fnd[col].astype(str).str.lower()
        fnd[out] = (~v.isin(["nan", ""]) & fnd[col].notna()).astype(int)   # any non-empty finding = present
    fnd = fnd.dropna(subset=["date"]).drop_duplicates(["pid", "date"])

    # 2. join v2 report-text labels (side/region/band) — keyed by pid/date via report_extracted_labels
    rep = pd.read_csv("results/report_extracted_labels.csv")
    rep["pid"] = rep.bdsp_id.str.replace(r"^S000\d", "", regex=True)
    rep["date"] = rep.eeg_datetime.astype(str).str[:8]
    lab = fnd.merge(rep[["pid", "date", "bdsp_id", "side", "region", "band", "mentions_slowing"]],
                    on=["pid", "date"], how="inner")
    keep = ["bdsp_id", "age", "sex", *FLAGS.keys(), "side", "region", "band", "mentions_slowing"]
    lab = lab[keep].drop_duplicates("bdsp_id")
    Path("data/derived").mkdir(parents=True, exist_ok=True)
    lab.to_parquet("data/derived/labels_canonical.parquet")

    # 3. counts
    L = ["# Canonical label counts (analyzed cohort, corrected non-exclusive flags)\n",
         f"\nCohort recordings: **{len(lab)}**\n\n## Class flags (NON-exclusive)\n"]
    for out, col in FLAGS.items():
        L.append(f"- {out.replace('lab_','')}: **{int(lab[out].sum())}**\n")
    L.append(f"- clean normal (normal & not focal & not gen): **{int(((lab.lab_normal==1)&(lab.lab_focal==0)&(lab.lab_gen==0)).sum())}**\n")
    L.append(f"- focal & gen (both): {int(((lab.lab_focal==1)&(lab.lab_gen==1)).sum())}\n")
    L.append("\n## Report-text labels\n")
    L.append(f"- side: {lab.side.value_counts(dropna=False).to_dict()}\n")
    L.append(f"- region: {lab.region.value_counts(dropna=False).to_dict()}\n")
    L.append(f"- band: {lab.band.value_counts(dropna=False).to_dict()}\n")
    # focal resolution
    foc = lab[lab.lab_focal == 1]
    L.append(f"\n## Focal resolution (n={len(foc)})\n")
    L.append(f"- unilateral side: {int(foc.side.isin(['left','right']).sum())} ({100*foc.side.isin(['left','right']).mean():.0f}%)\n")
    L.append(f"- region stated: {int(foc.region.notna().sum())} ({100*foc.region.notna().mean():.0f}%)\n")
    Path("results/label_counts.md").write_text("".join(L))
    print("".join(L))

    # 4. count-vs-age curves
    bins = np.arange(0, 95, 5)
    ctr = (bins[:-1] + bins[1:]) / 2
    panels = [("Class", [("normal", lab.lab_normal == 1, "#4a90e2"), ("focal", lab.lab_focal == 1, "#f5a623"),
                          ("generalized", lab.lab_gen == 1, "#e0568a")]),
              ("Side (focal)", [("left", (lab.lab_focal == 1) & (lab.side == "left"), "#4a90e2"),
                                ("right", (lab.lab_focal == 1) & (lab.side == "right"), "#e0568a"),
                                ("bilateral", (lab.lab_focal == 1) & (lab.side == "bilateral"), "#8798b3")]),
              ("Region (focal)", [(r, (lab.lab_focal == 1) & (lab.region == r), c) for r, c in
                                  [("temporal", "#f5a623"), ("frontal", "#4a90e2"), ("central", "#35e0c4"),
                                   ("parietal", "#e0568a"), ("occipital", "#9b59b6")]]),
              ("Band (slowing)", [("delta", lab.band == "delta", "#4a90e2"), ("theta", lab.band == "theta", "#f5a623"),
                                  ("mixed", lab.band == "mixed", "#35e0c4")])]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax, (title, series) in zip(axes.ravel(), panels):
        for name, mask, color in series:
            a = lab.loc[mask, "age"].dropna()
            h, _ = np.histogram(a, bins=bins)
            ax.plot(ctr, h, color=color, label=f"{name} (n={int(mask.sum())})", lw=2)
        ax.set_title(title); ax.set_xlabel("age (years)"); ax.set_ylabel("recordings"); ax.legend(fontsize=8); ax.grid(alpha=.25)
    fig.suptitle("Label availability vs age (analyzed cohort)", fontsize=13)
    fig.tight_layout()
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.savefig("results/figs/label_inventory.png", dpi=110, bbox_inches="tight")
    print("wrote results/figs/label_inventory.png")


if __name__ == "__main__":
    main()
