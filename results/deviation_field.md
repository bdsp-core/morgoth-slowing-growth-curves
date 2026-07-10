# The deviation field and its six descriptors

2,444,510 segment-region z-scores over 11,657 recordings. One learned direction `w` = `z_log_delta` +0.80, `z_log_theta` +2.82, `a_atten` +4.72 (5-fold AUROC 0.811, split on patient). Everything below is an aggregation or a contrast of `S = w · z`; nothing else is fit.

## Sanity: descriptors must be unremarkable in clinician-normals

| stage | group | n | amount (SD, median) | prevalence (mean) | longest run (min) | band index | alpha attenuation |
|---|---|---|---|---|---|---|---|
| W | clean-normal | 3930 | -0.05 | 0.047 | 0.00 | -0.023 | -0.05 |
| W | focal | 2984 | +0.73 | 0.289 | 0.47 | -0.026 | +3.52 |
| W | generalized | 1113 | +1.18 | 0.419 | 1.40 | -0.026 | +6.44 |
| N1 | clean-normal | 1977 | +0.02 | 0.048 | 0.00 | -0.016 | +0.04 |
| N1 | focal | 1732 | +0.69 | 0.200 | 0.00 | -0.048 | -0.34 |
| N1 | generalized | 778 | +1.19 | 0.356 | 0.23 | -0.066 | -0.20 |

**Calibration check.** The threshold is the 95% centile of normal segments at that age and stage, so clean-normals must average ~0.05 prevalence: observed **0.047** (median 0.000 — the distribution is right-skewed, so the mean is the quantity to read). Their median amount must be ~0: observed **-0.03 SD**.

## Stage coverage

| group        |   N1 |   N2 |   N3 |   REM |    W |
|:-------------|-----:|-----:|-----:|------:|-----:|
| clean-normal | 1977 | 1595 |  278 |  1098 | 3930 |
| focal        | 1732 | 1899 |  874 |   656 | 2984 |
| generalized  |  778 |  939 |  595 |   189 | 1113 |


Written: `data/derived/description_descriptors.parquet`, `data/derived/amount_direction.json`.
