# ONE recording-level Morgoth-free model (aggregated features) — report-trained, tested on all

Per-segment features aggregated per recording as {mean,p90,max,prev}; degrades to a single clip. Trained on report-train. MoE truth = canonical Experts-sheet consensus.

| test set | axis | model | AUROC | AP | % under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | ours | 0.737 | 0.623 | – | – |
| report-test | generalized | ours | 0.732 | 0.406 | – | – |
| occasion | focal | ours | 0.923 | 0.647 | 47% | 41% |
| occasion | generalized | ours | 0.949 | 0.771 | 61% | 56% |
| moe | focal | Morgoth | 0.949 | – | – | – |
| moe | focal | ours | 0.843 | 0.497 | nan | nan |
| moe | generalized | Morgoth | 0.837 | – | – | – |
| moe | generalized | ours | 0.666 | 0.718 | nan | nan |
| moe_noBS | focal | Morgoth | 0.950 | – | – | – |
| moe_noBS | focal | ours | 0.842 | 0.499 | nan | nan |
| moe_noBS | generalized | Morgoth | 0.853 | – | – | – |
| moe_noBS | generalized | ours | 0.668 | 0.729 | nan | nan |