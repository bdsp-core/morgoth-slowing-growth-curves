"""Generate Table 1 (cohort characteristics) with tableone -> docs/table1.md + README.

Uses age (embedded in the .mat files) + label (folder). Sex is added once available from OMOP
(scripts/05b or io.omop). Run: python scripts/make_table1.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from tableone import TableOne

from morgoth_slowing.io import segments

LABELS = {"normal": "Normal", "focal_slow": "Focal slowing", "general_slow": "Generalized slowing"}
BINS = [0, 2, 5, 12, 17, 29, 44, 59, 74, 120]
BAND_LABELS = ["0-2", "3-5", "6-12", "13-17", "18-29", "30-44", "45-59", "60-74", "75+"]


def build(raw_root="data/raw", sex_table: pd.DataFrame | None = None) -> TableOne:
    df = segments.load_metadata({"data": {"local": {"raw": raw_root}}}, with_age=True)
    df["Age (years)"] = df.age.where((df.age >= 0) & (df.age <= 120))  # drop impossible ages
    df["Group"] = df.label.map(LABELS)
    df["Age band"] = pd.cut(df["Age (years)"], bins=BINS, labels=BAND_LABELS, include_lowest=True)

    columns = ["Age (years)", "Age band"]
    categorical = ["Age band"]
    if sex_table is not None:  # sex_table: person_id -> Sex
        df = df.merge(sex_table, on="person_id", how="left")
        columns.append("Sex")
        categorical.append("Sex")

    return TableOne(df, columns=columns, categorical=categorical, groupby="Group",
                    nonnormal=["Age (years)"], pval=False, missing=True)


def main():
    t = build()
    out = Path("docs/table1.md")
    out.write_text("# Table 1. Cohort characteristics\n\n" + t.tabulate(tablefmt="github") + "\n")
    print(t.tabulate(tablefmt="github"))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
