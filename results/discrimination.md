# Discrimination results (age & sex adjusted)

AUC of each feature's normal-referenced z for separating groups. 0.5 = no signal; >0.5 means the group has higher z (more slowing/asymmetry). `auc_raw` = unadjusted (age-confounded) for comparison.

## normal_vs_focal

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| TAR | L_temporal | 0.704 | 0.637 | 6980 |
| TAR | whole_head | 0.697 | 0.629 | 6980 |
| |asym_ch_T3-T5_delta| | asym | 0.696 |  | 6980 |
| TAR | R_temporal | 0.687 | 0.622 | 6980 |
| TAR | L_parasagittal | 0.686 | 0.624 | 6980 |
| |asym_temporal_delta| | asym | 0.682 |  | 6980 |
| log_theta | whole_head | 0.681 | 0.584 | 6980 |
| TAR | R_parasagittal | 0.679 | 0.616 | 6980 |
| log_theta | L_parasagittal | 0.661 | 0.569 | 6980 |
| log_theta | L_temporal | 0.659 | 0.572 | 6980 |
| |asym_ch_C3-P3_delta| | asym | 0.652 |  | 6980 |
| |asym_parasagittal_delta| | asym | 0.648 |  | 6980 |

## normal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| TAR | whole_head | 0.727 | 0.695 | 10294 |
| TAR | R_parasagittal | 0.725 | 0.696 | 10294 |
| TAR | L_temporal | 0.725 | 0.694 | 10294 |
| TAR | L_parasagittal | 0.724 | 0.695 | 10294 |
| TAR | R_temporal | 0.720 | 0.689 | 10294 |
| DAR | L_temporal | 0.675 | 0.650 | 10294 |
| DAR | whole_head | 0.673 | 0.649 | 10294 |
| low_freq_rel | L_parasagittal | 0.673 | 0.637 | 10294 |
| DAR | R_parasagittal | 0.671 | 0.649 | 10294 |
| DAR | L_parasagittal | 0.671 | 0.648 | 10294 |
| DAR | R_temporal | 0.671 | 0.647 | 10294 |
| low_freq_rel | R_parasagittal | 0.668 | 0.633 | 10294 |

## focal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| DAR | R_parasagittal | 0.578 | 0.610 | 7446 |
| DAR | L_parasagittal | 0.571 | 0.603 | 7446 |
| low_freq_rel | R_parasagittal | 0.569 | 0.604 | 7446 |
| rel_delta | R_parasagittal | 0.568 | 0.598 | 7446 |
| DAR | R_temporal | 0.567 | 0.600 | 7446 |
| rel_delta | L_parasagittal | 0.563 | 0.594 | 7446 |
| low_freq_rel | L_parasagittal | 0.561 | 0.597 | 7446 |
| DAR | whole_head | 0.559 | 0.594 | 7446 |
| TAR | R_parasagittal | 0.558 | 0.599 | 7446 |
| DTR | L_parasagittal | 0.555 | 0.568 | 7446 |
| DTR | R_parasagittal | 0.552 | 0.566 | 7446 |
| rel_delta | R_temporal | 0.552 | 0.578 | 7446 |

