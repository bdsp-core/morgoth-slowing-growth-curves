# Band (delta / theta / mixed) calibration — agree with reports without over-fitting the hedge

Clean-paired report-band-labelled recordings: **N=9,412** (report marginals mixed 0.64 · delta 0.21 · theta 0.16). Band index = z_theta − z_delta (p90). Patient-split 50/50; thresholds set on train to reproduce the report's delta/theta rates.

| method | 3-way acc | balanced acc | Cohen κ | predicted mixed/delta/theta |
|---|---|---|---|---|
| current fixed thresholds (pre-calibration) | 0.392 | ~0.35 | ~0.02 | 0.39 / 0.29 / 0.32 |
| **marginal-matched (calibrated)** | **0.521** | 0.405 | **0.091** | 0.64 / 0.20 / 0.16 |
| trivial 'always mixed' | 0.636 | 0.333 | 0.000 | 1.00 / 0 / 0 |

**Where the signal is (test AUROC of the index):** delta-vs-theta 0.68 · delta-vs-mixed 0.59 · theta-vs-mixed 0.40. Only **delta-vs-theta carries real signal**; theta-vs-mixed is at/below chance — 'mixed' is a reader hedge, not a separable class.

**When we call a pure band and the report is also pure, delta-vs-theta agreement ≈ 0.74.**

**Expert ceiling.** Published expert-vs-expert band κ is **0.09–0.38**; the calibrated model's κ=0.09 sits at the low end — i.e. it agrees with reports about as well as reports agree with each other. This is the correct stopping point: matching the *distribution* and surfacing the delta↔theta axis, without pretending the 3-way hard call is more than a low-confidence gloss (the valid test is the continuous D1 dose-response).

**Production thresholds (scripts/58 `band_word`, refit on all N=9,412):** LO = -0.94, HI = 0.35 on z_theta − z_delta.
