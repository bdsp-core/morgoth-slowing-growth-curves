# ONE recording-level Morgoth-free model (aggregated features) — report-trained, tested on all

Per-segment features aggregated per recording as {mean,p90,max,prev}; degrades to a single clip. Trained on report-train. MoE truth = canonical Experts-sheet consensus.

| test set | axis | model | AUROC | AP | % under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | ours | 0.737 | 0.628 | – | – |
| report-test | generalized | ours | 0.717 | 0.391 | – | – |
| occasion | focal | ours | 0.909 [0.820, 0.977] | 0.658 | 59% | 53% |
| occasion | generalized | ours | 0.937 [0.884, 0.979] | 0.756 | 39% | 33% |