# Band-matched lateralization (focal, L vs R)

n=1301 focal-lateralized. Rows = the case's reported band; columns = which band's asymmetry features the classifier used. AUROC for left-vs-right.

| case_band   |   n |   clf_delta |   clf_theta |   clf_both |
|:------------|----:|------------:|------------:|-----------:|
| delta       | 292 |       0.941 |       0.887 |      0.943 |
| theta       |  82 |       0.862 |       0.876 |      0.85  |
| mixed       | 866 |       0.92  |       0.846 |      0.918 |


- **Band-aware routed predictor** (delta→delta, theta→theta, mixed→both): overall AUROC **0.917**

- Delta-only-always baseline: AUROC 0.919


**Face validity:** on theta-predominant focal cases, the theta-asymmetry classifier should lateralize at least as well as the delta one — so the side we report is driven by the same band we call the slowing. (theta n is small; treat as indicative.)
