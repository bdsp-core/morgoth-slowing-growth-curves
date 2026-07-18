# Table 3 — Descriptor reliability (SAP §10); resolves P3 and P4

Split-half reliability on the completed v6 run: within each recording, usable **W** segments are split into interleaved halves (odd/even segment index, so the halves are matched for time-on-task), each descriptor is computed independently on each half, and ICC(2,1) is taken across **19,181** recordings. Feature: `log_TAR` (whole-head). Normative map: age-conditioned against clean-normal segments in the same stage.

| descriptor                  |   split-half ICC(2,1) |     n | pre-registered threshold   | prediction   | verdict   |
|:----------------------------|----------------------:|------:|:---------------------------|:-------------|:----------|
| amount (median z)           |                 0.991 | 19181 | >= 0.80                    | P3           | CONFIRMED |
| prevalence (frac z > 1.645) |                 0.97  | 19257 | >= 0.80                    | P4           | CONFIRMED |

*Note: the SAP's centile model is GAMLSS/BCT and absolute centiles should be read from it. Split-half reliability is a property of measurement stability — both halves pass through the same normative map, so the choice of map cancels and does not affect these ICCs.*
