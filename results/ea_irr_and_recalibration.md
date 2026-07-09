# Expert-algorithm IRR vs expert-expert IRR, and recalibrating the gate

An algorithm can agree with each expert *better than experts agree with each other*, because two 
noisy raters compound two error sources while an accurate algorithm carries one. If experts were 
(truth + independent noise), an algorithm at the truth would score **κ_ae ≈ √κ_ee**. Expert errors 
are correlated (shared training, shared blind spots), which inflates κ_ee and makes √κ_ee a 
**conservative** target.

Thresholds and Platt coefficients are fitted **leave-one-out**; no EEG informs its own call. 
Morgoth's AUROC is threshold-free and unchanged by recalibration — only the operating point moves.


## focal slowing  (n = 98 EEGs, 14 experts, prevalence 0.14)

**Morgoth AUROC vs expert majority: 0.923** (threshold-free).

| calls | bal. accuracy vs majority | sens | spec | κ vs each expert (median [IQR]) |
|---|---|---|---|---|
| Morgoth, shipped threshold | 0.714 | 0.429 | 1.000 | 0.376 [0.325–0.444] |
| Morgoth, LOO Platt @0.5 | 0.780 | 0.571 | 0.988 | 0.426 [0.368–0.470] |
| Morgoth, LOO Youden threshold | 0.845 | 0.714 | 0.976 | 0.471 [0.424–0.530] |
| *average expert vs consensus* | *0.815* | — | — | *0.403 [0.316–0.457]* (expert–expert) |

- expert–expert κ median **0.403**; attenuation benchmark √κ_ee = **0.635**
- Morgoth (LOO Youden) vs each expert: κ median **0.471**
- difference κ_ae − κ_ee = **+0.068** [95% CI +0.014, +0.136] → **ea-IRR exceeds ee-IRR**

## generalized slowing  (n = 98 EEGs, 14 experts, prevalence 0.18)

**Morgoth AUROC vs expert majority: 0.895** (threshold-free).

| calls | bal. accuracy vs majority | sens | spec | κ vs each expert (median [IQR]) |
|---|---|---|---|---|
| Morgoth, shipped threshold | 0.667 | 0.333 | 1.000 | 0.289 [0.266–0.334] |
| Morgoth, LOO Platt @0.5 | 0.747 | 0.556 | 0.938 | 0.372 [0.330–0.415] |
| Morgoth, LOO Youden threshold | 0.814 | 0.778 | 0.850 | 0.481 [0.383–0.530] |
| *average expert vs consensus* | *0.808* | — | — | *0.500 [0.394–0.563]* (expert–expert) |

- expert–expert κ median **0.500**; attenuation benchmark √κ_ee = **0.707**
- Morgoth (LOO Youden) vs each expert: κ median **0.481**
- difference κ_ae − κ_ee = **-0.019** [95% CI -0.123, +0.039] → not distinguishable from zero

## Reading this

Recalibration cannot change ranking (AUROC is fixed); it changes *what we do with the ranking*. 
Reporting only the shipped threshold understates the system that can actually be deployed. 
Reporting only the LOO-Youden point risks flattering it — so both are given, and the Youden 
threshold is chosen without the EEG it is applied to.

κ_ae > κ_ee, if it holds, is a substantive claim: the algorithm agrees with the average expert 
better than two experts agree with each other. It is *not* a claim that the algorithm is right 
and the experts wrong — consensus is not truth (see docs/validation_plan.md V4).
