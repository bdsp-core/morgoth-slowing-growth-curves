# Severity robustness sweep (does ANY parameterisation recover the adjective?)

**72 combinations** of feature x normalization x stratum x statistic. Largest |rho| anywhere is **0.182** (DAR, raw, all, MAX; p = 2.8e-19, n = 2,393). Bonferroni threshold at 72 tests is p < 0.00069; **61** combination(s) clear it.

| feature | normalization | stratum | statistic | rho | p | n |
|---|---|---|---|---|---|---|
| DAR | raw | all | MAX | +0.182 | 2.8e-19 | 2,393 |
| DAR | raw | all | P95 | +0.182 | 3.6e-19 | 2,393 |
| DAR | raw | N3 | P95 | +0.169 | 7.2e-08 | 1,007 |
| DAR | raw | N3 | MAX | +0.167 | 9.8e-08 | 1,007 |
| rel_delta | raw | all | P95 | +0.161 | 2.7e-15 | 2,393 |
| rel_delta | raw | all | MAX | +0.157 | 9.6e-15 | 2,393 |
| rel_delta | raw | N1 | P95 | +0.154 | 2.9e-13 | 2,221 |
| TAR | raw | all | P95 | +0.153 | 5e-14 | 2,393 |
| rel_delta | raw | N1 | MAX | +0.152 | 5.6e-13 | 2,221 |
| DAR | raw | N1 | P95 | +0.151 | 8.4e-13 | 2,221 |
| TAR | raw | all | MAX | +0.151 | 1.3e-13 | 2,393 |
| DAR | raw | N1 | MAX | +0.150 | 1.3e-12 | 2,221 |
| TAR | raw | N3 | P95 | +0.137 | 1.2e-05 | 1,007 |
| TAR | raw | N3 | MAX | +0.135 | 1.7e-05 | 1,007 |
| rel_delta | raw | REM | P95 | +0.133 | 3.5e-09 | 1,966 |
| TAR | raw | N2 | P95 | +0.131 | 4.8e-09 | 1,975 |
| TAR | raw | N2 | MAX | +0.131 | 5.2e-09 | 1,975 |
| DAR | raw | N2 | P95 | +0.130 | 5.9e-09 | 1,975 |
| rel_delta | raw | REM | MAX | +0.128 | 1.1e-08 | 1,966 |
| DAR | raw | N2 | MAX | +0.128 | 1.1e-08 | 1,975 |
