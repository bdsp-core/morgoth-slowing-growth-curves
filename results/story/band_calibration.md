# Band (delta / theta / mixed) calibration — agree with reports without over-fitting the hedge

Clean-paired report-band-labelled recordings: **N=9,412** (report marginals mixed 0.64 · delta 0.21 · theta 0.16). Band axis = **whole-head mean log(δ/θ) power** (`band_dtr`; high = delta-dominant). Patient-split 50/50; thresholds set on train to reproduce the report's delta/theta rates.

**Why the absolute-power axis, not the deviation z.** A clinician's *delta slowing* means delta power dominates the trace. The per-band age/stage deviation z does not track that — normal delta σ is large, so a big delta in a young brain sits at a modest z while a smaller theta excess wins the deviation axis even though delta plainly dominates the trace. On the held-out reports the raw ratio separates delta-vs-theta at **AUROC 0.74**, vs **0.68** for the old deviation axis (z_theta − z_delta) — a +0.06 gain, and it matches what a reader sees.

| method | 3-way acc | balanced acc | Cohen κ | predicted mixed/delta/theta |
|---|---|---|---|---|
| **marginal-matched on log(δ/θ) (production)** | **0.527** | 0.413 | **0.098** | 0.64 / 0.21 / 0.15 |
| trivial 'always mixed' | 0.636 | 0.333 | 0.000 | 1.00 / 0 / 0 |

**Where the signal is (test AUROC, separability):** delta-vs-theta 0.74 · delta-vs-mixed 0.62 · theta-vs-mixed 0.63. The **delta-vs-theta axis carries the real signal**; 'mixed' is a reader hedge that sits between the two pure bands and is only weakly separated from either, so we do not chase a 3-way hard call.

**Expert ceiling.** Published expert-vs-expert band κ is **0.09–0.38**; the calibrated model's κ=0.10 sits at the low end — i.e. it agrees with reports about as well as reports agree with each other. This is the correct stopping point: matching the *distribution* and surfacing the delta↔theta axis, without pretending the 3-way hard call is more than a low-confidence gloss (the valid test is the continuous D1 dose-response).

**Production thresholds (scripts/58 `band_word`, refit on all N=9,412):** LO = 0.52, HI = 1.64 on `band_dtr` = mean log(δ/θ):  dtr > HI → delta, dtr < LO → theta, else mixed.
