# ONE recording-level Morgoth-free model (aggregated features) — report-trained, tested on all

Per-segment features aggregated per recording as {mean,p90,max,prev}; degrades to a single clip. Trained on report-train. MoE truth = canonical Experts-sheet consensus.

| test set | axis | model | AUROC | AP | % under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | ours | 0.733 | 0.626 | – | – |
| report-test | generalized | ours | 0.720 | 0.399 | – | – |
| occasion | focal | ours | 0.924 [0.831, 0.989] | 0.754 | 76% | 76% |
| occasion | generalized | ours | 0.943 [0.890, 0.982] | 0.782 | 61% | 56% |