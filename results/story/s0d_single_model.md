# ONE Morgoth-free model — trained on report, tested on report / occasion / MoE

Segment-level, two heads, trained ONLY on report-train. EEG answer = top-5 mean of segment scores (a single clip = its segment). v1 = broadcast labels; v2 = MIL (top-k relabelling).

| test set | axis | model | AUROC | AP | % experts under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | v1 | 0.709 | 0.577 | – | – |
| report-test | focal | v2 | 0.706 | 0.580 | – | – |
| report-test | generalized | v1 | 0.714 | 0.400 | – | – |
| report-test | generalized | v2 | 0.701 | 0.390 | – | – |
| occasion | focal | Morgoth | 0.908 [0.828, 0.974] | 0.665 | 41% | 47% |
| occasion | focal | LENS-v1 | 0.865 [0.755, 0.958] | 0.662 | 18% | 29% |
| occasion | focal | LENS-v2 | 0.852 [0.745, 0.940] | 0.547 | 18% | 12% |
| occasion | generalized | Morgoth | 0.853 [0.750, 0.934] | 0.613 | 11% | 6% |
| occasion | generalized | LENS-v1 | 0.951 [0.907, 0.986] | 0.825 | 67% | 50% |
| occasion | generalized | LENS-v2 | 0.961 [0.914, 0.994] | 0.871 | 83% | 78% |