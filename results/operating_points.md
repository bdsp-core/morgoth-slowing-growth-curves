# Operating points, per branch — flag-for-review

n = 12,027. Three outcomes per branch, so a data limitation is not scored as a disagreement:

- **agree / quantify** — gate fires, we measure slowing (normal operation)
- **quantification-limited** — gate fires, we measure nothing, but the recording is WAKE-ONLY (no sleep staged); slowing is subtle in alert wake, so this is a data limitation, NOT a flag
- **FLAG** — case 1 (we measure MARKED slowing, gate silent) OR case 2b (gate fires, we measure nothing, WITH sleep coverage: a genuine contradiction)

## generalized

| gate tau | % gated | case 1 (marked, silent) | quant-limited (wake-only) | case 2b (FLAG: has sleep, nothing) | true flag | gate sens vs report |
|---|---|---|---|---|---|---|
| 0.30 | 51.3% | 0.22% | 1.09% | 5.64% | **5.85%** | 0.89 |
| 0.35 | 39.5% | 0.37% | 0.47% | 4.34% | **4.71%** | 0.79 |
| 0.40 | 34.0% | 0.55% | 0.30% | 3.92% | **4.47%** | 0.73 |
| 0.45 | 30.5% | 0.66% | 0.22% | 3.56% | **4.22%** | 0.68 |
| 0.50 | 28.1% | 0.79% | 0.18% | 3.36% | **4.15%** | 0.64 |
| 0.55 | 26.1% | 0.84% | 0.18% | 3.20% | **4.04%** | 0.61 |
| 0.60 | 24.5% | 0.94% | 0.16% | 3.08% | **4.02%** | 0.58 |
| 0.65 | 23.0% | 1.00% | 0.13% | 2.98% | **3.98%** | 0.55 |
| 0.70 | 21.5% | 1.10% | 0.12% | 2.89% | **3.98%** | 0.52 |
| 0.75 | 20.3% | 1.18% | 0.12% | 2.78% | **3.96%** | 0.50 |
| 0.80 | 18.7% | 1.25% | 0.11% | 2.66% | **3.91%** | 0.47 |
| 0.85 | 16.8% | 1.36% | 0.11% | 2.48% | **3.83%** | 0.42 |

## focal

| gate tau | % gated | case 1 (marked, silent) | quant-limited (wake-only) | case 2b (FLAG: has sleep, nothing) | true flag | gate sens vs report |
|---|---|---|---|---|---|---|
| 0.30 | 13.0% | 0.76% | 2.64% | 7.23% | **8.00%** | 0.34 |
| 0.35 | 9.1% | 0.81% | 2.00% | 4.63% | **5.45%** | 0.24 |
| 0.40 | 6.9% | 0.84% | 1.65% | 3.21% | **4.05%** | 0.18 |
| 0.45 | 5.3% | 0.84% | 1.40% | 2.29% | **3.13%** | 0.14 |
| 0.50 | 4.4% | 0.86% | 1.17% | 1.85% | **2.71%** | 0.12 |
| 0.55 | 3.6% | 0.86% | 1.02% | 1.41% | **2.27%** | 0.10 |
| 0.60 | 3.0% | 0.86% | 0.86% | 1.14% | **2.00%** | 0.08 |
| 0.65 | 2.5% | 0.87% | 0.69% | 0.93% | **1.80%** | 0.07 |
| 0.70 | 2.0% | 0.87% | 0.54% | 0.72% | **1.59%** | 0.05 |
| 0.75 | 1.6% | 0.87% | 0.41% | 0.52% | **1.40%** | 0.04 |
| 0.80 | 1.2% | 0.87% | 0.30% | 0.38% | **1.26%** | 0.03 |
| 0.85 | 0.8% | 0.87% | 0.18% | 0.24% | **1.11%** | 0.02 |
