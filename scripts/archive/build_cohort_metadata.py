"""Build the committed cohort metadata CSV -> metadata/cohort_metadata.csv.

One row per recording, enough to regenerate Table 1 and the growth curves without touching S3:
  bdsp_id, session, eeg_datetime, label, age, age_valid, sex

age comes from the .mat files; sex is filled by scripts/07_pull_sex_omop.py once OMOP is reachable
(left blank until then). Run: python scripts/build_cohort_metadata.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from morgoth_slowing.io import segments

OUT = Path("metadata/cohort_metadata.csv")
LABELS = {"normal": "normal", "focal_slow": "focal_slow", "general_slow": "general_slow"}


def main():
    df = segments.load_metadata({"data": {"local": {"raw": "data/raw"}}}, with_age=True)
    sex_path = Path("data/derived/sex.parquet")
    if sex_path.exists():
        sex = pd.read_parquet(sex_path)[["bdsp_id", "sex"]].drop_duplicates("bdsp_id")
        df = df.merge(sex, on="bdsp_id", how="left")
    else:
        df["sex"] = pd.NA  # pending OMOP (scripts/07_pull_sex_omop.py)

    df["age_valid"] = df.age.between(0, 120)
    out = (df[["bdsp_id", "session", "eeg_datetime", "label", "age", "age_valid", "sex"]]
             .sort_values(["label", "bdsp_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} rows")
    print(out.label.value_counts().to_string())
    print("sex filled:", int(out.sex.notna().sum()), "/", len(out))


if __name__ == "__main__":
    main()
