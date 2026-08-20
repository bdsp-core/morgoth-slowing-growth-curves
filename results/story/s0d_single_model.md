# ONE Morgoth-free model — trained on report, tested on report / occasion / MoE

Segment-level, two heads, trained ONLY on report-train. EEG answer = top-5 mean of segment scores (a single clip = its segment). v1 = broadcast labels; v2 = MIL (top-k relabelling).

| test set | axis | model | AUROC | AP | % experts under ROC | % under PR |
|---|---|---|---|---|---|---|
| report-test | focal | v1 | 0.712 | 0.582 | – | – |
| report-test | focal | v2 | 0.717 | 0.590 | – | – |
| report-test | generalized | v1 | 0.720 | 0.406 | – | – |
| report-test | generalized | v2 | 0.721 | 0.405 | – | – |
| occasion | focal | Morgoth | 0.908 [0.828, 0.974] | 0.665 | 41% | 47% |
| occasion | focal | LENS-v1 | 0.847 [0.731, 0.949] | 0.631 | 24% | 18% |
| occasion | focal | LENS-v2 | 0.833 [0.719, 0.934] | 0.512 | 24% | 18% |
| occasion | generalized | Morgoth | 0.853 [0.750, 0.934] | 0.613 | 11% | 6% |
| occasion | generalized | LENS-v1 | 0.949 [0.902, 0.985] | 0.816 | 61% | 56% |
| occasion | generalized | LENS-v2 | 0.971 [0.933, 0.997] | 0.911 | 94% | 89% |