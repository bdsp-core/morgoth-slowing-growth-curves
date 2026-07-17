# Morgoth-free detector v4 — all stages (stage-matched) + localized focal (OccasionNoise, LOO-CV)

Stages: W+N1+N2+N3+REM. Focal uses localization: per-segment region z -> peak_z, focality (peak − median region), asymmetry z, spatial stability.

| axis | stages | n pos/N | AUROC | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|---|
| focal | W+N1+N2+N3+REM | 14/100 | 0.898 | 0.745 | 17 | **53%** | **65%** |
| generalized | W+N1+N2+N3+REM | 19/100 | 0.913 | 0.792 | 18 | **33%** | **33%** |