# The deviation field and its six descriptors

**Fixes (2026-07-10):** flat segments (all bands at the eps floor; 22-32% of abnormal wake) are dropped as suppressed/dead epochs; the alpha-attenuation axis is restricted to W/N1 (alpha is the posterior dominant rhythm, meaningful only where it is expected). See results/n1_anomaly_diagnosis.md.

2,279,923 segment-region z-scores over 11,657 recordings. One learned direction `w` = `z_log_theta` +2.37, `a_atten` +2.35 (5-fold AUROC 0.770, split on patient). Everything below is an aggregation or a contrast of `S = w · z`; nothing else is fit.

## Sanity: descriptors must be unremarkable in clinician-normals

| stage | group | n | amount (SD, median) | prevalence (mean) | longest run (min) | band index | alpha attenuation |
|---|---|---|---|---|---|---|---|
| W | clean-normal | 3918 | -0.06 | 0.045 | 0.00 | +0.010 | +0.07 |
| W | focal | 2684 | +0.70 | 0.062 | 0.00 | +0.010 | +0.04 |
| W | generalized | 889 | +0.97 | 0.088 | 0.00 | -0.044 | +0.18 |
| N1 | clean-normal | 1977 | -0.13 | 0.051 | 0.00 | -0.017 | +0.00 |
| N1 | focal | 1731 | +0.94 | 0.308 | 0.23 | -0.029 | +0.00 |
| N1 | generalized | 778 | +1.29 | 0.412 | 0.47 | -0.044 | +0.00 |

**Calibration check.** The threshold is the 95% centile of normal segments at that age and stage, so clean-normals must average ~0.05 prevalence: observed **0.047** (median 0.000 — the distribution is right-skewed, so the mean is the quantity to read). Their median amount must be ~0: observed **-0.09 SD**.

## Stage coverage

| group        |   N1 |   N2 |   N3 |   REM |    W |
|:-------------|-----:|-----:|-----:|------:|-----:|
| clean-normal | 1977 | 1595 |  278 |  1098 | 3918 |
| focal        | 1731 | 1899 |  874 |   656 | 2684 |
| generalized  |  778 |  939 |  595 |   189 |  889 |


Written: `data/derived/description_descriptors.parquet`, `data/derived/amount_direction.json`.
