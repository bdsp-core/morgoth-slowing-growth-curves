# Morgoth-free wake detector v2 — per-segment intermittency (OccasionNoise, N=100, LOO-CV)

Per-segment wake features aggregated as {mean, p90, max} over wake segments (captures intermittent slowing). Ground truth = panel majority; experts scored vs leave-one-out consensus.

| axis | features | n pos/N | AUROC (LOO) | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|---|
| focal | per-seg L-R asymmetry {mean,p90,max} | 14/100 | 0.748 | 0.422 | 17 | **6%** | **6%** |
| generalized | per-seg whole-head amount {mean,p90,max} | 19/100 | 0.841 | 0.659 | 18 | **28%** | **28%** |