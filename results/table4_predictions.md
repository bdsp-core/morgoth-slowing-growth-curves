# Table 4 — Pre-registered predictions scorecard (SAP §10)

Every pre-registered prediction, scored against its stated falsification threshold on the completed v6 run. Predictions we could not yet honestly score are marked **UNEVALUATED** rather than omitted.

| P   | prediction                                                 | falsified_if                                               | result                                                                                           | verdict                                                                      |
|:----|:-----------------------------------------------------------|:-----------------------------------------------------------|:-------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------|
| P1  | Detection AUROC >= 0.80 whole-recording, vigilance-matched | < 0.75                                                     | Morgoth gate 0.881 (any slowing); sparse score 0.844; normative deviation 0.806 (N1) / 0.784 (W) | CONFIRMED                                                                    |
| P2  | Sex can be pooled in the norms                             | dAUROC from adding sex > 0.01                              | dAUROC <= 0.002 (prior run); NOT re-verified on v6                                               | CONFIRMED (pending v6 re-verification)                                       |
| P3  | Amount score is reliable                                   | split-half ICC < 0.8                                       | Table 3 (descriptor reliability) not yet produced                                                | UNEVALUATED                                                                  |
| P4  | Prevalence descriptor is reliable                          | ICC < 0.8                                                  | Table 3 (descriptor reliability) not yet produced                                                | UNEVALUATED                                                                  |
| P5  | Band call is WEAK (report only as low-confidence)          | band-match > 0.8 (then promote it)                         | near-chance against per-expert band calls (kappa 0.01-0.07)                                      | CONFIRMED (weak, as predicted)                                               |
| P6  | Readers under-report SLEEP slowing                         | our sleep rate <= report rate                              | evidence file (v4a_wake_sleep) deleted in the results purge; NOT regenerated on v6               | UNEVALUATED                                                                  |
| P7  | Our detection meets/exceeds the human ceiling              | our balanced acc < between-rater ceiling                   | focal: ours 0.748 vs ceiling 0.795; generalized: ours 0.757 vs ceiling 0.809                     | focal FALSIFIED / generalized FALSIFIED                                      |
| P8a | Age-norming a van Putten metric beats it as-published      | dAUROC(normed - raw) <= 0                                  | Q_SLOWING +0.038/+0.049/+0.041 (CONFIRMED); r_sBSI -0.012/-0.017/-0.011 (FALSIFIED)              | MIXED — confirmed for the slowing indices, falsified for the asymmetry index |
| P8b | Our best score >= best van Putten on each target           | any van Putten arm beats ours by dAUROC > 0.02 -> adopt it | Morgoth 0.881/0.918/0.875 vs best vP 0.698/0.751/0.726 (margin +0.18/+0.17/+0.15)                | CONFIRMED (no adoption triggered)                                            |


## P7 detail — the human ceiling

|             |   ours_bacc |   ours_auroc |   ceiling | verdict   |
|:------------|------------:|-------------:|----------:|:----------|
| focal       |    0.748106 |     0.904356 |  0.794744 | FALSIFIED |
| generalized |    0.757453 |     0.859756 |  0.809321 | FALSIFIED |


## P8a detail — does our normative framing improve HIS instruments?

| metric    | target      |   raw |   normed |   delta | verdict   |
|:----------|:------------|------:|---------:|--------:|:----------|
| Q_SLOWING | abnormal    | 0.654 |    0.692 |   0.038 | CONFIRMED |
| Q_SLOWING | generalized | 0.702 |    0.751 |   0.049 | CONFIRMED |
| Q_SLOWING | focal       | 0.63  |    0.671 |   0.041 | CONFIRMED |
| r_sBSI    | abnormal    | 0.698 |    0.686 |  -0.012 | FALSIFIED |
| r_sBSI    | generalized | 0.692 |    0.675 |  -0.017 | FALSIFIED |
| r_sBSI    | focal       | 0.726 |    0.715 |  -0.011 | FALSIFIED |


## P8b detail — the adoption rule

| target      |   ours(Morgoth) |   best van Putten |   margin | verdict                 |
|:------------|----------------:|------------------:|---------:|:------------------------|
| abnormal    |           0.881 |             0.698 |    0.183 | CONFIRMED (no adoption) |
| generalized |           0.918 |             0.751 |    0.167 | CONFIRMED (no adoption) |
| focal       |           0.875 |             0.726 |    0.149 | CONFIRMED (no adoption) |

