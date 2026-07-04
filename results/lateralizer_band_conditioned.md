# Band-conditioned antisymmetric lateralizer (focal, L vs R)

Antisymmetric (flip-augmented, no-intercept) + dominant-band×asymmetry interactions; multi-band inputs; grouped CV. Per dominant-band stratum:

| stratum   |   n |   auroc |   bal_acc |   recall_L |   recall_R |
|:----------|----:|--------:|----------:|-----------:|-----------:|
| ALL       | 555 |   0.852 |     0.792 |      0.775 |      0.81  |
| delta     | 169 |   0.88  |     0.797 |      0.766 |      0.828 |
| theta     |  41 |   0.736 |     0.739 |      0.786 |      0.692 |
| mixed     | 345 |   0.855 |     0.796 |      0.777 |      0.816 |


_Balanced left/right recall (no left prior), band-specific behavior, and the tiny theta stratum borrows strength from the shared backbone. This is the model to wire into the report generator; the reader sees only band-matched deviation magnitudes, not any of this._
