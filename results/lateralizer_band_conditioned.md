# Band-conditioned antisymmetric lateralizer (focal, L vs R)

Antisymmetric (flip-augmented, no-intercept) + dominant-band×asymmetry interactions; multi-band inputs; grouped CV. Per dominant-band stratum:

| stratum   |    n |   auroc |   bal_acc |   recall_L |   recall_R |
|:----------|-----:|--------:|----------:|-----------:|-----------:|
| ALL       | 2926 |   0.861 |     0.79  |      0.8   |      0.781 |
| delta     |  571 |   0.889 |     0.816 |      0.84  |      0.792 |
| theta     |  204 |   0.788 |     0.748 |      0.78  |      0.716 |
| mixed     | 2151 |   0.86  |     0.787 |      0.791 |      0.784 |


_Balanced left/right recall (no left prior), band-specific behavior, and the tiny theta stratum borrows strength from the shared backbone. This is the model to wire into the report generator; the reader sees only band-matched deviation magnitudes, not any of this._
