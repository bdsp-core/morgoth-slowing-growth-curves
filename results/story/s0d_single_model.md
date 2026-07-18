# ONE Morgoth-free model — trained on report, tested on report / occasion / MoE

Segment-level, two heads, trained ONLY on report-train. EEG answer = top-5 mean of segment scores (a single clip = its segment). v1 = broadcast labels; v2 = MIL (top-k relabelling).

| test set | axis | model | AUROC | AP | % experts under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | v1 | 0.690 | 0.538 | – | – |
| report-test | focal | v2 | 0.681 | 0.540 | – | – |
| report-test | generalized | v1 | 0.710 | 0.401 | – | – |
| report-test | generalized | v2 | 0.676 | 0.358 | – | – |
| occasion | focal | Morgoth | 0.908 | 0.665 | 41% | 47% |
| occasion | focal | ours-v1 | 0.825 | 0.485 | 18% | 12% |
| occasion | focal | ours-v2 | 0.832 | 0.528 | 12% | 12% |
| occasion | generalized | Morgoth | 0.853 | 0.613 | 11% | 6% |
| occasion | generalized | ours-v1 | 0.941 | 0.765 | 61% | 50% |
| occasion | generalized | ours-v2 | 0.937 | 0.749 | 67% | 78% |
| moe | focal | Morgoth | 0.932 | 0.781 | 86% | 90% |
| moe | focal | ours-v1 | 0.862 | 0.493 | 24% | 19% |
| moe | focal | ours-v2 | 0.841 | 0.483 | 14% | 19% |
| moe | generalized | Morgoth | 0.732 | 0.881 | 14% | 43% |
| moe | generalized | ours-v1 | 0.632 | 0.843 | 0% | 33% |
| moe | generalized | ours-v2 | 0.614 | 0.827 | 0% | 29% |