# Figure S1 — severity is a null result (regenerated on v6)

Our continuous deviation score against the reader's own **mild / moderate / marked** adjective, on **2,393** cleanly-paired recordings. Two summary statistics are compared: the fragile **MAX** over each recording's region×stage deviation cells (one artifactual cell can set it) and a robust **P95**. If the adjective carried quantitative information, at least the robust version should track it.

| statistic | Spearman ρ | p (ρ) | Kruskal–Wallis p | median \|z\| mild → moderate → marked | n |
|---|---|---|---|---|---|
| MAX | +0.107 | 1.5e-07 | 1.5e-19 | 1.13 → 1.15 → 2.58 | 2,393 |
| P95 | +0.101 | 6.6e-07 | 2.2e-19 | 1.03 → 1.04 → 2.20 | 2,393 |

**The result replicates on v6, and it is worth stating precisely.** The association is *statistically detectable but negligible* (ρ ≈ 0.10; with n ≈ 2,400 even a trivial effect clears p < 1e-6, so the p-value is not the story). The structure is the point: **mild and moderate are indistinguishable** (median |z| 1.13 vs 1.15) and only the small `marked` tail (n = 128) is elevated (2.58). An adjective that cannot separate its own two most common levels is not a quantitative grading, and replacing the max-statistic with a robust upper quantile does not rescue it (ρ 0.107 → 0.101).

We therefore claim no severity grading anywhere in the paper. What the score *does* track is **conspicuity** — how many independent experts saw the slowing at all (Spearman ρ ≈ 0.62, `results/table5_human_ceiling.md`). It is the adjective, not the measurement, that is unreliable.
