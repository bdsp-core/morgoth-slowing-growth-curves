# Discrimination results (age & sex adjusted)

AUC of each feature's normal-referenced z for separating groups. 0.5 = no signal; >0.5 means the group has higher z (more slowing/asymmetry). `auc_raw` = unadjusted (age-confounded) for comparison.

## normal_vs_focal

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| TAR | L_temporal | 0.719 | 0.652 | 5359 |
| TAR | whole_head | 0.716 | 0.646 | 5359 |
| TAR | L_parasagittal | 0.708 | 0.642 | 5359 |
| TAR | R_temporal | 0.706 | 0.641 | 5359 |
| TAR | R_parasagittal | 0.704 | 0.639 | 5359 |
| log_theta | whole_head | 0.677 | 0.586 | 5359 |
| |asym_ch_T3-T5_delta| | asym | 0.672 |  | 5359 |
| DAR | L_temporal | 0.665 | 0.607 | 5359 |
| log_theta | L_parasagittal | 0.661 | 0.572 | 5359 |
| log_delta | whole_head | 0.658 | 0.571 | 5359 |
| DAR | whole_head | 0.656 | 0.599 | 5359 |
| log_theta | L_temporal | 0.656 | 0.571 | 5359 |

## normal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| TAR | R_parasagittal | 0.643 | 0.623 | 8454 |
| TAR | whole_head | 0.641 | 0.619 | 8454 |
| TAR | R_temporal | 0.638 | 0.617 | 8454 |
| TAR | L_parasagittal | 0.638 | 0.617 | 8454 |
| TAR | L_temporal | 0.638 | 0.617 | 8454 |
| DAR | R_parasagittal | 0.600 | 0.585 | 8454 |
| low_freq_rel | R_parasagittal | 0.599 | 0.581 | 8454 |
| DAR | L_temporal | 0.599 | 0.583 | 8454 |
| DAR | R_temporal | 0.599 | 0.582 | 8454 |
| DAR | whole_head | 0.598 | 0.582 | 8454 |
| low_freq_rel | whole_head | 0.597 | 0.580 | 8454 |
| low_freq_rel | L_parasagittal | 0.596 | 0.578 | 8454 |

## focal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| log_theta | whole_head | 0.416 | 0.479 | 8779 |
| log_delta | L_temporal | 0.416 | 0.475 | 8779 |
| TAR | L_temporal | 0.417 | 0.467 | 8779 |
| log_theta | L_temporal | 0.417 | 0.476 | 8779 |
| log_delta | whole_head | 0.418 | 0.480 | 8779 |
| TAR | whole_head | 0.426 | 0.478 | 8779 |
| log_theta | L_parasagittal | 0.427 | 0.489 | 8779 |
| TAR | L_parasagittal | 0.431 | 0.480 | 8779 |
| log_theta | R_temporal | 0.431 | 0.489 | 8779 |
| DAR | L_temporal | 0.431 | 0.474 | 8779 |
| TAR | R_temporal | 0.432 | 0.482 | 8779 |
| rel_delta | L_temporal | 0.433 | 0.470 | 8779 |

