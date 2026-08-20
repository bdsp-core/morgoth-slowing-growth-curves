# Does the fitted median track the data? (mu spline df sweep)

Median |fitted median − rolling median| as a fraction of that cell's own p25–p75 width, over all feature × stage cells. Lower is better; >0.25 means the fitted median is off by more than a quarter of the interquartile range, which is visible in the figure.

| mu df | infant (2mo-1y) | child (1-20y) | adult (>20y) |
|---|---|---|---|
| 9 | 1.37 | 0.09 | 0.04 |
| 20 | 0.53 | 0.06 | 0.04 |

## Worst cells per mu df (infant band)

| mu df | feature | stage | infant | child | adult |
|---|---|---|---|---|---|
| 9 | DAR | REM | 1.37 | 0.02 | 0.01 |
| 9 | DAR | W | 0.97 | 0.02 | 0.00 |
| 9 | TAR | REM | 0.60 | 0.04 | 0.01 |
| 20 | DAR | REM | 0.53 | 0.02 | 0.01 |
| 20 | DAR | N2 | 0.25 | 0.04 | 0.01 |
| 20 | DAR | W | 0.24 | 0.01 | 0.00 |
