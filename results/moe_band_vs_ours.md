# MoE — our band determination vs the expert panel (no report text)

Featurized **1761/1761** pooled BDSP MoE events with the project's own pipeline (`features.extract` -> `features.recording`); each event is one 15-s, 3000-sample, 200 Hz referential segment. `icare_*` cardiac-arrest events excluded. 22 raters, anonymized R01..R22 (one is an author of this paper).

**A-priori band rules.** Generalized: `delta` if whole-head rel_delta > rel_theta else `theta`. Focal: the same rule at the most-slowed lobe (max rel_delta+rel_theta over L/R temporal, L/R parasagittal). No report text and no text extractor enter this pipeline.

Our own band-call mix — generalized: {'delta': 0.9818285065303805, 'theta': 0.018171493469619535}; focal: {'delta': 0.9784213515048268, 'theta': 0.021578648495173196}.

## Primary: categorical delta-vs-theta band, on single-band slowing events

For each expert, restrict to events that expert scored as slowing in **exactly one** of delta/theta (band unambiguous); compare to our band call. The **ceiling** is the identical statistic between experts on the identical event universe. Distribution is over experts (algorithm) / expert pairs (ceiling); experts/pairs need ≥20 such events.

| kind | our vs expert: match median [IQR] | expert vs expert (ceiling): match median [IQR] | contrast (algo−ceiling), boot 95% CI | our κ (med) | expert κ (med) | √κ_ee benchmark |
|---|---|---|---|---|---|---|
| focalslowing | **0.901** [0.842, 0.936] | 0.907 [0.833, 0.942] | +0.003 [-0.019, +0.026] | 0.067 | 0.260 | 0.510 |
| genslowing | **0.418** [0.312, 0.742] | 0.750 [0.651, 0.816] | -0.313 [-0.350, -0.277] | 0.011 | 0.408 | 0.639 |

- **focalslowing**: 20 experts, 137 expert pairs; median single-band events per expert = 139, per pair = 51. Cohen-κ contrast (algo−ceiling): -0.197 [-0.323, -0.076].
- **genslowing**: 22 experts, 188 expert pairs; median single-band events per expert = 281, per pair = 79. Cohen-κ contrast (algo−ceiling): -0.393 [-0.441, -0.348].

## Secondary: delta-vs-theta vote-vector match (analogue of the human-ceiling script)

Among events the expert called slowing (delta or theta marked), fraction where the full (delta,theta) vote pair matches. The expert-vs-expert column reproduces the 90-script ceiling (0.576 focal / 0.434 generalized) on this featurized subset.

| kind | our vs expert (median) | expert vs expert / ceiling (median) |
|---|---|---|
| focalslowing | 0.809 | 0.581 |
| genslowing | 0.278 | 0.462 |

## Sensitivity: author-rater excluded

Recomputed dropping the one rater who is an author (index withheld). Primary categorical match:

| kind | our vs expert (match med) | ceiling (match med) |
|---|---|---|
| focalslowing | 0.898 | 0.906 |
| genslowing | 0.416 | 0.757 |

## Age-matched ALT rule (aged subset, n=550 events with a recoverable age)

Band = whichever of rel_delta/rel_theta is more elevated above its age-matched normal median (growth-curve p50, sex pooled; elevation scaled by p90−p50). Same categorical match statistic.

| kind | ALT our vs expert (match med) | ceiling on aged subset (match med) |
|---|---|---|
| focalslowing | 0.720 | 0.903 |
| genslowing | 0.592 | 0.714 |

## Interpretation

- **focalslowing**: our band call MATCHES the expert-expert ceiling on band determination (match 0.901 vs ceiling 0.907; contrast +0.003 [-0.019, +0.026]). The attenuation benchmark √κ_ee = 0.510 is the score an algorithm sitting at the latent truth would reach against noisy experts (conservative, since expert errors are correlated).
- **genslowing**: our band call FALLS BELOW the expert-expert ceiling on band determination (match 0.418 vs ceiling 0.750; contrast -0.313 [-0.350, -0.277]). The attenuation benchmark √κ_ee = 0.639 is the score an algorithm sitting at the latent truth would reach against noisy experts (conservative, since expert errors are correlated).

**On the old 0.74.** That number was band agreement of our regex extractor against **report text**, one report per recording — it measures text parsing, not perception of the signal, and shares no event, rater, or estimand with the numbers above. It is not comparable to them and should not be reported as if it were the same quantity. The numbers here are the honest signal-level band agreement, benchmarked against the expert-expert ceiling on the same events.
