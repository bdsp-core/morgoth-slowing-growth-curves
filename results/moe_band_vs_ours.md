# MoE — our band determination vs the expert panel (no report text)

Featurized **1761/1761** pooled BDSP MoE events with the project's own pipeline (`features.extract` -> `features.recording`); each event is one 15-s, 3000-sample, 200 Hz referential segment. `icare_*` cardiac-arrest events excluded. 22 raters, anonymized R01..R22 (one is an author of this paper).

**Headline metric = Cohen κ, not raw match.** Raw agreement is prevalence-inflated (delta dominates the base rate); κ is chance-corrected. A constant "always-delta" classifier is included as a baseline so raw numbers can be read against chance.

Band-call mix — **primary (raw rel_delta>rel_theta) rule**: generalized {'delta': 0.982, 'theta': 0.018}, focal {'delta': 0.979, 'theta': 0.021}. This rule is **nearly a constant `delta` caller**: relative delta (1-4 Hz) almost always exceeds relative theta (4-7 Hz) on the 1/f spectrum, so it barely discriminates band. The **age-normalized z-rule** (below) is balanced — generalized {'delta': 0.565, 'theta': 0.435}, focal {'theta': 0.525, 'delta': 0.475}.

## Primary result — chance-corrected band agreement (κ), primary raw rule

Per expert / per expert-pair, restricted to events the expert scored as slowing in **exactly one** of delta/theta (band unambiguous); experts/pairs need ≥20 such events. κ is the headline; raw match and the constant-classifier baselines follow.

| kind | our κ_ae (med) | expert κ_ee ceiling (med) | κ contrast (algo−ceiling), boot 95% CI | √κ_ee benchmark | our match (med) | ceiling match (med) | always-delta | always-theta |
|---|---|---|---|---|---|---|---|---|
| focalslowing | **0.070** | 0.260 | -0.196 [-0.323, -0.075] | 0.510 | 0.901 | 0.907 | 0.902 | 0.098 |
| genslowing | **0.011** | 0.408 | -0.393 [-0.441, -0.348] | 0.639 | 0.418 | 0.750 | 0.415 | 0.585 |

- **focalslowing**: 20 experts, 137 pairs; median single-band events per expert = 139, per pair = 51. Raw-match contrast (algo−ceiling) = +0.004 [-0.018, +0.027]. Our raw match (0.901) sits at the always-delta baseline (0.902) — the agreement is the delta base rate, not band perception (κ_ae = 0.070).
- **genslowing**: 22 experts, 188 pairs; median single-band events per expert = 281, per pair = 79. Raw-match contrast (algo−ceiling) = -0.313 [-0.350, -0.277]. Our raw match (0.418) sits at the always-delta baseline (0.415) — the agreement is the delta base rate, not band perception (κ_ae = 0.011).

## Age-normalized z-rule (principled rule; aged subset n=1021)

`band = argmax(z(rel_delta), z(rel_theta))`, z = deviation from the clean-normal reference at the event's age (Gaussian age kernel bw=5 y; reference = `channel_stage_features` src==cohort & clean_normal, **stage W** — MoE events are assumed awake clips). Focal lobe = the lobe with the largest slowing z-deviation. Age recovered by joining the 9-digit pid (and eeg date where available) to `fractional_age` / `labels_unified` / `cohort_metadata`; sources: {'none': 740, 'fa_pid': 516, 'fa_exact': 448, 'lu_pid': 57}.

| kind | our κ_ae (med) | expert κ_ee ceiling (med) | √κ_ee | our match (med) | ceiling match (med) | always-delta | our band mix |
|---|---|---|---|---|---|---|---|
| focalslowing | **0.065** | 0.282 | 0.531 | 0.527 | 0.900 | 0.901 | {'theta': 0.525, 'delta': 0.475} |
| genslowing | **0.223** | 0.396 | 0.629 | 0.622 | 0.747 | 0.426 | {'delta': 0.565, 'theta': 0.435} |

## Secondary — delta-vs-theta vote-vector match (analogue of the human-ceiling script, raw rule)

Among events the expert called slowing (delta or theta marked), fraction where the full (delta,theta) vote pair matches. The expert-vs-expert column reproduces the 90-script ceiling (0.576 focal / 0.434 generalized) on this featurized subset.

| kind | our vs expert (median) | expert vs expert / ceiling (median) |
|---|---|---|
| focalslowing | 0.809 | 0.581 |
| genslowing | 0.278 | 0.462 |

## Sensitivity — author-rater excluded (primary rule)

Recomputed dropping the one rater who is an author (anonymized index withheld).

| kind | our κ_ae (med) | ceiling κ_ee (med) | our match | ceiling match |
|---|---|---|---|---|
| focalslowing | 0.062 | 0.259 | 0.898 | 0.906 |
| genslowing | 0.011 | 0.428 | 0.416 | 0.757 |

## Verdict

1. **The primary raw rule is near-chance.** Chance-corrected, our band determination carries almost no information: κ_ae = 0.070 (focal) and 0.011 (generalized), versus expert-expert κ_ee = 0.260 and 0.408. The focal raw match (~0.90) is a **base-rate artifact** — it equals the always-delta baseline, which an "always delta" classifier would also achieve. The κ contrast is negative and its 95% CI excludes 0 for both kinds; our raw rule is below the human ceiling, focal and generalized.
2. **The age-normalized z-rule is the principled fix and partly helps.** Its band mix is balanced (not 98% delta). On **generalized** slowing κ_ae rises from 0.011 to 0.223 — a real gain. On **focal** slowing it does NOT help (0.070 -> 0.065, still near-chance). Either way, on the aged subset the z-rule **still sits below** the expert-expert ceiling (κ_ee = 0.282 focal / 0.396 gen) and below the attenuation benchmark √κ_ee. Our current signal-level band determination does not reach human concordance.
3. **The old 0.74 must be retired.** It was band agreement of our regex extractor against **report text**, one report per recording — it measures text parsing, not perception of the signal, and shares no event, rater, or estimand with the numbers here. It is not comparable to them and should not be reported as the same quantity. The √κ_ee column is the score an algorithm sitting at the latent truth would reach against noisy experts (conservative, since expert errors are correlated).
