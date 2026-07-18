# Age provenance (a correction)

Figure 1's scatter was **banded at young ages** because the `age` used by every analysis was a **whole number of years** for 100% of recordings — while the figure plots age on a log axis with ticks at 1, 3 and 6 *months*. The infant end of the curve was therefore drawn with resolution the data did not have.

The column was also partly wrong: **7 recordings carried negative ages** (−6 … −1), and the discrepancy against the true fractional age reached **10.4 years** (median 0.33 y).

A correct OMOP-derived fractional-age table existed (`fractional_age.parquet`) and had simply never been joined in, despite the manuscript claiming *'precise OMOP-derived fractional ages'*.

| age source | n | share |
|---|---|---|
| true fractional (OMOP) | 27,416 | 99.6% |
| integer only (AgeAtVisit) | 0 | 0.0% |

**Honest limitation.** Only ~38% of recordings have a true fractional age; the expansion/backfill rows have nothing better than whole years. The negative ages are fixed and no analysis is fit on them. Effect on the headline detection AUROC is negligible (0.7328 → 0.7329 — adults dominate and the curve is flat there). Effect on the **paediatric growth curves is material**, and the manuscript's claim of precise fractional ages must be restricted to the cohort subset.
