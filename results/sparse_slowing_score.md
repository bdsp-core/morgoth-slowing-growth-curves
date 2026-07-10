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
| `DAR@whole_head@N1` | +0.051 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `|asym|@parasagittal@TAR@W` (0.52), `TAR@midline@N1` (0.41), `|asym|@parasagittal@DAR@W` (0.33), `|asym|@parasagittal@log_delta@N1` (0.33), `|asym|@parasagittal@log_delta@W` (0.23)

## focal slowing  (n = 3122 positive / 4869 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.868** [0.859, 0.875] across 5 folds
- **Parsimonious frozen model: 5 features**, nested AUROC 0.813 at mean size 3.2 (C = 0.001)
- L1 with the 1-SE rule retains 19 of 34 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.055 AUROC over the parsimonious one

**How few features suffice?** (nested test AUROC vs model size)

| C | mean # features | nested AUROC |
|---|---|---|
| 0.0003 | 0.0 | 0.500 |
| 0.001 | 3.2 | 0.813 |
| 0.003 | 15.6 | 0.860 |
| 0.01 | 17.8 | 0.868 |
| 0.03 | 19.4 | 0.868 |
| 0.1 | 26.0 | 0.870 |
| 0.3 | 28.4 | 0.870 |
| 1 | 30.0 | 0.870 |

| retained feature | coefficient | stability |
|---|---|---|
| `log_delta@whole_head@N1` | +0.311 | 1.00 |
| `TAR@midline@W` | +0.188 | 1.00 |
| `|asym|@temporal@log_delta@N1` | +0.093 | 0.98 |
| `|asym|@temporal@DAR@N1` | +0.025 | 0.95 |
| `|asym|@temporal@TAR@N1` | +0.004 | 0.99 |

Representative features the L1 path *dropped* (stability < 60%): `TAR@L_temporal@N1` (0.54), `DAR@whole_head@W` (0.39), `rel_delta@midline@W` (0.23), `|asym|@temporal@DAR@W` (0.21), `rel_delta@R_temporal@N1` (0.15)

## focal_specific slowing  (n = 3122 positive / 6526 clean-normal)

- **Nested-CV AUROC of the linear predictor: 0.798** [0.771, 0.812] across 5 folds
- **Parsimonious frozen model: 8 features**, nested AUROC 0.745 at mean size 4.8 (C = 0.001)
- L1 with the 1-SE rule retains 20 of 32 correlation-cluster representatives (from ~100 candidates); the dense model buys +0.052 AUROC over the parsimonious one

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
| `|asym|@temporal@DAR@N1` | +0.076 | 0.93 |
| `log_delta@L_temporal@N1` | +0.076 | 0.98 |
| `|asym|@parasagittal@log_theta@N1` | +0.044 | 1.00 |
| `|asym|@parasagittal@TAR@N1` | +0.029 | 0.96 |
| `|asym|@parasagittal@DAR@N1` | +0.028 | 1.00 |
| `|asym|@temporal@TAR@N1` | +0.010 | 0.92 |
| `TAR@L_temporal@W` | +0.009 | 1.00 |

Representative features the L1 path *dropped* (stability < 60%): `DAR@R_temporal@N1` (0.49), `|asym|@parasagittal@log_delta@N1` (0.45), `|asym|@parasagittal@DAR@W` (0.44), `rel_delta@L_temporal@W` (0.43), `rel_delta@midline@W` (0.43)

## Frozen for external confirmation

Coefficients written to `data/derived/sparse_score_coefs.json`. The external test against the 18-expert panel is run by `scripts/104_sparse_score_external.py` with these coefficients **frozen**. Disclosure: OccasionNoise has already been examined with hand-picked scores (scripts/94), so that run is confirmatory, not a first look.

## What is deliberately not modelled

The **band** (delta vs theta vs mixed). Experts agree with one another on band at κ = 0.09–0.38 (`results/moe_band_vs_ours.md`). Fitting an L1 model to a target with that little reliable signal would select noise and dress it in confidence intervals. We report the ceiling and decline the axis.
