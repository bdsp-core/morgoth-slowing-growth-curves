# Band-matched lateralization (focal, L vs R)

n=2049 focal-lateralized. Rows = the case's reported band; columns = which band's asymmetry features the classifier used. AUROC for left-vs-right.

| case_band   |    n |   clf_delta |   clf_theta |   clf_both |
|:------------|-----:|------------:|------------:|-----------:|
| delta       |  434 |       0.921 |       0.861 |      0.926 |
| theta       |  146 |       0.841 |       0.835 |      0.827 |
| mixed       | 1342 |       0.877 |       0.782 |      0.879 |


- **Band-aware routed predictor** (delta→delta, theta→theta, mixed→both): overall AUROC **0.882**

- Delta-only-always baseline: AUROC 0.882


**Face validity:** on theta-predominant focal cases, the theta-asymmetry classifier should lateralize at least as well as the delta one — so the side we report is driven by the same band we call the slowing. (theta n is small; treat as indicative.)
