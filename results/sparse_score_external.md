# External test of the sparse score S against the 18-expert panel

Coefficients were frozen on the in-cohort data (`scripts/103`). Nothing about these 100 EEGs informed the normal reference, the correlation clusters, the penalty, the L1 selection, or the weights. This script only applies them.

The focal detector is evaluated on the same three questions as in-cohort, using the expert majority on each axis (FN = focal non-epileptiform, GN = generalized non-epileptiform).


## generalized slowing (n = 100 EEGs, expert-majority prevalence 0.19)

- **S (frozen, 3 features): AUROC 0.910 [0.849, 0.960]** vs the expert majority
- hand-picked score (scripts/94): 0.903  |  Morgoth gate: 0.895
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.617** (p = 8.1e-12) — the graded human target
- retained features: `log_delta@whole_head@N1` (+0.384), `TAR@whole_head@W` (+0.303), `|asym|@temporal@log_delta@N1` (+0.064)

## focal slowing (n = 100 EEGs, expert-majority prevalence 0.14)

- **S (frozen, 9 features): AUROC 0.879 [0.767, 0.965]** vs the expert majority
- hand-picked score (scripts/94): 0.738  |  Morgoth gate: 0.923
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.531** (p = 1.4e-08) — the graded human target
- retained features: `|asym|@temporal@log_delta@N1` (+0.170), `log_theta@L_temporal@N1` (+0.155), `|asym|@parasagittal@log_theta@N1` (+0.133), `|asym|@temporal@log_theta@N1` (+0.103), `|asym|@parasagittal@log_delta@N1` (+0.096), `|asym|@temporal@rel_delta@W` (+0.064), `|asym|@parasagittal@rel_delta@W` (+0.036), `|asym|@temporal@TAR@W` (+0.017), `|asym|@temporal@log_delta@W` (+0.001)

## The focal detector, evaluated on three different questions (expert majority)

**Note on the positives:** an expert calling focal slowing does not exclude generalized slowing. The second block restricts positives to EEGs the panel called focal and NOT generalized.

| positives | comparison group | AUROC [95% CI] | n |
|---|---|---|---|
| all focal (FN) | no abnormality (all four axes 0) | **0.870** [0.748, 0.964] | 14 vs 40 |
| all focal (FN) | everything else | **0.879** [0.773, 0.965] | 14 vs 86 |
| all focal (FN) | generalized, not focal (GN, not FN) | **0.829** [0.667, 0.962] | 14 vs 18 |
| exclusively focal (FN, not GN) | no abnormality (all four axes 0) | **0.867** [0.745, 0.964] | 13 vs 40 |
| exclusively focal (FN, not GN) | everything else | **0.875** [0.763, 0.972] | 13 vs 86 |
| exclusively focal (FN, not GN) | generalized, not focal (GN, not FN) | **0.825** [0.650, 0.958] | 13 vs 18 |
