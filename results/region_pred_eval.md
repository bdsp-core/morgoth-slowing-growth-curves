# Data-driven region/side localization (max-deviation lobe) vs reports

Predictor: lobe with max age-matched DAR deviation. Abnormal recordings only.


## Region — accuracy 0.162, macro-F1 0.115 (n=3525)

| region    |   precision |   recall |    f1 |   n_report |
|:----------|------------:|---------:|------:|-----------:|
| frontal   |       0.144 |    0.093 | 0.113 |        691 |
| temporal  |       0.773 |    0.175 | 0.285 |       2445 |
| central   |       0.074 |    0.121 | 0.092 |        256 |
| parietal  |       0.021 |    0.212 | 0.039 |         66 |
| occipital |       0.023 |    0.507 | 0.045 |         67 |


## Side — accuracy 0.748 (n=5900)

| side      |   precision |   recall |    f1 |   n_report |
|:----------|------------:|---------:|------:|-----------:|
| left      |       0.33  |    0.282 | 0.304 |        760 |
| right     |       0.174 |    0.276 | 0.213 |        279 |
| bilateral |       0.857 |    0.848 | 0.852 |       4861 |


_Predicts a specific lobe for every recording (no temporal default), so per-region recall is now meaningful. Deviation is age-band-matched vs normals per channel._
