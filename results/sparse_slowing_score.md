# The sparse slowing score S

S is the **linear predictor** of an L1-regularised logistic model fit on normative deviations (z-scores), not the probability. The probability saturates near 0 and 1 and destroys grading; the logit is unbounded, linear in the z's, and monotone in evidence.

**S is not the measurement.** `z` is the measurement — unsupervised, fit to nothing but the normal population. `S` is trained to predict the expert's call and therefore inherits the expert's blind spots. S is used for detection and interpretability; it is never used to argue that we see slowing the reader misses. That argument belongs to z (§V4a).

Selection (correlation clustering, C, L1 path, stability) is re-derived **inside each outer training fold**; the normal reference is rebuilt from that fold's clean-normals. Split on patient.


## generalized slowing  (n = 3152 positive / 4869 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.933** [0.922, 0.946] across 5 folds
- **Parsimonious frozen model: 3 features**, nested AUROC 0.908 at mean size 3.0 (C = 0.001)
- L1 with the 1-SE rule retains 24 of 29 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.025 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 3.0 | 0.908 |
| 0.003 | 10.4 | 0.923 |
| 0.01 | 17.6 | 0.931 |
| 0.03 | 22.0 | 0.933 |
| 0.1 | 27.2 | 0.934 |
| 0.3 | 28.0 | 0.934 |
| 1 | 28.0 | 0.934 |

| retained feature | coefficient | stability |
|---|---|---|
| `TAR@midline@W` | +0.514 | 1.00 |
| `log_delta@whole_head@N1` | +0.437 | 0.99 |
| `DAR@whole_head@N1` | +0.052 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `|asym|@parasagittal@TAR@W` (0.52), `TAR@midline@N1` (0.41), `|asym|@parasagittal@DAR@W` (0.33), `|asym|@parasagittal@log_delta@N1` (0.33), `|asym|@parasagittal@log_delta@W` (0.23)

## focal slowing  (n = 3122 positive / 6526 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.798** [0.771, 0.812] across 5 folds
- **Parsimonious frozen model: 8 features**, nested AUROC 0.745 at mean size 4.8 (C = 0.001)
- L1 with the 1-SE rule retains 20 of 32 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.053 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 4.8 | 0.745 |
| 0.003 | 13.2 | 0.794 |
| 0.01 | 17.0 | 0.796 |
| 0.03 | 20.6 | 0.800 |
| 0.1 | 23.6 | 0.801 |
| 0.3 | 26.2 | 0.801 |
| 1 | 27.4 | 0.801 |

| retained feature | coefficient | stability |
|---|---|---|
| `|asym|@temporal@log_delta@N1` | +0.168 | 1.00 |
| `|asym|@temporal@DAR@N1` | +0.076 | 0.90 |
| `log_delta@L_temporal@N1` | +0.076 | 1.00 |
| `|asym|@parasagittal@log_theta@N1` | +0.044 | 1.00 |
| `|asym|@parasagittal@TAR@N1` | +0.029 | 0.98 |
| `|asym|@parasagittal@DAR@N1` | +0.028 | 0.99 |
| `|asym|@temporal@TAR@N1` | +0.010 | 0.91 |
| `TAR@L_temporal@W` | +0.009 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `DAR@R_temporal@N1` (0.57), `|asym|@parasagittal@DAR@W` (0.44), `|asym|@parasagittal@log_delta@N1` (0.41), `|asym|@temporal@rel_delta@W` (0.41), `rel_delta@L_temporal@W` (0.40)

## The focal detector, evaluated on three different questions

One detector (negatives during training = clean-normals **plus** generalized slowing, so it cannot win on global slowing). The three contrasts below use that same score and differ only in which recordings form the comparison group. Nested CV; mean over outer folds, range in brackets.

**Note on the positives:** a report naming focal slowing does not exclude generalized slowing — 60.9% of focal recordings also carry pathologic generalized slowing. The second block restricts positives to the 39.1% that are exclusively focal.

| positives | comparison group | nested AUROC [fold range] | what it tells us |
|---|---|---|---|
| all focal | clean-normal | **0.857** [0.841–0.869] | can we see focal slowing at all? |
| all focal | clean-normal + generalized | **0.798** [0.768–0.813] | the deployment question: focal against everything else |
| all focal | generalized | **0.622** [0.576–0.638] | can we tell focal *from* generalized? (the hard one) |
| exclusively focal (no pathologic generalized) | clean-normal | **0.759** [0.732–0.780] | can we see focal slowing at all? |
| exclusively focal (no pathologic generalized) | clean-normal + generalized | **0.688** [0.645–0.713] | the deployment question: focal against everything else |
| exclusively focal (no pathologic generalized) | generalized | **0.477** [0.415–0.502] | can we tell focal *from* generalized? (the hard one) |

## Frozen for external confirmation

Coefficients written to `data/derived/sparse_score_coefs.json`. The external test against the 18-expert panel is run by `scripts/104_sparse_score_external.py` with these coefficients **frozen**. Disclosure: OccasionNoise has already been examined with hand-picked scores (scripts/94), so that run is confirmatory, not a first look.

## What is deliberately not modelled

The **band** (delta vs theta vs mixed). Experts agree with one another on band at κ = 0.09–0.38 (`results/moe_band_vs_ours.md`). Fitting an L1 model to a target with that little reliable signal would select noise and dress it in confidence intervals. We report the ceiling and decline the axis.
