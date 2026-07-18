#!/usr/bin/env python3
"""SAP companion adapter #6 — extend scores_v2 with the AMOUNT / BURDEN / PREVALENCE descriptors that
scripts/50 (severity_prevalence.png) and the severity null-result figures consume.

Source = data/derived/description_descriptors.parquet (scripts/107 deviation field, SAP §7.2), which is
itself built from the new segment_master. Per recording we take the ACCENTUATED stage's descriptors
(the stage that most accentuates the slowing, SAP §7.2 item 6):
  peak_z     = amount_p90     (robust amount; the old peak_z was a MAX over segments -> artifact-dominated)
  burden     = amount_median  (median SD deviation)
  prevalence = prevalence     (% of that stage's segments above the normal 95th centile)
plus accentuated_stage + label. Writes data/derived/scores_v2.parquet.

Run: PYTHONPATH=src python scratchpad/adapter_scores_v2_full.py
"""
import numpy as np, pandas as pd

REPO = "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
DER = f"{REPO}/data/derived"


def main():
    d = pd.read_parquet(f"{DER}/description_descriptors.parquet")
    lu = pd.read_parquet(f"{DER}/labels_unified.parquet")[["bdsp_id", "label"]].drop_duplicates("bdsp_id")
    # the recording's descriptors = those of its accentuated stage
    acc = d[d.stage == d.accentuated_stage].drop_duplicates("bdsp_id")
    if acc.empty:                                   # fallback: max-amount stage
        acc = d.sort_values("amount_p90").drop_duplicates("bdsp_id", keep="last")
    s = pd.DataFrame({
        "bdsp_id": acc.bdsp_id.values,
        "accentuated_stage": acc.accentuated_stage.values,
        "peak_z": acc.amount_p90.values,           # robust amount (SD)
        "burden": acc.amount_median.values,
        "prevalence": acc.prevalence.values,
        "longest_run_min": acc.longest_run_min.values,
        "focal_side": acc.focal_side.values,
        "sleep_only": acc.sleep_only.values,
    }).merge(lu, on="bdsp_id", how="left")
    s.to_parquet(f"{DER}/scores_v2.parquet", index=False)
    print(f"scores_v2 {s.shape}")
    print(s.groupby("label")[["peak_z", "burden", "prevalence"]].median().round(3).to_string())
    print("\naccentuated_stage (abnormal):")
    print(s[s.label.isin(["focal_slow", "general_slow"])].accentuated_stage.value_counts().to_string())


if __name__ == "__main__":
    main()
