# F4 — objective deviation LR vs the Morgoth gate (v6)

Recomputed on the v6 run with the **corrected SAP labels** and the **authoritative exact ages**. The LR (spectral deviation + age + sex) is **cross-fitted by patient** (5-fold `GroupKFold`), so its probability is out-of-fold — the legacy version reported an in-sample AUC (0.962), which is why it appeared to beat the gate.

| quantity | value |
|---|---|
| n recordings | 23,869 |
| Pearson r (LR vs Morgoth) | 0.409 |
| Spearman ρ | 0.438 |
| AUROC — deviation LR (out-of-fold) | 0.667 |
| AUROC — Morgoth gate | 0.835 |

The gate out-ranks the objective deviation model (0.835 vs 0.667); the two agree only moderately (ρ=0.438), so the deviation features capture much — not all — of what the report-calibrated detector encodes. This supports keeping Morgoth as the gate and the deviation field as the *descriptor*.
