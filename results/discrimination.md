# Discrimination results (age & sex adjusted)

AUC of each feature's normal-referenced z for separating groups. 0.5 = no signal; >0.5 means the group has higher z (more slowing/asymmetry). `auc_raw` = unadjusted (age-confounded) for comparison.

## normal_vs_focal

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| TAR | L_temporal | 0.724 | 0.665 | 9048 |
| TAR | whole_head | 0.720 | 0.659 | 9048 |
| TAR | R_temporal | 0.713 | 0.654 | 9048 |
| TAR | L_parasagittal | 0.712 | 0.657 | 9048 |
| TAR | R_parasagittal | 0.707 | 0.652 | 9048 |
| DAR | L_temporal | 0.682 | 0.631 | 9048 |
| log_theta | whole_head | 0.676 | 0.587 | 9048 |
| DAR | whole_head | 0.675 | 0.625 | 9048 |
| log_delta | whole_head | 0.674 | 0.588 | 9048 |
| DAR | R_temporal | 0.668 | 0.618 | 9048 |
| DAR | L_parasagittal | 0.663 | 0.615 | 9048 |
| log_delta | L_temporal | 0.663 | 0.579 | 9048 |

## normal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| TAR | R_parasagittal | 0.817 | 0.765 | 6720 |
| TAR | whole_head | 0.814 | 0.757 | 6720 |
| TAR | L_parasagittal | 0.814 | 0.760 | 6720 |
| TAR | L_temporal | 0.806 | 0.750 | 6720 |
| TAR | R_temporal | 0.804 | 0.749 | 6720 |
| DAR | L_temporal | 0.793 | 0.741 | 6720 |
| DAR | R_parasagittal | 0.793 | 0.747 | 6720 |
| DAR | whole_head | 0.793 | 0.742 | 6720 |
| DAR | L_parasagittal | 0.790 | 0.742 | 6720 |
| DAR | R_temporal | 0.790 | 0.738 | 6720 |
| log_delta | whole_head | 0.742 | 0.640 | 6720 |
| log_delta | L_parasagittal | 0.738 | 0.632 | 6720 |

## focal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| DAR | R_parasagittal | 0.649 | 0.650 | 5654 |
| TAR | R_parasagittal | 0.641 | 0.645 | 5654 |
| DAR | L_parasagittal | 0.641 | 0.640 | 5654 |
| DAR | whole_head | 0.634 | 0.634 | 5654 |
| DAR | R_temporal | 0.632 | 0.633 | 5654 |
| TAR | L_parasagittal | 0.631 | 0.633 | 5654 |
| TAR | whole_head | 0.626 | 0.629 | 5654 |
| DAR | L_temporal | 0.620 | 0.620 | 5654 |
| TAR | R_temporal | 0.619 | 0.623 | 5654 |
| TAR | L_temporal | 0.606 | 0.609 | 5654 |
| rel_delta | R_parasagittal | 0.606 | 0.602 | 5654 |
| rel_delta | L_parasagittal | 0.598 | 0.593 | 5654 |

