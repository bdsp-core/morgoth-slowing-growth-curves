# Honest-wrinkle check — de-confounded focal head: region-only vs finer vs combined (corrected labels)

Same de-confounded focal-specific target (scripts/66), three feature sets, on the held-out OccasionNoise 18-reader panel and the external Sandor_100 (14-expert-vote CORRECTED labels). OccasionNoise 14/95 focal+, Sandor 25/98 focal+.

| de-confounded head | OccasionNoise AUROC [95% CI] / % under | Sandor AUROC [95% CI] / % under |
|---|---|---|
| region-only | 0.937 [0.88, 0.98] / 65% | 0.938 [0.88, 0.98] / 64% |
| finer per-channel | 0.862 [0.73, 0.97] / 29% | 0.898 [0.80, 0.97] / 43% |
| COMBINED (deployed) | 0.921 [0.82, 0.99] / 71% | 0.933 [0.86, 0.98] / 71% |

**Reference (Sandor, corrected):** Morgoth gate 0.974 / 93% under; SCORE-AI 0.878 / 29% under; amount-confounded any-focal region head (scripts/55) 0.946 / 79% under but only 47% on the panel.

**Read.** COMBINED is the most consistent (71%/71%) and highest experts-under on both sets; the finer features add high-specificity behaviour in combination (region-only 64–65%). The 0.946/79% region head wins on Sandor only by leaning on overall slowing amount (amount-confound), which fails in-domain. Production head = COMBINED de-confounded (scripts/66).
