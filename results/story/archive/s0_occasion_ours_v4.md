# Morgoth-free detector v4 — all stages (stage-matched) + localized focal (OccasionNoise, LOO-CV)

Stages: W+N1. Focal uses localization: per-segment region z -> peak_z, focality (peak − median region), asymmetry z, spatial stability.

| axis | stages | n pos/N | AUROC | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|---|
| focal | W+N1 | 14/100 | 0.886 | 0.688 | 17 | **47%** | **35%** |
| generalized | W+N1 | 19/100 | 0.898 | 0.737 | 18 | **39%** | **28%** |