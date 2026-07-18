# Section 0 — Morgoth EEG-level detection vs the expert panel (OccasionNoise, N=100, 18 raters)

Focal and generalized slowing are scored as **separate binary axes** (they co-occur — 29/100 EEGs have a rater marking both). Ground truth = panel majority; each expert is an operating point vs the leave-one-out consensus of the others.

| axis | n pos / N | AUROC | AP | experts | % under ROC | % under PR |
|---|---|---|---|---|---|---|
| focal | 14/100 | 0.905 | 0.656 | 17 | **41%** | **35%** |
| generalized | 19/100 | 0.867 | 0.671 | 18 | **17%** | **17%** |

*MoE (larger, band-resolved panel) pending re-supply of its per-rater labels.*