# Feature selection

Target importances into age/sex-adjusted feature z-scores (40 candidate feature@region columns, n=12008).

## normal_vs_focal (top 15 by RF importance; stability = bootstrap L1 selection freq)
| feature@region | RF imp | L1 |coef| | stability |
|---|---|---|---|
| TAR@L_temporal | 0.083 | 1.09 | 1.00 |
| TAR@whole_head | 0.068 | 0.00 | 0.03 |
| log_theta@whole_head | 0.062 | 0.45 | 0.83 |
| TAR@R_temporal | 0.053 | 0.73 | 1.00 |
| TAR@L_parasagittal | 0.044 | 0.09 | 0.53 |
| log_theta@L_parasagittal | 0.040 | 0.00 | 0.10 |
| TAR@R_parasagittal | 0.038 | 0.78 | 1.00 |
| log_delta@L_temporal | 0.036 | 0.00 | 0.00 |
| log_delta@whole_head | 0.031 | 1.84 | 1.00 |
| log_theta@R_parasagittal | 0.030 | 0.96 | 1.00 |
| log_theta@L_temporal | 0.026 | 0.54 | 1.00 |
| log_theta@R_temporal | 0.025 | 0.02 | 0.67 |
| DAR@R_parasagittal | 0.025 | 0.66 | 0.97 |
| DAR@R_temporal | 0.024 | 0.74 | 1.00 |
| log_delta@R_temporal | 0.024 | 0.16 | 0.37 |

## normal_vs_general (top 15 by RF importance; stability = bootstrap L1 selection freq)
| feature@region | RF imp | L1 |coef| | stability |
|---|---|---|---|
| TAR@R_parasagittal | 0.101 | 0.80 | 1.00 |
| TAR@whole_head | 0.099 | 0.00 | 0.13 |
| TAR@L_parasagittal | 0.096 | 0.12 | 0.90 |
| TAR@L_temporal | 0.089 | 0.84 | 1.00 |
| TAR@R_temporal | 0.071 | 0.79 | 1.00 |
| DAR@L_temporal | 0.039 | 0.00 | 0.27 |
| log_theta@whole_head | 0.030 | 1.43 | 1.00 |
| DAR@R_temporal | 0.029 | 0.65 | 1.00 |
| log_delta@whole_head | 0.026 | 1.43 | 1.00 |
| DAR@L_parasagittal | 0.025 | 0.22 | 0.80 |
| log_delta@L_temporal | 0.024 | 0.00 | 0.13 |
| log_delta@R_temporal | 0.023 | 0.00 | 0.23 |
| DAR@whole_head | 0.022 | 0.83 | 1.00 |
| rel_theta@R_temporal | 0.022 | 0.81 | 1.00 |
| rel_theta@L_temporal | 0.022 | 0.58 | 1.00 |

## distill_MORGOTH_abnormal (top 15 by RF importance; stability = bootstrap L1 selection freq)
| feature@region | RF imp | L1 |coef| | stability |
|---|---|---|---|
| TAR@whole_head | 0.111 | 0.01 | 0.57 |
| TAR@L_temporal | 0.104 | 0.75 | 1.00 |
| DAR@L_temporal | 0.076 | 0.00 | 0.37 |
| TAR@R_parasagittal | 0.074 | 0.74 | 1.00 |
| TAR@L_parasagittal | 0.069 | 0.07 | 0.87 |
| TAR@R_temporal | 0.067 | 0.56 | 1.00 |
| log_delta@whole_head | 0.044 | 4.29 | 1.00 |
| DAR@R_temporal | 0.041 | 0.00 | 0.50 |
| DAR@whole_head | 0.035 | 0.88 | 1.00 |
| log_delta@L_temporal | 0.031 | 0.57 | 0.80 |
| log_theta@whole_head | 0.028 | 3.09 | 1.00 |
| DAR@L_parasagittal | 0.027 | 0.06 | 0.73 |
| log_delta@L_parasagittal | 0.026 | 0.95 | 1.00 |
| log_delta@R_temporal | 0.024 | 1.28 | 1.00 |
| DAR@R_parasagittal | 0.024 | 0.21 | 0.73 |
