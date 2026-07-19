# ONE Morgoth-free model — trained on report, tested on report / occasion / MoE

Segment-level, two heads, trained ONLY on report-train. EEG answer = top-5 mean of segment scores (a single clip = its segment). v1 = broadcast labels; v2 = MIL (top-k relabelling).

| test set | axis | model | AUROC | AP | % experts under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | v1 | 0.694 | 0.546 | – | – |
| report-test | focal | v2 | 0.688 | 0.548 | – | – |
| report-test | generalized | v1 | 0.714 | 0.406 | – | – |
| report-test | generalized | v2 | 0.700 | 0.382 | – | – |
| occasion | focal | Morgoth | 0.908 [0.828, 0.974] | 0.665 | 41% | 47% |
| occasion | focal | LENS-v1 | 0.821 [0.700, 0.931] | 0.493 | 12% | 12% |
| occasion | focal | LENS-v2 | 0.792 [0.666, 0.904] | 0.383 | 6% | 6% |
| occasion | generalized | Morgoth | 0.853 [0.750, 0.934] | 0.613 | 11% | 6% |
| occasion | generalized | LENS-v1 | 0.948 [0.903, 0.985] | 0.814 | 61% | 56% |
| occasion | generalized | LENS-v2 | 0.946 [0.887, 0.990] | 0.772 | 78% | 72% |