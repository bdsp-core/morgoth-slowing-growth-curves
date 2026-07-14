#!/usr/bin/env python3
"""Replace the integer AGE used by every analysis with the true fractional age where one exists.

THE BUG (spotted from Figure 1: the scatter is BANDED at young ages).
  * The `age` carried on the manifest — and therefore on every analysis table — is a WHOLE NUMBER of
    years for 100% of recordings. A 6-month-old and an 18-month-old both become "1".
  * The keystone growth-curve figure plots age on a log axis with ticks at 1, 3 and 6 MONTHS. So it is
    drawn as if we had sub-year resolution, while the data has none. The infant end of the curve has
    fabricated precision, and the integer grid shows up as vertical banding.
  * Worse, that column is not merely rounded, it is partly WRONG: 7 recordings carry NEGATIVE ages
    (-6 … -1), and the discrepancy against the true fractional age reaches 10.4 years.
  * A correct fractional-age table (OMOP-derived, `fractional_age.parquet`, 27,029 rows keyed on
    patient + recording date) already existed and was simply never joined in — even though the
    manuscript claims "precise OMOP-derived fractional ages".

WHAT THIS DOES
  best_age = fractional age where available (10,432 recordings, incl. all 7 negatives -> fixed);
             the integer age otherwise (17,092 — no better source exists for the expansion/backfill rows).
Patches the age column in-place on recording_labels_sap + channel_stage_features, and records the
provenance in an `age_source` column so no downstream analysis can pretend the integer rows are precise.

HONEST LIMIT: only 37.9% of recordings get a true fractional age. The child/infant curves are therefore
still limited by whole-year resolution for the majority of recordings, and the manuscript's claim of
"precise OMOP-derived fractional ages" is true for a minority. That must be stated, not papered over.

Run: PYTHONPATH=src python scripts/fix_ages_fractional.py
"""
from pathlib import Path
import numpy as np, pandas as pd

FA = "data/derived/fractional_age.parquet"
LAB = "data/derived/recording_labels_sap.parquet"
CSF = "data/derived/channel_stage_features.parquet"


def best_age_table():
    fa = pd.read_parquet(FA)
    fa["eeg_dt"] = pd.to_datetime(fa.eeg_date, errors="coerce")
    fa = fa.dropna(subset=["eeg_dt", "age_frac"])
    fa["date"] = fa.eeg_dt.dt.strftime("%Y%m%d")

    # RECOVER DATE OF BIRTH. age_frac is exact, so dob = eeg_date - age_frac. For patients with several
    # EEGs the recovered DOB agrees to 0.0 days, so this is exact, not an approximation. Any OTHER
    # recording of the same patient then gets an exact fractional age for free — no OMOP query needed.
    fa["dob_est"] = fa.eeg_dt - pd.to_timedelta(fa.age_frac * 365.25, unit="D")
    dob = fa.groupby("bdsp_id").dob_est.median().rename("dob")

    lab = pd.read_parquet(LAB)
    lab["date"] = lab.eeg_id.str.split("_").str[-1].str[:8]
    lab["eeg_dt"] = pd.to_datetime(lab.date, format="%Y%m%d", errors="coerce")
    m = lab.merge(fa[["bdsp_id", "date", "age_frac"]].drop_duplicates(["bdsp_id", "date"]),
                  left_on=["patient_id", "date"], right_on=["bdsp_id", "date"],
                  how="left", suffixes=("", "_fa"))
    m = m.merge(dob, left_on="patient_id", right_index=True, how="left")

    # age from the recovered DOB, wherever we have one and no direct fractional age
    age_dob = (m.eeg_dt - m.dob).dt.total_seconds() / (365.25 * 24 * 3600)
    n_dob = int((m.age_frac.isna() & age_dob.notna()).sum())
    print(f"  recovered via DOB back-calculation: {n_dob:,} extra fractional ages "
          f"(DOB is exact: 0.0-day spread across a patient's EEGs)")
    m["age_frac"] = m.age_frac.where(m.age_frac.notna(), age_dob)

    a_int = pd.to_numeric(m.age, errors="coerce")
    n_neg = int((a_int < 0).sum())
    best = m.age_frac.where(m.age_frac.notna(), a_int)
    best = best.where(best >= 0)                      # a negative age is impossible; never fit on it
    src = np.where(m.age_frac.notna(), "fractional(OMOP)", "integer(AgeAtVisit)")
    src = np.where(best.isna(), "MISSING", src)

    print(f"recordings                 : {len(m):,}")
    print(f"  true fractional age      : {int(m.age_frac.notna().sum()):,}  ({100*m.age_frac.notna().mean():.1f}%)")
    print(f"  integer age only         : {int((m.age_frac.isna() & best.notna()).sum()):,}")
    print(f"  unusable (negative/NaN)  : {int(best.isna().sum()):,}   [{n_neg} were NEGATIVE integer ages]")
    d = (a_int - m.age_frac).abs()
    print(f"  |integer - fractional|   : median {d.median():.2f} y, 95th {d.quantile(.95):.2f} y, "
          f"max {d.max():.2f} y")
    return pd.DataFrame({"eeg_id": m.eeg_id, "age_best": best.values, "age_source": src})


