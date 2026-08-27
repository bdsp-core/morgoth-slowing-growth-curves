# Recording-level top-k aggregation sweep

A recording's score is the mean of its top-k segment scores. The model is trained once; k is varied only at aggregation, so every row uses the identical fitted model.

**generalized** — best on report-test at k=50 (AUROC 0.7052); k=5 gives 0.6924 (Δ -0.0127). Externally k=5 gives 0.9454, best 0.9668.

**focal** — best on report-test at k=50 (AUROC 0.7163); k=5 gives 0.6904 (Δ -0.0258). Externally k=5 gives 0.8022, best 0.8695.

| axis | k | AUROC report-test | AUROC ON-100 |
|---|---|---|---|
| focal | 1 | 0.6547 | 0.7259 |
| focal | 2 | 0.6746 | 0.7550 |
| focal | 3 | 0.6826 | 0.7771 |
| focal | 5 | 0.6904 | 0.8022 |
| focal | 8 | 0.6972 | 0.8133 |
| focal | 10 | 0.6996 | 0.8213 |
| focal | 15 | 0.7036 | 0.8293 |
| focal | 20 | 0.7061 | 0.8303 |
| focal | 30 | 0.7094 | 0.8373 |
| focal | 50 | 0.7163 | 0.8695 |
| generalized | 1 | 0.6734 | 0.8924 |
| generalized | 2 | 0.6825 | 0.9201 |
| generalized | 3 | 0.6878 | 0.9320 |
| generalized | 5 | 0.6924 | 0.9454 |
| generalized | 8 | 0.6958 | 0.9581 |
| generalized | 10 | 0.6974 | 0.9612 |
| generalized | 15 | 0.7003 | 0.9660 |
| generalized | 20 | 0.7010 | 0.9668 |
| generalized | 30 | 0.7001 | 0.9604 |
| generalized | 50 | 0.7052 | 0.9652 |
