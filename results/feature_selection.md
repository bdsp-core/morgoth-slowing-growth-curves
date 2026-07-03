# Feature selection

Target importances into age/sex-adjusted feature z-scores (40 candidate feature@region columns, n=12008).

## normal_vs_focal (top 15 by RF importance; stability = bootstrap L1 selection freq)
| feature@region | RF imp | L1 |coef| | stability |
|---|---|---|---|
| TAR@L_temporal | 0.084 | 1.22 | 1.00 |
| TAR@whole_head | 0.067 | 0.00 | 0.40 |
| log_theta@whole_head | 0.062 | 1.25 | 0.97 |
| TAR@R_temporal | 0.050 | 0.97 | 1.00 |
| log_theta@L_parasagittal | 0.043 | 0.00 | 0.53 |
| TAR@L_parasagittal | 0.041 | 0.02 | 0.50 |
| TAR@R_parasagittal | 0.037 | 0.52 | 1.00 |
| log_theta@R_temporal | 0.031 | 0.15 | 0.77 |
| log_theta@R_parasagittal | 0.029 | 0.97 | 1.00 |
| log_theta@L_temporal | 0.029 | 0.68 | 1.00 |
| low_freq_rel@L_temporal | 0.028 | 0.00 | 0.40 |
| log_delta@L_temporal | 0.026 | 0.00 | 0.00 |
| log_delta@whole_head | 0.025 | 1.11 | 1.00 |
| rel_theta@L_temporal | 0.023 | 0.76 | 1.00 |
| DTR@R_parasagittal | 0.022 | 0.00 | 0.40 |

## normal_vs_general (top 15 by RF importance; stability = bootstrap L1 selection freq)
| feature@region | RF imp | L1 |coef| | stability |
|---|---|---|---|
| TAR@whole_head | 0.096 | 0.00 | 0.20 |
| TAR@R_parasagittal | 0.095 | 0.90 | 1.00 |
| TAR@L_parasagittal | 0.089 | 0.00 | 0.63 |
| TAR@L_temporal | 0.087 | 0.82 | 1.00 |
| TAR@R_temporal | 0.070 | 0.73 | 1.00 |
| low_freq_rel@L_parasagittal | 0.032 | 0.00 | 0.33 |
| log_theta@whole_head | 0.030 | 1.52 | 1.00 |
| DAR@L_temporal | 0.026 | 0.00 | 0.17 |
| log_delta@L_temporal | 0.025 | 0.00 | 0.23 |
| low_freq_rel@R_parasagittal | 0.025 | 0.00 | 0.33 |
| log_theta@L_parasagittal | 0.023 | 0.00 | 0.07 |
| rel_theta@R_temporal | 0.022 | 0.71 | 1.00 |
| rel_theta@whole_head | 0.022 | 0.04 | 0.70 |
| rel_theta@L_temporal | 0.022 | 0.64 | 1.00 |
| DAR@whole_head | 0.020 | 0.53 | 0.97 |
