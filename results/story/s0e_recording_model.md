# ONE recording-level Morgoth-free model (aggregated features) — report-trained, tested on all

Per-segment features aggregated per recording as {mean,p90,max,prev}; degrades to a single clip. Trained on report-train. MoE truth = canonical Experts-sheet consensus.

| test set | axis | model | AUROC | AP | % under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | ours | 0.737 | 0.623 | – | – |
| report-test | generalized | ours | 0.732 | 0.406 | – | – |
| occasion | focal | ours | 0.921 [0.824, 0.988] | 0.776 | 71% | 65% |
| occasion | generalized | ours | 0.949 [0.903, 0.984] | 0.771 | 61% | 56% |