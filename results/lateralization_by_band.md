# Band-matched lateralization (focal, L vs R)

n=2691 focal-lateralized. Rows = the case's reported band; columns = which band's asymmetry features the classifier used. AUROC for left-vs-right.

| case_band   |    n |   clf_delta |   clf_theta |   clf_both |
|:------------|-----:|------------:|------------:|-----------:|
| delta       |  536 |       0.891 |       0.768 |      0.894 |
| theta       |  329 |       0.852 |       0.829 |      0.841 |
| mixed       | 1632 |       0.888 |       0.787 |      0.888 |


- **Band-aware routed predictor** (delta→delta, theta→theta, mixed→both): overall AUROC **0.879**

- Delta-only-always baseline: AUROC 0.881


**Face validity:** on theta-predominant focal cases, the theta-asymmetry classifier should lateralize at least as well as the delta one — so the side we report is driven by the same band we call the slowing. (theta n is small; treat as indicative.)
