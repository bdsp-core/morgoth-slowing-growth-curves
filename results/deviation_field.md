# The deviation field and its six descriptors

**Fixes (2026-07-10):** flat segments (all bands at the eps floor; 22-32% of abnormal wake) are dropped as suppressed/dead epochs; the alpha-attenuation axis is restricted to W/N1 (alpha is the posterior dominant rhythm, meaningful only where it is expected). See results/n1_anomaly_diagnosis.md.

45,038,939 segment-region z-scores over 16,327 recordings. One learned direction `w` = `z_log_delta` +0.23, `z_log_theta` +1.67, `a_atten` +1.98 (5-fold AUROC 0.744, split on patient). Everything below is an aggregation or a contrast of `S = w · z`; nothing else is fit.

## Sanity: descriptors must be unremarkable in clinician-normals

| stage | group | n | amount (SD, median) | prevalence (mean) | longest run (min) | band index | alpha attenuation |
|---|---|---|---|---|---|---|---|
| W | clean-normal | 6249 | -0.13 | 0.045 | 0.00 | -0.071 | +0.08 |
| W | focal | 4972 | +0.61 | 0.179 | 0.23 | -0.068 | +0.05 |
| W | generalized | 1620 | +0.99 | 0.279 | 0.47 | -0.145 | +0.27 |
| N1 | clean-normal | 4893 | -0.19 | 0.035 | 0.00 | -0.013 | +0.00 |
| N1 | focal | 4349 | +0.50 | 0.133 | 0.00 | -0.056 | +0.00 |
| N1 | generalized | 1477 | +0.75 | 0.195 | 0.00 | -0.135 | +0.00 |

**Calibration check.** The threshold is the 95% centile of normal segments at that age and stage, so clean-normals must average ~0.05 prevalence: observed **0.040** (median 0.000 — the distribution is right-skewed, so the mean is the quantity to read). Their median amount must be ~0: observed **-0.16 SD**.

## Stage coverage

| group        |   N1 |   N2 |   N3 |   REM |    W |
|:-------------|-----:|-----:|-----:|------:|-----:|
| clean-normal | 4893 | 4181 | 1362 |  3994 | 6249 |
| focal        | 4349 | 4169 | 2412 |  3050 | 4972 |
| generalized  | 1477 | 1622 | 1073 |   947 | 1620 |


Written: `data/derived/description_descriptors.parquet`, `data/derived/amount_direction.json`.
