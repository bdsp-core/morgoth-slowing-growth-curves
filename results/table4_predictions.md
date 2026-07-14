# Table 4 — Pre-registered predictions scorecard (SAP §10)

Every pre-registered prediction, scored against its stated falsification threshold on the completed v6 run. Predictions we could not yet honestly score are marked **UNEVALUATED** rather than omitted.

| P   | prediction                                                 | falsified_if                                               | result                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | verdict                                                                                     |
|:----|:-----------------------------------------------------------|:-----------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------|
| P1  | Detection AUROC >= 0.80 whole-recording, vigilance-matched | < 0.75                                                     | Morgoth gate 0.881 (any slowing); sparse score 0.844; normative deviation 0.806 (N1) / 0.784 (W)                                                                                                                                                                                                                                                                                                                                                                                                                                            | CONFIRMED                                                                                   |
| P2  | Sex can be pooled in the norms                             | dAUROC from adding sex > 0.01                              | RE-VERIFIED on v6 across 15 (stage x feature) cells: max |dAUROC| = 0.0043, median 0.0006 (bar is 0.01). Splitting the normative reference by sex does not improve detection anywhere. NB: this required first fixing a manifest bug in which sex was encoded two ways (F/M and Female/Male), which had been silently dropping ~12.8k recordings from any sex-filtered analysis.                                                                                                                                                            | CONFIRMED                                                                                   |
| P3  | Amount score is reliable                                   | split-half ICC < 0.8                                       | split-half ICC(2,1) = 0.991 (n=19,184 recordings, interleaved segment halves, stage W)                                                                                                                                                                                                                                                                                                                                                                                                                                                      | CONFIRMED                                                                                   |
| P4  | Prevalence descriptor is reliable                          | ICC < 0.8                                                  | split-half ICC(2,1) = 0.970 (n=19,257)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | CONFIRMED                                                                                   |
| P5  | Band call is WEAK (report only as low-confidence)          | band-match > 0.8 (then promote it)                         | near-chance against per-expert band calls (kappa 0.01-0.07)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | CONFIRMED (weak, as predicted)                                                              |
| P6  | Readers under-report SLEEP slowing                         | our sleep rate <= report rate                              | LITERAL criterion: our sleep-slowing rate 15.6% <= report slowing rate 48.2% -> falsified. BUT the conditional (non-circular) test supports the phenomenon: readers name slowing in 75.0% of recordings where it is visible AWAKE vs only 54.1% where it is visible ONLY IN SLEEP (n=4,280 vs 703, clean_pair). The pre-registered criterion compares a 95th-centile exceedance rate (~5% in normals BY CONSTRUCTION) against the report's overall slowing rate - not commensurable quantities. Falsified as written; phenomenon supported. | FALSIFIED (as written) / phenomenon SUPPORTED                                               |
| P7  | Our detection meets/exceeds the human ceiling              | our balanced acc < between-rater ceiling                   | GATE - focal 0.748 vs ceiling 0.795; generalized 0.757 vs 0.809 -> below on BOTH axes. DEVIATION SCORE (frozen S) - focal 0.787 vs 0.801 (below); generalized 0.861 vs 0.809 (ABOVE). Both scores OUT-RANK the experts (gate AUROC 0.860/0.904; S 0.879/0.910) - it is thresholding, not ranking, that falls short.                                                                                                                                                                                                                         | FALSIFIED for the gate (both axes) / deviation score CONFIRMED for generalized only         |
| P8a | Age-norming a van Putten metric beats it as-published      | dAUROC(normed - raw) <= 0                                  | CONFIRMED for every SLOWING index (Q_SLOWING +0.038/+0.049/+0.041; DAR +0.030/+0.041/+0.034; DTABR +0.035/+0.046/+0.040; SEF95 +0.038/+0.045/+0.043). FALSIFIED for both ASYMMETRY indices (r_sBSI -0.012/-0.017/-0.011; Q_ASYM -0.004/-0.006/-0.004). The split is physiologically coherent: SLOWING changes with age, so an age-matched reference helps; left-right SYMMETRY does not, so age-norming it only adds noise.                                                                                                                 | MIXED — but systematically: helps every age-DEPENDENT metric, hurts every age-INVARIANT one |
| P8b | Our best score >= best van Putten on each target           | any van Putten arm beats ours by dAUROC > 0.02 -> adopt it | Morgoth 0.881/0.918/0.875 vs best vP 0.719/0.789/0.726 (DTABR-z, DTABR-z, r_sBSI) -> margin +0.162/+0.129/+0.149                                                                                                                                                                                                                                                                                                                                                                                                                            | CONFIRMED (no adoption triggered)                                                           |


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
| DAR       | abnormal    | 0.667 |    0.697 |   0.03  | CONFIRMED |
| DAR       | generalized | 0.731 |    0.772 |   0.041 | CONFIRMED |
| DAR       | focal       | 0.63  |    0.664 |   0.034 | CONFIRMED |
| DTABR     | abnormal    | 0.684 |    0.719 |   0.035 | CONFIRMED |
| DTABR     | generalized | 0.743 |    0.789 |   0.046 | CONFIRMED |
| DTABR     | focal       | 0.651 |    0.691 |   0.04  | CONFIRMED |
| SEF95     | abnormal    | 0.637 |    0.675 |   0.038 | CONFIRMED |
| SEF95     | generalized | 0.665 |    0.71  |   0.045 | CONFIRMED |
| SEF95     | focal       | 0.621 |    0.664 |   0.043 | CONFIRMED |
| r_sBSI    | abnormal    | 0.698 |    0.686 |  -0.012 | FALSIFIED |
| r_sBSI    | generalized | 0.692 |    0.675 |  -0.017 | FALSIFIED |
| r_sBSI    | focal       | 0.726 |    0.715 |  -0.011 | FALSIFIED |
| Q_ASYM    | abnormal    | 0.684 |    0.68  |  -0.004 | FALSIFIED |
| Q_ASYM    | generalized | 0.69  |    0.684 |  -0.006 | FALSIFIED |
| Q_ASYM    | focal       | 0.697 |    0.693 |  -0.004 | FALSIFIED |


## P8b detail — the adoption rule

| target      |   ours(Morgoth) |   best van Putten |   margin | verdict                 |
|:------------|----------------:|------------------:|---------:|:------------------------|
| abnormal    |           0.881 |             0.719 |    0.162 | CONFIRMED (no adoption) |
| generalized |           0.918 |             0.789 |    0.129 | CONFIRMED (no adoption) |
| focal       |           0.875 |             0.726 |    0.149 | CONFIRMED (no adoption) |

