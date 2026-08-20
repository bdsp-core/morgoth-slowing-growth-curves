# ONE Morgoth-free model — trained on report, tested on report / occasion / MoE

Segment-level, two heads, trained ONLY on report-train. EEG answer = top-5 mean of segment scores (a single clip = its segment). v1 = broadcast labels; v2 = MIL (top-k relabelling).

| test set | axis | model | AUROC | AP | % experts under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | v1 | 0.708 | 0.577 | – | – |
| report-test | focal | v2 | 0.704 | 0.574 | – | – |
| report-test | generalized | v1 | 0.712 | 0.401 | – | – |
| report-test | generalized | v2 | 0.699 | 0.392 | – | – |
| occasion | focal | Morgoth | 0.908 [0.828, 0.974] | 0.665 | 41% | 47% |
| occasion | focal | LENS-v1 | 0.867 [0.757, 0.957] | 0.636 | 24% | 24% |
| occasion | focal | LENS-v2 | 0.852 [0.743, 0.942] | 0.556 | 18% | 12% |
| occasion | generalized | Morgoth | 0.853 [0.750, 0.934] | 0.613 | 11% | 6% |
| occasion | generalized | LENS-v1 | 0.947 [0.900, 0.984] | 0.804 | 61% | 50% |
| occasion | generalized | LENS-v2 | 0.954 [0.908, 0.989] | 0.840 | 83% | 67% |