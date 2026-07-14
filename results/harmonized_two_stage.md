# Morgoth is truth. Our features describe. Then we report what is left over.

Rebuilt after MBW identified three defects in the first attempt. All three were real.

## What was wrong before

1. **Intermittency washout — a bug, not a choice.** "Evidence" required `amount_z`, the median z over
   *all* segments, to be low. In an intermittently-slow recording the normal segments outvote the abnormal
   ones, so that statistic is near zero **by construction**. It silently asked *"is this EEG slow ALL the
   time?"* — the wrong question. **71.4%** of the recordings it called "no evidence" in fact contained slow
   segments, at median severity **+1.54** when present. Intermittency is something to **describe**, never a
   reason to say nothing is there.
2. **The threshold was picked by fiat** (the 95th centile). It is a free parameter and was never optimised.
3. **The features were averaged together**, so isolated delta excess with normal ratios was diluted away.

## The rule now

A **segment** fires for feature *f* when its abnormality z exceeds **X**.
A **recording** fires for *f* when at least **Y%** of its segments fire.
A recording has **evidence** when **any** feature fires — the features are independent statements, and the
description says *which*. Severity leaves the rule entirely and becomes **conditional severity**: the median
z among the **firing segments only**. Persistence (longest run, episodes) is likewise a descriptor.

**(X, Y) are chosen to agree with Morgoth as well as they possibly can** — grid search maximising Cohen's
kappa, fit on a **patient-split train half**, everything below reported on **held-out patients**. Two free
parameters cannot buy a flattering number, and the residual disagreement is therefore the *best achievable*,
not an artefact of someone's favourite percentile.

| axis | harmonised operating point | test kappa | test balanced acc |
|---|---|---|---|
| generalized | segment z > **1.5**, in ≥ **20%** of segments | 0.419 | 0.708 |
| focal (asymmetry) | segment z > **2.5**, in ≥ **15%** of segments | 0.436 | 0.714 |

## In WHICH WAY is the EEG abnormal? (features evaluated independently)

Among the 11,210 recordings Morgoth calls generalized:

| feature | fires in |
|---|---|
| theta/alpha ratio | 39.2% |
| delta/alpha ratio | 38.9% |
| delta excess | 37.5% |
| relative delta excess | 35.6% |
| theta excess | 29.1% |
| paucity of alpha | 8.7% |

**They are not redundant.** Number of the six features firing together:

| n features | recordings | % |
|---|---|---|
| 0 | 3,852 | 34.4% |
| 1 | 1,739 | 15.5% |
| 2 | 1,714 | 15.3% |
| 3 | 1,491 | 13.3% |
| 4 | 953 | 8.5% |
| 5 | 1,035 | 9.2% |
| 6 | 426 | 3.8% |

Nearly a third of corroborated recordings fire on only **one or two** features. Averaging them — as the
first version did — destroys exactly this information.

## HOW MUCH? (the 7,358 gated-generalized recordings our features corroborate)

| descriptor | value |
|---|---|
| prevalence | median **0.26** → *frequent (10–50%)* |
| conditional severity (median z among **firing** segments) | **+1.90** |
| longest continuous run | **1.6 min** |
| episodes | **14** |

## WHICH SIDE? (the 6,105 gated-focal recordings our features corroborate)

| side | n | % |
|---|---|---|
| left | 2,901 | 47.5% |
| right | 2,490 | 40.8% |
| no clear side | 714 | 11.7% |

Only **11.7%** now lack a side, against 64% before — because the side is read from the
**firing segments only**, not from a median over a recording that is mostly normal.

## The discordance, at the best achievable operating point

| | generalized | focal |
|---|---|---|
| gate fires, **no feature fires** | **35.0%** | **38.9%** |
| gate silent, a feature fires | 23.4% | 18.3% |

(was 60.8% / 61.7% under the old, broken rule)

**Read these against the base rate:** the harmonised generalized rule also fires on **23.9%** of
clean-normal recordings, and the focal rule on **17.7%**. The operating point is deliberately
permissive — it was tuned to agree with Morgoth, not to be specific against normals.

## The finding: disagreement tracks Morgoth's confidence

Corroboration is **not random**. Among gated-generalized recordings, split by Morgoth's own probability:

| p_generalized quartile | our features corroborate |
|---|---|
| Q1 (weakest) | **48.7%** |
| Q2 | **59.7%** |
| Q3 | **71.7%** |
| Q4 (strongest) | **82.5%** |

It rises **monotonically, 48.7% → 82.5%**. Where Morgoth is confident, our normative field
almost always agrees. The residual disagreement concentrates precisely where he is least sure — which is
what you would want, and is strong evidence the two are measuring the same underlying thing rather than
talking past each other.

What remains is a real, irreducible ~35–39%: recordings the gate flags confidently enough to pass threshold,
in which no band-power feature departs from its age- and stage-matched norm. The most likely explanation is
that the gate reads **morphology** — waveform shape, rhythmicity, reactivity — that a band-power deviation
cannot represent at all. That is the honest limit of the current descriptor vocabulary, and it is the right
place to look next.
