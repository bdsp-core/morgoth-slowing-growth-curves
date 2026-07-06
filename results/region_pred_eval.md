# Data-driven region/side localization (max-deviation lobe) vs reports

Predictor: lobe with max age-matched DAR deviation. Abnormal recordings only.


## Region — accuracy 0.175, macro-F1 0.128 (n=3412)

| region    |   precision |   recall |    f1 |   n_report |
|:----------|------------:|---------:|------:|-----------:|
| frontal   |       0.109 |    0.1   | 0.105 |        509 |
| temporal  |       0.771 |    0.179 | 0.29  |       2416 |
| central   |       0.08  |    0.131 | 0.099 |        245 |
| parietal  |       0.04  |    0.208 | 0.067 |        120 |
| occipital |       0.043 |    0.475 | 0.079 |        122 |


## Side — accuracy 0.525 (n=5681)

| side      |   precision |   recall |    f1 |   n_report |
|:----------|------------:|---------:|------:|-----------:|
| left      |       0.723 |    0.256 | 0.378 |       1862 |
| right     |       0.71  |    0.241 | 0.36  |       1381 |
| bilateral |       0.477 |    0.89  | 0.621 |       2438 |


_Predicts a specific lobe for every recording (no temporal default), so per-region recall is now meaningful. Deviation is age-band-matched vs normals per channel._
