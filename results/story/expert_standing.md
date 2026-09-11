# Standing against the individual experts, symmetric and with uncertainty (review comment 7)

**AUROC** is against the full expert majority (primary metric), with a recording-level bootstrap 95% CI.
**Under, as published**: an expert counts as under the model's ROC when that expert's point (graded against the leave-one-out majority of the other experts) lies on or below the model's ROC graded against the FULL majority. This must reproduce Figures 2 and 3.
**Under, symmetric**: the model's ROC is re-graded, for each expert, against that expert's own leave-one-out reference on the recordings that expert read. Bootstrap 95% CI re-derives every expert point and reference inside each of 2,000 replicates. This is relative standing, not a hypothesis test against any individual expert.

**Majority rule and denominator.** Here, as in Figures 2, 3 and S3, a recording is positive when at least half of its readers call it positive (mean vote >= 0.5), so an exact tie counts as positive. The human-ceiling table (Table S2) counts ties as negative, which is why its ON-100 base rates (12/100 focal, 18/100 generalized) differ from the positives here. ON-100 rows use the recordings finite for every compared method, which is why n is below 100.

| panel | axis | model | n (pos) | AUROC [95% CI] | experts | under, as published | under, symmetric [95% CI] |
|---|---|---|---|---|---|---|---|
| ON-100 | focal | LENS | 95 (14) | 0.908 [0.815, 0.978] | 17 | 53% (9/17) | 71% (12/17) [35%, 100%] |
| ON-100 | focal | Morgoth gate | 95 (14) | 0.908 [0.828, 0.974] | 17 | 41% (7/17) | 53% (9/17) [18%, 88%] |
| ON-100 | focal | van Putten (asym_rel_delta) | 95 (14) | 0.825 [0.717, 0.923] | 17 | 12% (2/17) | 12% (2/17) [0%, 59%] |
| ON-100 | generalized | LENS | 95 (17) | 0.961 [0.914, 0.994] | 18 | 83% (15/18) | 83% (15/18) [50%, 100%] |
| ON-100 | generalized | Morgoth gate | 95 (17) | 0.853 [0.750, 0.934] | 18 | 11% (2/18) | 17% (3/18) [6%, 56%] |
| ON-100 | generalized | van Putten (DAR) | 95 (17) | 0.817 [0.707, 0.913] | 18 | 11% (2/18) | 28% (5/18) [6%, 56%] |
| SAI-100 | focal | LENS | 100 (26) | 0.930 [0.862, 0.979] | 14 | 64% (9/14) | 71% (10/14) [43%, 93%] |
| SAI-100 | focal | Morgoth | 100 (26) | 0.976 [0.928, 1.000] | 14 | 93% (13/14) | 93% (13/14) [71%, 100%] |
| SAI-100 | focal | SCORE-AI | 100 (26) | 0.878 [0.784, 0.953] | 14 | 29% (4/14) | 36% (5/14) [21%, 79%] |
| SAI-100 | generalized | LENS | 100 (24) | 0.908 [0.806, 0.979] | 14 | 50% (7/14) | 50% (7/14) [36%, 86%] |
| SAI-100 | generalized | Morgoth | 100 (24) | 0.951 [0.897, 0.991] | 14 | 71% (10/14) | 64% (9/14) [43%, 100%] |
| SAI-100 | generalized | SCORE-AI | 100 (24) | 0.931 [0.878, 0.973] | 14 | 57% (8/14) | 64% (9/14) [29%, 86%] |

## Paired AUROC differences (same bootstrap resample for both models)

| panel | axis | comparison | ΔAUROC [95% CI] | two-sided bootstrap p |
|---|---|---|---|---|
| ON-100 | focal | LENS - Morgoth gate | -0.000 [-0.071, +0.082] | 1.00 |
| ON-100 | focal | LENS - van Putten (asym_rel_delta) | +0.083 [-0.050, +0.217] | 0.22 |
| ON-100 | generalized | LENS - Morgoth gate | +0.108 [+0.030, +0.204] | 0.00 |
| ON-100 | generalized | LENS - van Putten (DAR) | +0.143 [+0.068, +0.224] | < 0.001 |
| SAI-100 | focal | LENS - SCORE-AI | +0.052 [-0.047, +0.155] | 0.30 |
| SAI-100 | focal | LENS - Morgoth | -0.045 [-0.117, +0.015] | 0.14 |
| SAI-100 | generalized | LENS - SCORE-AI | -0.023 [-0.130, +0.061] | 0.69 |
| SAI-100 | generalized | LENS - Morgoth | -0.043 [-0.160, +0.042] | 0.38 |
