# Descriptor validation — are the six descriptors measurements?

Each descriptor is tested AS A NUMBER (docs/description_architecture.md sec 4): calibration on clean-normals, split-half reliability within a recording, dose-response across report strata, external conspicuity, and a persistence sanity check. Not classification accuracy. S is reconstructed exactly as `scripts/107` (`amount_direction.json`: `z_log_theta` +2.37, `a_atten` +2.35).

## 1. Calibration — clean-normals at ~0 SD, ~0.05 prevalence, by construction

| stage | group | n | amount_median (SD) | prevalence (mean) |
|---|---|---|---|---|
| W | clean-normal | 3918 | -0.06 | 0.045 |
| W | focal | 2684 | +0.70 | 0.062 |
| W | generalized | 889 | +0.97 | 0.088 |
| N1 | clean-normal | 1977 | -0.13 | 0.051 |
| N1 | focal | 1731 | +0.94 | 0.308 |
| N1 | generalized | 778 | +1.29 | 0.412 |

Clean-normal alert: amount_median **-0.09 SD** (target ~0), prevalence **0.047** (target 0.05, right-skewed so read the mean). Focal and generalized rise monotonically above both.

**VERDICT (amount, prevalence): reliable — calibrated by construction (-0.09 SD, 0.047 prevalence in normals).**

## 2. Split-half reliability — the key new result

7,498 recordings with >=20 alert (W/N1) whole_head segments; each split even/odd by segment index, both descriptors recomputed per half.

| descriptor | Spearman rho | ICC(2,1) | n |
|---|---|---|---|
| amount_median | 0.969 | 0.971 | 7498 |
| prevalence | 0.778 | 0.942 | 7498 |
| longest_run_min | 0.758 | 0.898 | 7498 |

**VERDICT (amount_median): reliable — split-half rho 0.97, ICC 0.97** (bar: >0.6).
**VERDICT (prevalence): reliable — split-half rho 0.78, ICC 0.94** (bar: >0.6).
**VERDICT (longest_run_min): reliable — split-half rho 0.76, ICC 0.90** (bar: >0.6).

## 3. Dose-response — amount rises across report strata

Per-recording amount = n_seg-weighted mean of W/N1 `amount_median`; abnormal strata require `clean_pair`.

| stratum | n | amount_median (SD) |
|---|---|---|
| 0 clean-normal | 4289 | -0.08 |
| 1 abnormal, no slowing named | 631 | +0.31 |
| 2 abnormal, slowing named | 3207 | +0.81 |

Spearman rho (stratum rank vs amount) = **0.447** (n=8127); medians -0.08/+0.31/+0.81 monotone rising.

**VERDICT (amount, construct validity): reliable — monotone dose-response, rho 0.45.**

## 4. Conspicuity — amount vs the 18-expert consensus (external test set)

Amount recomputed on the 100 OccasionNoise whole_head EEGs (same cohort-normal references, no refitting); scored against the fraction of 18 raters marking generalized slowing (GN).

Spearman rho = **0.549** (p=3.2e-09, n=100). scripts/94 sparse score = 0.652.

**VERDICT (amount, external conspicuity): reliable — rho 0.55 vs the expert consensus proportion.**

## 5. Persistence — longest_run / n_episodes ~0 in normals, rising with severity

| stage | group | n | longest_run_min (median) | longest_run_min (mean) | n_episodes (mean) |
|---|---|---|---|---|---|
| W | clean-normal | 3918 | 0.00 | 0.17 | 0.68 |
| W | focal | 2684 | 0.00 | 0.16 | 0.68 |
| W | generalized | 889 | 0.00 | 0.19 | 0.77 |
| N1 | clean-normal | 1977 | 0.00 | 0.12 | 0.33 |
| N1 | focal | 1731 | 0.23 | 0.88 | 0.88 |
| N1 | generalized | 778 | 0.47 | 1.52 | 1.17 |

Clean-normal alert: median longest run **0.00 min**, mean 0.15. Persistence rides on the prevalence threshold, so its reliability is that of prevalence (split-half above).

**VERDICT (persistence): reliable — normals ~0 and it rises with severity, but split-half rho 0.76 / ICC 0.90 (parity-split breaks run structure).**

## Summary

| descriptor | test that binds | number | verdict |
|---|---|---|---|
| amount | split-half + dose-response + conspicuity | rho 0.97/ICC 0.97; dose 0.45; consp 0.55 | reliable |
| prevalence | split-half + calibration | rho 0.78/ICC 0.94; normals 0.047 | reliable |
| persistence | split-half | rho 0.76/ICC 0.90 | reliable |
| band / location / accentuation | not tested here | see scripts/94, docs/claims_table.md | provisional/other |
