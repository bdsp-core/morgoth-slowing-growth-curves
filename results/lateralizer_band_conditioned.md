# Band-conditioned antisymmetric lateralizer (focal, L vs R)

Antisymmetric (flip-augmented, no-intercept) + dominant-band×asymmetry interactions; multi-band inputs; grouped CV. Per dominant-band stratum:

| stratum   |    n |   auroc |   bal_acc |   recall_L |   recall_R |
|:----------|-----:|--------:|----------:|-----------:|-----------:|
| ALL       | 1301 |   0.908 |     0.857 |      0.869 |      0.845 |
| delta     |  292 |   0.936 |     0.854 |      0.847 |      0.862 |
| theta     |   82 |   0.741 |     0.745 |      0.704 |      0.786 |
| mixed     |  927 |   0.914 |     0.868 |      0.892 |      0.844 |


_Balanced left/right recall (no left prior), band-specific behavior, and the tiny theta stratum borrows strength from the shared backbone. This is the model to wire into the report generator; the reader sees only band-matched deviation magnitudes, not any of this._
