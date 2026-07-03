# Discrimination results (age & sex adjusted)

AUC of each feature's normal-referenced z for separating groups. 0.5 = no signal; >0.5 means the group has higher z (more slowing/asymmetry). `auc_raw` = unadjusted (age-confounded) for comparison.

## normal_vs_focal

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| log_delta | L_temporal | 0.741 | 0.636 | 6980 |
| log_theta | whole_head | 0.740 | 0.636 | 6980 |
| log_delta | whole_head | 0.736 | 0.623 | 6980 |
| log_theta | L_temporal | 0.730 | 0.640 | 6980 |
| log_theta | L_parasagittal | 0.726 | 0.627 | 6980 |
| log_theta | R_temporal | 0.720 | 0.629 | 6980 |
| TAR | L_temporal | 0.715 | 0.660 | 6980 |
| log_theta | R_parasagittal | 0.715 | 0.616 | 6980 |
| log_delta | R_temporal | 0.715 | 0.610 | 6980 |
| log_delta | L_parasagittal | 0.711 | 0.607 | 6980 |
| |asym_temporal_delta| | asym | 0.708 |  | 6980 |
| TAR | whole_head | 0.700 | 0.641 | 6980 |

## normal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| log_delta | whole_head | 0.752 | 0.682 | 10294 |
| log_delta | L_temporal | 0.741 | 0.675 | 10294 |
| log_delta | L_parasagittal | 0.740 | 0.675 | 10294 |
| log_delta | R_parasagittal | 0.736 | 0.673 | 10294 |
| log_delta | R_temporal | 0.736 | 0.668 | 10294 |
| TAR | L_temporal | 0.729 | 0.714 | 10294 |
| TAR | whole_head | 0.728 | 0.711 | 10294 |
| TAR | R_temporal | 0.723 | 0.712 | 10294 |
| log_theta | L_parasagittal | 0.715 | 0.655 | 10294 |
| log_theta | R_parasagittal | 0.715 | 0.656 | 10294 |
| log_theta | whole_head | 0.711 | 0.651 | 10294 |
| TAR | L_parasagittal | 0.703 | 0.687 | 10294 |

## focal_vs_general

| feature | region | AUC (adj) | AUC (raw) | n |
|---|---|---|---|---|
| DAR | R_temporal | 0.577 | 0.598 | 7446 |
| DAR | whole_head | 0.573 | 0.594 | 7446 |
| DTR | R_temporal | 0.565 | 0.557 | 7446 |
| DAR | R_parasagittal | 0.563 | 0.578 | 7446 |
| DAR | L_parasagittal | 0.562 | 0.579 | 7446 |
| DTR | whole_head | 0.559 | 0.548 | 7446 |
| TAR | R_parasagittal | 0.553 | 0.583 | 7446 |
| DAR | L_temporal | 0.553 | 0.577 | 7446 |
| DTR | L_temporal | 0.551 | 0.541 | 7446 |
| TAR | whole_head | 0.550 | 0.587 | 7446 |
| TAR | R_temporal | 0.548 | 0.583 | 7446 |
| rel_delta | R_temporal | 0.548 | 0.568 | 7446 |

