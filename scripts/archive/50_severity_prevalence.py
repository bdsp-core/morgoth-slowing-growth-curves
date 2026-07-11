"""Severity-grading & prevalence/persistence agreement vs report adjectives (Brandon's ② list, final 2).

Parses the report text's severity words (mild/moderate/marked/severe) and frequency/prevalence words
(rare/occasional/intermittent/frequent/abundant/continuous) from the slowing sentences, maps them to
ordinal scales, and correlates with our quantitative scores (peak z / burden ; prevalence / run-length).
Writes results/severity_prevalence.md + results/figs/severity_prevalence.png.
Run: PYTHONPATH=src python scripts/50_severity_prevalence.py
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

REPORTS = "/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad/reports/EEGs_And_Reports.csv"
SEV = [("marked", 3), ("severe", 3), ("moderate", 2), ("mild", 1), ("slight", 1)]
FRQ = [("continuous", 4), ("abundant", 3), ("frequent", 3), ("intermittent", 2), ("occasional", 1), ("rare", 1)]


def ordinal(text, table):
    segs = [s for s in re.split(r"[.;\n]", text.lower()) if "slow" in s]
    ctx = " ".join(segs)
    for w, v in table:
        if w in ctx:
            return v
    return np.nan


def main():
    use = ["SiteID", "BDSPPatientID", "reports", "impression", "slowing"]
    rows = []
    for ch in pd.read_csv(REPORTS, usecols=use, chunksize=100000, dtype=str, low_memory=False):
        t = (ch.reports.fillna("") + " " + ch.impression.fillna(""))
        m = t.str.contains("slow", case=False)
        if m.any():
            s = ch[m].copy(); s["txt"] = t[m]
            rows.append(s)
    r = pd.concat(rows)
    r["bdsp_id"] = r.SiteID.astype(str) + r.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    r["rep_sev"] = r.txt.map(lambda x: ordinal(x, SEV))
    r["rep_frq"] = r.txt.map(lambda x: ordinal(x, FRQ))
    r = r.dropna(subset=["rep_sev", "rep_frq"], how="all").drop_duplicates("bdsp_id")

    sc = pd.read_parquet("data/derived/scores_v2.parquet")
    df = sc.merge(r[["bdsp_id", "rep_sev", "rep_frq"]], on="bdsp_id", how="inner")
    out = ["# Severity & prevalence agreement vs report adjectives\n",
           f"Matched {len(df)} recordings with a report severity/frequency word.\n"]
    # correlations
    sev = df.dropna(subset=["rep_sev", "peak_z"])
    frq = df.dropna(subset=["rep_frq", "prevalence"])
    rho_s = spearmanr(sev.peak_z, sev.rep_sev).correlation if len(sev) > 20 else np.nan
    rho_p = spearmanr(frq.prevalence, frq.rep_frq).correlation if len(frq) > 20 else np.nan
    rho_b = spearmanr(sev.burden, sev.rep_sev).correlation if len(sev) > 20 else np.nan
    out += [f"- **Severity**: our peak-z vs report severity — Spearman ρ = {rho_s:.3f} (n={len(sev)}); burden vs severity ρ = {rho_b:.3f}",
            f"- **Prevalence**: our %-segments vs report frequency — Spearman ρ = {rho_p:.3f} (n={len(frq)})"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
    if len(sev) > 20:
        sev.boxplot(column="peak_z", by="rep_sev", ax=ax[0]); ax[0].set_title(f"peak-z by report severity (ρ={rho_s:.2f})")
        ax[0].set_xlabel("report severity (1=mild..3=marked)"); ax[0].set_ylabel("our peak z")
    if len(frq) > 20:
        frq.boxplot(column="prevalence", by="rep_frq", ax=ax[1]); ax[1].set_title(f"prevalence by report frequency (ρ={rho_p:.2f})")
        ax[1].set_xlabel("report frequency (1=occasional..4=continuous)"); ax[1].set_ylabel("our %-segments")
    plt.suptitle(""); fig.tight_layout()
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.savefig("results/figs/severity_prevalence.png", dpi=130); plt.close(fig)
    Path("results/severity_prevalence.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
