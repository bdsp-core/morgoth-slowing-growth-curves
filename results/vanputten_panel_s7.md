# Figure S7 — van Putten vs LENS vs Morgoth on the CLEAN ON-100 expert panel (fair benchmark; expert-majority labels)

LENS = production code path (gen: scripts/54 MIL top-5; focal: scripts/66), identical to Figure 2. van Putten = best index per axis recomputed on the panel. Recording-level bootstrap 95% CIs.

| axis | method | AUROC [95% CI] | % experts under ROC |
|---|---|---|---|
| focal | best van Putten index (asym_rel_delta) | 0.825 [0.717, 0.923] | 12% |
| focal | LENS | 0.921 [0.824, 0.988] | 71% |
| focal | Morgoth | 0.908 [0.828, 0.974] | 41% |
| generalized | best van Putten index (DAR) | 0.817 [0.707, 0.913] | 11% |
| generalized | LENS | 0.946 [0.887, 0.990] | 78% |
| generalized | Morgoth | 0.853 [0.750, 0.934] | 11% |