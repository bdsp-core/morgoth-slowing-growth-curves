# The sparse slowing score S

S is the **linear predictor** of an L1-regularised logistic model fit on normative deviations (z-scores), not the probability. The probability saturates near 0 and 1 and destroys grading; the logit is unbounded, linear in the z's, and monotone in evidence.

**S is not the measurement.** `z` is the measurement — unsupervised, fit to nothing but the normal population. `S` is trained to predict the expert's call and therefore inherits the expert's blind spots. S is used for detection and interpretability; it is never used to argue that we see slowing the reader misses. That argument belongs to z (§V4a).

Selection (correlation clustering, C, L1 path, stability) is re-derived **inside each outer training fold**; the normal reference is rebuilt from that fold's clean-normals. Split on patient.


## generalized slowing  (n = 4994 positive / 10276 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.844** [0.827, 0.858] across 5 folds
- **Parsimonious frozen model: 2 features**, nested AUROC 0.815 at mean size 2.0 (C = 0.001)
- L1 with the 1-SE rule retains 20 of 39 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.030 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 2.0 | 0.815 |
| 0.003 | 10.6 | 0.837 |
| 0.01 | 18.8 | 0.842 |
| 0.03 | 22.6 | 0.845 |
| 0.1 | 26.0 | 0.847 |
| 0.3 | 30.8 | 0.847 |
| 1 | 32.8 | 0.847 |

| retained feature | coefficient | stability |
|---|---|---|
| `log_delta@whole_head@N1` | +0.346 | 1.00 |
| `TAR@whole_head@W` | +0.245 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `|asym|@temporal@log_delta@W` (0.55), `|asym|@parasagittal@log_delta@N1` (0.54), `|asym|@temporal@TAR@W` (0.53), `rel_delta@whole_head@N1` (0.52), `|asym|@temporal@DAR@W` (0.46)

## focal slowing  (n = 8064 positive / 13482 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.758** [0.745, 0.772] across 5 folds
- **Parsimonious frozen model: 7 features**, nested AUROC 0.699 at mean size 3.4 (C = 0.001)
- L1 with the 1-SE rule retains 25 of 37 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.059 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 3.4 | 0.699 |
| 0.003 | 10.0 | 0.744 |
| 0.01 | 16.6 | 0.751 |
| 0.03 | 25.4 | 0.757 |
| 0.1 | 30.2 | 0.759 |
| 0.3 | 34.2 | 0.759 |
| 1 | 35.4 | 0.759 |

| retained feature | coefficient | stability |
|---|---|---|
| `|asym|@temporal@log_delta@N1` | +0.169 | 1.00 |
| `|asym|@parasagittal@log_theta@N1` | +0.107 | 1.00 |
| `log_theta@L_temporal@N1` | +0.083 | 1.00 |
| `|asym|@parasagittal@log_delta@N1` | +0.028 | 0.99 |
| `|asym|@temporal@log_theta@N1` | +0.017 | 1.00 |
| `|asym|@temporal@TAR@W` | +0.003 | 0.97 |
| `|asym|@temporal@rel_delta@W` | +0.001 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `|asym|@parasagittal@DAR@W` (0.55), `|asym|@temporal@log_delta@W` (0.47), `|asym|@temporal@DAR@N1` (0.45), `TAR@L_temporal@W` (0.41), `|asym|@temporal@DAR@W` (0.41)

## The focal detector, evaluated on three different questions

One detector (negatives during training = clean-normals **plus** generalized slowing, so it cannot win on global slowing). The three contrasts below use that same score and differ only in which recordings form the comparison group. Nested CV; mean over outer folds, range in brackets.

**Note on the positives:** a report naming focal slowing does not exclude generalized slowing — 60.9% of focal recordings also carry pathologic generalized slowing. The second block restricts positives to the 39.1% that are exclusively focal.

| positives | comparison group | nested AUROC [fold range] | what it tells us |
|---|---|---|---|
| all focal | clean-normal | **0.785** [0.771–0.802] | can we see focal slowing at all? |
| all focal | clean-normal + generalized | **0.758** [0.744–0.774] | the deployment question: focal against everything else |
| all focal | generalized | **0.635** [0.618–0.650] | can we tell focal *from* generalized? (the hard one) |
| exclusively focal (no pathologic generalized) | clean-normal | **0.758** [0.748–0.775] | can we see focal slowing at all? |
| exclusively focal (no pathologic generalized) | clean-normal + generalized | **0.729** [0.721–0.743] | the deployment question: focal against everything else |
| exclusively focal (no pathologic generalized) | generalized | **0.599** [0.578–0.616] | can we tell focal *from* generalized? (the hard one) |

## Frozen for external confirmation

Coefficients written to `data/derived/sparse_score_coefs.json`. The external test against the 18-expert panel is run by `scripts/104_sparse_score_external.py` with these coefficients **frozen**. Disclosure: OccasionNoise has already been examined with hand-picked scores (scripts/94), so that run is confirmatory, not a first look.

## What is deliberately not modelled

The **band** (delta vs theta vs mixed). Experts agree with one another on band at κ = 0.09–0.38 (`results/moe_band_vs_ours.md`). Fitting an L1 model to a target with that little reliable signal would select noise and dress it in confidence intervals. We report the ceiling and decline the axis.
