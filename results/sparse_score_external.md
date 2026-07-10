# Confirmatory external test of the sparse score S

Coefficients frozen by `scripts/103` on the in-cohort data alone. Nothing about these 100 EEGs informed the reference, the clusters, the penalty, the selection, or the weights.

**Disclosure 1.** OccasionNoise was already examined with hand-picked scores (`scripts/94`). This is confirmatory, not a first look.

**Disclosure 2 — the focal_specific target is POST HOC.** The `focal` model was trained against clean-normals only, and it collapsed here (AUROC 0.611): trained that way, 'focal' is learnable as 'generally slow', and its two largest weights are indeed whole-head and midline terms. That failure is what prompted `focal_specific`, whose negatives include generalized-slowing recordings so the model cannot win on global slowing. The fix is principled — the panel's task (focal vs everything, including generalized) is not the task we had trained — and it was made without inspecting which features would help. **But the decision to make it was triggered by this test set.** The 0.848 below is therefore optimistic and requires independent confirmation on data neither model has seen. We report it as a hypothesis-generating result, not a validated one.


## generalized slowing (n = 100 EEGs, expert-majority prevalence 0.19)

- **S (frozen, 3 features): AUROC 0.909 [0.840, 0.962]** vs the expert majority
- hand-picked score (scripts/94): 0.903  |  Morgoth gate: 0.895
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.661** (p = 7.5e-14) — the graded human target
- retained features: `TAR@midline@W` (+0.514), `log_delta@whole_head@N1` (+0.437), `DAR@whole_head@N1` (+0.052)

## focal slowing (n = 100 EEGs, expert-majority prevalence 0.14)

- **S (frozen, 5 features): AUROC 0.611 [0.424, 0.777]** vs the expert majority
- hand-picked score (scripts/94): 0.738  |  Morgoth gate: 0.923
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.105** (p = 3.0e-01) — the graded human target
- retained features: `log_delta@whole_head@N1` (+0.311), `TAR@midline@W` (+0.188), `|asym|@temporal@log_delta@N1` (+0.093), `|asym|@temporal@DAR@N1` (+0.025), `|asym|@temporal@TAR@N1` (+0.004)

## focal_specific slowing (n = 100 EEGs, expert-majority prevalence 0.14)

- **S (frozen, 8 features): AUROC 0.848 [0.724, 0.946]** vs the expert majority
- (no hand-picked comparator; Morgoth gate on this axis: 0.923)
- **S vs the consensus proportion** (how many of 18 experts saw it): Spearman ρ = **0.450** (p = 2.6e-06) — the graded human target
- retained features: `|asym|@temporal@log_delta@N1` (+0.168), `|asym|@temporal@DAR@N1` (+0.076), `log_delta@L_temporal@N1` (+0.076), `|asym|@parasagittal@log_theta@N1` (+0.044), `|asym|@parasagittal@TAR@N1` (+0.029), `|asym|@parasagittal@DAR@N1` (+0.028), `|asym|@temporal@TAR@N1` (+0.010), `TAR@L_temporal@W` (+0.009)
