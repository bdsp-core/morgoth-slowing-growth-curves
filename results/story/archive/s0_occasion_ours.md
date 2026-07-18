# Can a Morgoth-FREE wake-segment classifier beat the experts? (OccasionNoise, N=100)

L2 logistic on WAKE spectral features only, leave-one-out CV. Ground truth = panel majority; each expert an operating point vs the leave-one-out consensus of the others.

| axis | features | n pos/N | AUROC (LOO) | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|---|
| focal | wake L-R asymmetry + amount | 14/100 | 0.850 | 0.585 | 17 | **24%** | **18%** |
| generalized | wake whole-head amount | 19/100 | 0.805 | 0.563 | 18 | **28%** | **22%** |