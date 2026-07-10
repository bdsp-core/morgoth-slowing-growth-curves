# External test of the sparse score S against the 18-expert panel

Coefficients were frozen on the in-cohort data (`scripts/103`). Nothing about these 100 EEGs informed the normal reference, the correlation clusters, the penalty, the L1 selection, or the weights. This script only applies them.

The focal detector is evaluated on the same three questions as in-cohort, using the expert majority on each axis (FN = focal non-epileptiform, GN = generalized non-epileptiform).


## generalized slowing (n = 100 EEGs, expert-majority prevalence 0.19)

- **S (frozen, 3 features): AUROC 0.909 [0.840, 0.962]** vs the expert majority
- hand-picked score (scripts/94): 0.903  |  Morgoth gate: 0.895
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.661** (p = 7.5e-14) — the graded human target
- retained features: `TAR@midline@W` (+0.514), `log_delta@whole_head@N1` (+0.437), `DAR@whole_head@N1` (+0.052)

## focal slowing (n = 100 EEGs, expert-majority prevalence 0.14)

- **S (frozen, 8 features): AUROC 0.848 [0.723, 0.948]** vs the expert majority
- hand-picked score (scripts/94): 0.738  |  Morgoth gate: 0.923
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.451** (p = 2.5e-06) — the graded human target
- retained features: `|asym|@temporal@log_delta@N1` (+0.168), `|asym|@temporal@DAR@N1` (+0.076), `log_delta@L_temporal@N1` (+0.076), `|asym|@parasagittal@log_theta@N1` (+0.044), `|asym|@parasagittal@TAR@N1` (+0.029), `|asym|@parasagittal@DAR@N1` (+0.028), `|asym|@temporal@TAR@N1` (+0.010), `TAR@L_temporal@W` (+0.009)

## The focal detector, evaluated on three different questions (expert majority)

**Note on the positives:** an expert calling focal slowing does not exclude generalized slowing. The second block restricts positives to EEGs the panel called focal and NOT generalized.

| positives | comparison group | AUROC [95% CI] | n |
|---|---|---|---|
| all focal (FN) | no abnormality (all four axes 0) | **0.855** [0.729, 0.957] | 14 vs 40 |
| all focal (FN) | everything else | **0.848** [0.731, 0.946] | 14 vs 86 |
| all focal (FN) | generalized, not focal (GN, not FN) | **0.746** [0.554, 0.909] | 14 vs 18 |
| exclusively focal (FN, not GN) | no abnormality (all four axes 0) | **0.848** [0.718, 0.956] | 13 vs 40 |
| exclusively focal (FN, not GN) | everything else | **0.841** [0.717, 0.953] | 13 vs 86 |
| exclusively focal (FN, not GN) | generalized, not focal (GN, not FN) | **0.739** [0.541, 0.905] | 13 vs 18 |
