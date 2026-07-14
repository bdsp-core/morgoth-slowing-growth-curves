# The sparse slowing score S

S is the **linear predictor** of an L1-regularised logistic model fit on normative deviations (z-scores), not the probability. The probability saturates near 0 and 1 and destroys grading; the logit is unbounded, linear in the z's, and monotone in evidence.

**S is not the measurement.** `z` is the measurement — unsupervised, fit to nothing but the normal population. `S` is trained to predict the expert's call and therefore inherits the expert's blind spots. S is used for detection and interpretability; it is never used to argue that we see slowing the reader misses. That argument belongs to z (§V4a).

Selection (correlation clustering, C, L1 path, stability) is re-derived **inside each outer training fold**; the normal reference is rebuilt from that fold's clean-normals. Split on patient.


## generalized slowing  (n = 6841 positive / 10249 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.775** [0.770, 0.781] across 5 folds
- **Parsimonious frozen model: 3 features**, nested AUROC 0.756 at mean size 3.0 (C = 0.001)
- L1 with the 1-SE rule retains 17 of 40 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.019 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 3.0 | 0.756 |
| 0.003 | 14.4 | 0.773 |
| 0.01 | 18.8 | 0.776 |
| 0.03 | 23.8 | 0.778 |
| 0.1 | 29.0 | 0.779 |
| 0.3 | 33.0 | 0.779 |
| 1 | 34.0 | 0.779 |

| retained feature | coefficient | stability |
|---|---|---|
| `log_delta@whole_head@N1` | +0.384 | 1.00 |
| `TAR@whole_head@W` | +0.303 | 1.00 |
| `|asym|@temporal@log_delta@N1` | +0.064 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `log_delta@whole_head@W` (0.55), `|asym|@parasagittal@log_delta@W` (0.53), `|asym|@temporal@TAR@N1` (0.43), `DAR@midline@N1` (0.43), `log_theta@midline@W` (0.33)

## focal slowing  (n = 8304 positive / 15055 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.746** [0.741, 0.753] across 5 folds
- **Parsimonious frozen model: 9 features**, nested AUROC 0.727 at mean size 7.8 (C = 0.001)
- L1 with the 1-SE rule retains 30 of 40 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.019 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 7.8 | 0.727 |
| 0.003 | 13.8 | 0.734 |
| 0.01 | 21.4 | 0.742 |
| 0.03 | 30.6 | 0.746 |
| 0.1 | 35.2 | 0.747 |
| 0.3 | 36.8 | 0.747 |
| 1 | 36.8 | 0.747 |

| retained feature | coefficient | stability |
|---|---|---|
| `|asym|@temporal@log_delta@N1` | +0.170 | 1.00 |
| `log_theta@L_temporal@N1` | +0.155 | 1.00 |
| `|asym|@parasagittal@log_theta@N1` | +0.133 | 1.00 |
| `|asym|@temporal@log_theta@N1` | +0.103 | 1.00 |
| `|asym|@parasagittal@log_delta@N1` | +0.096 | 1.00 |
| `|asym|@temporal@rel_delta@W` | +0.064 | 1.00 |
| `|asym|@parasagittal@rel_delta@W` | +0.036 | 1.00 |
| `|asym|@temporal@TAR@W` | +0.017 | 0.92 |
| `|asym|@temporal@log_delta@W` | +0.001 | 0.75 |

Representative features the L1 path *dropped* (stability < 60%): `DAR@midline@W` (0.56), `|asym|@temporal@TAR@N1` (0.55), `TAR@midline@W` (0.53), `rel_delta@R_parasagittal@N1` (0.49), `TAR@L_temporal@W` (0.44)

## The focal detector, evaluated on three different questions

One detector (negatives during training = clean-normals **plus** generalized slowing, so it cannot win on global slowing). The three contrasts below use that same score and differ only in which recordings form the comparison group. Nested CV; mean over outer folds, range in brackets.

**Note on the positives:** a report naming focal slowing does not exclude generalized slowing — 60.9% of focal recordings also carry pathologic generalized slowing. The second block restricts positives to the 39.1% that are exclusively focal.

| positives | comparison group | nested AUROC [fold range] | what it tells us |
|---|---|---|---|
| all focal | clean-normal | **0.774** [0.771–0.777] | can we see focal slowing at all? |
| all focal | clean-normal + generalized | **0.746** [0.740–0.753] | the deployment question: focal against everything else |
| all focal | generalized | **0.669** [0.649–0.691] | can we tell focal *from* generalized? (the hard one) |
| exclusively focal (no pathologic generalized) | clean-normal | **0.740** [0.727–0.748] | can we see focal slowing at all? |
| exclusively focal (no pathologic generalized) | clean-normal + generalized | **0.710** [0.700–0.723] | the deployment question: focal against everything else |
| exclusively focal (no pathologic generalized) | generalized | **0.628** [0.611–0.655] | can we tell focal *from* generalized? (the hard one) |

## Frozen for external confirmation

Coefficients written to `data/derived/sparse_score_coefs.json`. The external test against the 18-expert panel is run by `scripts/104_sparse_score_external.py` with these coefficients **frozen**. Disclosure: OccasionNoise has already been examined with hand-picked scores (scripts/94), so that run is confirmatory, not a first look.

## What is deliberately not modelled

The **band** (delta vs theta vs mixed). Experts agree with one another on band at κ = 0.09–0.38 (`results/moe_band_vs_ours.md`). Fitting an L1 model to a target with that little reliable signal would select noise and dress it in confidence intervals. We report the ceiling and decline the axis.
