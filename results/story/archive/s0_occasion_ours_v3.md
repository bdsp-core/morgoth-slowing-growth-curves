# Morgoth-free detector v3 — WAKE + N1, stage-matched deviation (OccasionNoise, N=100, LOO-CV)

W and N1 segments, each turned into a stage-matched deviation z (physiologic drowsy slowing normalized out). Ground truth = panel majority; experts scored vs leave-one-out consensus.

| axis | features | n pos/N | AUROC (LOO) | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|---|
| focal | W+N1 stage-matched z | 14/100 | 0.875 | 0.683 | 17 | **29%** | **24%** |
| generalized | W+N1 stage-matched z | 19/100 | 0.898 | 0.737 | 18 | **39%** | **28%** |