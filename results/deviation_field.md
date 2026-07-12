# The deviation field and its six descriptors

**Fixes (2026-07-10):** flat segments (all bands at the eps floor; 22-32% of abnormal wake) are dropped as suppressed/dead epochs; the alpha-attenuation axis is restricted to W/N1 (alpha is the posterior dominant rhythm, meaningful only where it is expected). See results/n1_anomaly_diagnosis.md.

36,157,158 segment-region z-scores over 13,393 recordings. One learned direction `w` = `z_log_delta` +0.08, `z_log_theta` +1.32, `a_atten` +1.45 (5-fold AUROC 0.684, split on patient). Everything below is an aggregation or a contrast of `S = w · z`; nothing else is fit.

## Sanity: descriptors must be unremarkable in clinician-normals

| stage | group | n | amount (SD, median) | prevalence (mean) | longest run (min) | band index | alpha attenuation |
|---|---|---|---|---|---|---|---|
| W | clean-normal | 5200 | -0.10 | 0.046 | 0.00 | -0.054 | +0.06 |
| W | focal | 4190 | +0.62 | 0.181 | 0.23 | -0.052 | +0.04 |
| W | generalized | 2142 | +0.73 | 0.224 | 0.23 | -0.089 | +0.16 |
| N1 | clean-normal | 4089 | -0.16 | 0.036 | 0.00 | -0.014 | +0.00 |
| N1 | focal | 3681 | +0.55 | 0.134 | 0.00 | -0.061 | +0.00 |
| N1 | generalized | 1927 | +0.61 | 0.158 | 0.00 | -0.085 | +0.00 |

**Calibration check.** The threshold is the 95% centile of normal segments at that age and stage, so clean-normals must average ~0.05 prevalence: observed **0.042** (median 0.000 — the distribution is right-skewed, so the mean is the quantity to read). Their median amount must be ~0: observed **-0.13 SD**.

## Stage coverage

| group        |   N1 |   N2 |   N3 |   REM |    W |
|:-------------|-----:|-----:|-----:|------:|-----:|
| clean-normal | 4089 | 3482 | 1129 |  3344 | 5200 |
| focal        | 3681 | 3528 | 2047 |  2606 | 4190 |
| generalized  | 1927 | 1970 | 1168 |  1304 | 2142 |


Written: `data/derived/description_descriptors.parquet`, `data/derived/amount_direction.json`.
