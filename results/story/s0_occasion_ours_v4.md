# Morgoth-free detector v4 — all stages (stage-matched) + localized focal (OccasionNoise, LOO-CV)

Stages: W+N1+N2+N3+REM. Focal uses localization: per-segment region z -> peak_z, focality (peak − median region), asymmetry z, spatial stability.

| axis | stages | n pos/N | AUROC | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|---|
| focal | W+N1+N2+N3+REM | 14/100 | 0.895 | 0.737 | 17 | **47%** | **53%** |
| generalized | W+N1+N2+N3+REM | 19/100 | 0.920 | 0.800 | 18 | **39%** | **44%** |