# Band-conditioned antisymmetric lateralizer (focal, L vs R)

Antisymmetric (flip-augmented, no-intercept) + dominant-band×asymmetry interactions; multi-band inputs; grouped CV. Per dominant-band stratum:

| stratum   |    n |   auroc |   bal_acc |   recall_L |   recall_R |
|:----------|-----:|--------:|----------:|-----------:|-----------:|
| ALL       | 2049 |   0.88  |     0.809 |      0.806 |      0.813 |
| delta     |  434 |   0.917 |     0.849 |      0.843 |      0.855 |
| theta     |  146 |   0.768 |     0.674 |      0.727 |      0.621 |
| mixed     | 1469 |   0.88  |     0.811 |      0.802 |      0.82  |


_Balanced left/right recall (no left prior), band-specific behavior, and the tiny theta stratum borrows strength from the shared backbone. This is the model to wire into the report generator; the reader sees only band-matched deviation magnitudes, not any of this._
