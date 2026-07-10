# Operating points — minimising flag-for-review

n = 12,027 recordings with both a gate probability and descriptors. Descriptor cutoff held at its principled value. **Flags are genuine contradictions only**: case 1 = we measure MARKED slowing (>3 SD) while the gate is silent; case 2 = the gate fires while we measure NOTHING (amount ≤ 0 SD, no lobar excess). 'Gate fires, we measure mild slowing' is normal operation and is NOT flagged — the descriptor describes, it does not re-detect.

| gate τ_M | % gated in | case 1 (we see, gate silent) | case 2 (gate fires, we don't) | total flag | gate sens | gate spec |
|---|---|---|---|---|---|---|
| 0.20 | 83.1% | 0.0% | 14.2% | **14.2%** | 0.98 | 0.30 |
| 0.25 | 73.6% | 0.0% | 10.4% | **10.4%** | 0.96 | 0.46 |
| 0.30 | 55.5% | 0.1% | 4.7% | **4.7%** | 0.88 | 0.72 |  ←
| 0.35 | 46.3% | 0.1% | 2.7% | **2.8%** | 0.80 | 0.82 |
| 0.40 | 40.5% | 0.2% | 2.0% | **2.2%** | 0.72 | 0.87 |
| 0.45 | 35.8% | 0.3% | 1.6% | **1.8%** | 0.65 | 0.89 |
| 0.50 | 32.4% | 0.4% | 1.3% | **1.6%** | 0.60 | 0.91 |
| 0.55 | 29.7% | 0.4% | 1.1% | **1.5%** | 0.55 | 0.92 |
| 0.60 | 27.5% | 0.4% | 0.9% | **1.4%** | 0.51 | 0.93 |
| 0.65 | 25.5% | 0.5% | 0.8% | **1.3%** | 0.48 | 0.93 |
| 0.70 | 23.5% | 0.5% | 0.7% | **1.2%** | 0.44 | 0.94 |
| 0.75 | 21.8% | 0.6% | 0.6% | **1.2%** | 0.41 | 0.95 |
| 0.80 | 19.9% | 0.6% | 0.5% | **1.1%** | 0.38 | 0.95 |
| 0.85 | 17.6% | 0.7% | 0.4% | **1.1%** | 0.34 | 0.96 |
| 0.90 | 14.0% | 0.8% | 0.3% | **1.1%** | 0.27 | 0.97 |
| 0.95 | 9.1% | 0.9% | 0.2% | **1.1%** | 0.18 | 0.98 |

**Chosen τ_M = 0.30** (minimises total flag with gate sensitivity ≥ 0.80): flag-for-review **4.7%** (case1 0.1%, case2 4.7%), gate sensitivity 0.88, specificity 0.72.

At the shipped τ_M = 0.30 the flag rate is 4.7%; the knee cuts it to 4.7%. Both corner cases remain flag-for-review outputs — the goal is a small, genuinely surprising set, not zero.