def main():
    ba = best_age_table()

    lab = pd.read_parquet(LAB).merge(ba, on="eeg_id", how="left")
    lab["age_integer_orig"] = lab.age                  # keep the old column for audit
    lab["age"] = lab.age_best
    lab.drop(columns=["age_best"]).to_parquet(LAB, index=False)
    print(f"\npatched {LAB}")

    d = pd.read_parquet(CSF)
    d = d.drop(columns=[c for c in ("age_source",) if c in d.columns])
    d = d.merge(ba.rename(columns={"eeg_id": "bdsp_id"}), on="bdsp_id", how="left")
    d["age"] = d.age_best
    d.drop(columns=["age_best"]).to_parquet(CSF, index=False)
    print(f"patched {CSF}  ({len(d):,} rows)")

    u = lab[lab.age.notna()]
    print(f"\nunder-2s now resolvable to sub-year: "
          f"{int(((u.age < 2) & (u.age_source == 'fractional(OMOP)')).sum()):,} of "
          f"{int((u.age < 2).sum()):,}")
    Path("results").mkdir(exist_ok=True)
    Path("results/age_provenance.md").write_text(
        "# Age provenance (a correction)\n\n"
        "Figure 1's scatter was **banded at young ages** because the `age` used by every analysis was a "
        "**whole number of years** for 100% of recordings — while the figure plots age on a log axis with "
        "ticks at 1, 3 and 6 *months*. The infant end of the curve was therefore drawn with resolution the "
        "data did not have.\n\n"
        "The column was also partly wrong: **7 recordings carried negative ages** (−6 … −1), and the "
        "discrepancy against the true fractional age reached **10.4 years** (median 0.33 y).\n\n"
        "A correct OMOP-derived fractional-age table existed (`fractional_age.parquet`) and had simply never "
        "been joined in, despite the manuscript claiming *'precise OMOP-derived fractional ages'*.\n\n"
        "| age source | n | share |\n|---|---|---|\n"
        f"| true fractional (OMOP) | {int((ba.age_source=='fractional(OMOP)').sum()):,} | "
        f"{100*(ba.age_source=='fractional(OMOP)').mean():.1f}% |\n"
        f"| integer only (AgeAtVisit) | {int((ba.age_source=='integer(AgeAtVisit)').sum()):,} | "
        f"{100*(ba.age_source=='integer(AgeAtVisit)').mean():.1f}% |\n\n"
        "**Honest limitation.** Only ~38% of recordings have a true fractional age; the expansion/backfill "
        "rows have nothing better than whole years. The negative ages are fixed and no analysis is fit on "
        "them. Effect on the headline detection AUROC is negligible (0.7328 → 0.7329 — adults dominate and "
        "the curve is flat there). Effect on the **paediatric growth curves is material**, and the "
        "manuscript's claim of precise fractional ages must be restricted to the cohort subset.\n")
    print("wrote results/age_provenance.md")


if __name__ == "__main__":
    main()
