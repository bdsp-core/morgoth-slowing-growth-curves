# Recording-level top-k aggregation sweep

A recording's score is the mean of its top-k segment scores. The model is trained once; k is varied only at aggregation, so every row uses the identical fitted model.

**generalized** — best on report-test at k=50 (AUROC 0.7174); k=5 gives 0.6999 (Δ -0.0175). Externally k=5 gives 0.9502, best 0.9763.

**focal** — best on report-test at k=50 (AUROC 0.7039); k=5 gives 0.6878 (Δ -0.0161). Externally k=5 gives 0.7641, best 0.8313.

| axis | k | AUROC report-test | AUROC ON-100 |
|---|---|---|---|
| focal | 1 | 0.6571 | 0.6837 |
| focal | 2 | 0.6737 | 0.7319 |
| focal | 3 | 0.6803 | 0.7620 |
| focal | 5 | 0.6878 | 0.7641 |
| focal | 8 | 0.6931 | 0.7761 |
| focal | 10 | 0.6949 | 0.7771 |
| focal | 15 | 0.6981 | 0.7781 |
| focal | 20 | 0.7000 | 0.7831 |
| focal | 30 | 0.7028 | 0.8092 |
| focal | 50 | 0.7039 | 0.8313 |
| generalized | 1 | 0.6744 | 0.8821 |
| generalized | 2 | 0.6884 | 0.9217 |
| generalized | 3 | 0.6937 | 0.9343 |
| generalized | 5 | 0.6999 | 0.9502 |
| generalized | 8 | 0.7053 | 0.9628 |
| generalized | 10 | 0.7073 | 0.9684 |
| generalized | 15 | 0.7104 | 0.9691 |
| generalized | 20 | 0.7113 | 0.9699 |
| generalized | 30 | 0.7123 | 0.9763 |
| generalized | 50 | 0.7174 | 0.9699 |
