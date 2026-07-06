# Band-matched lateralization (focal, L vs R)

n=2926 focal-lateralized. Rows = the case's reported band; columns = which band's asymmetry features the classifier used. AUROC for left-vs-right.

| case_band   |    n |   clf_delta |   clf_theta |   clf_both |
|:------------|-----:|------------:|------------:|-----------:|
| delta       |  571 |       0.897 |       0.84  |      0.901 |
| theta       |  204 |       0.827 |       0.835 |      0.802 |
| mixed       | 1977 |       0.863 |       0.762 |      0.867 |


- **Band-aware routed predictor** (delta→delta, theta→theta, mixed→both): overall AUROC **0.867**

- Delta-only-always baseline: AUROC 0.866


**Face validity:** on theta-predominant focal cases, the theta-asymmetry classifier should lateralize at least as well as the delta one — so the side we report is driven by the same band we call the slowing. (theta n is small; treat as indicative.)
