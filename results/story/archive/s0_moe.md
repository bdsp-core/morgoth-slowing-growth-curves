# Section 0b — Morgoth EEG-level detection vs the MoE expert panel (band-resolved, author excluded)

Events collapsed to EEG-level slowing per axis (any band, any round). Ground truth = panel majority; each expert scored vs the leave-one-out consensus of the others. `bwestove` (author) excluded.

| axis | n pos / N | AUROC | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|
| focal | 250/1,761 | 0.935 | 0.788 | 21 | **81%** | **90%** |
| generalized | 1,271/1,761 | 0.734 | 0.877 | 21 | **10%** | **38%** |