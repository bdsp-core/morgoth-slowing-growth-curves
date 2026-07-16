# Morgoth is truth. Our features describe. Then we report what is left over.

*Recording-level gate: **guard-disabled 1 s re-run gate (gate_eeg_level_rerun)**. The old 5 s/guard-on gate spuriously zeroed 20.6% of p_focal (Morgoth's low-signal short-circuit); the re-run recomputed both EEG-level heads at a 1 s step with that guard disabled, so every recording carries a real focal and generalized probability.*

## The rule

A **segment** fires for feature *f* when its abnormality z exceeds **X**. A **recording** fires for *f* when at least **Y%** of its segments fire. A recording has **evidence** when **any** feature fires — features are independent statements, and the description says *which*. Severity is not part of the rule: it is the **conditional severity**, the median z among the firing segments only. (X, Y) are chosen by grid search to maximise Cohen's kappa vs Morgoth on a **patient-split train half**; everything below is on **held-out patients**.

| axis | harmonised operating point | test kappa | test balanced acc |
|---|---|---|---|
| generalized | segment z > **1.75**, in ≥ **15%** of segments | 0.423 | 0.707 |
| focal (asymmetry) | segment z > **2.5**, in ≥ **15%** of segments | 0.441 | 0.716 |

## In WHICH WAY is the EEG abnormal? (features evaluated independently)

Among the 11,312 recordings Morgoth calls generalized:

| feature | fires in |
|---|---|
| delta/alpha ratio | 33.6% |
| delta excess | 33.1% |
| theta/alpha ratio | 32.7% |
| relative delta excess | 32.4% |
| theta excess | 24.1% |
| paucity of alpha | 0.3% |

## Which side, among the 6,522 gated-focal recordings we corroborate

| side | n | % |
|---|---|---|
| left | 3,060 | 46.9% |
| right | 2,630 | 40.3% |
| no clear side | 832 | 12.8% |

## The discordance, at the best achievable operating point

| | generalized | focal |
|---|---|---|
| gate fires, **no feature fires** | **41.1%** | **40.1%** |
| gate silent, a feature fires | 17.4% | 16.7% |

Read against the base rate: the harmonised generalized rule also fires on **18.4%** of clean-normal recordings, the focal rule on **17.8%**. The operating point was tuned to agree with Morgoth, not to be specific against normals.

## The finding: disagreement tracks Morgoth's confidence

Among gated-generalized recordings, split by Morgoth's own probability:

| p_generalized quartile | our features corroborate |
|---|---|
| Q1 (weakest) | **37.5%** |
| Q2 | **54.3%** |
| Q3 | **69.8%** |
| Q4 (strongest) | **76.4%** |

It rises **monotonically, 37.5% → 76.4%**. Where Morgoth is confident, the normative field almost always agrees; the residual disagreement concentrates where he is least sure — evidence the two measure the same underlying thing rather than talking past each other.

What remains is a real, irreducible **~41% (generalized) / ~40% (focal)**: recordings the gate flags confidently enough to pass threshold, in which no band-power feature departs from its age- and stage-matched norm. The likeliest explanation is that the gate reads **morphology** — waveform shape, rhythmicity, reactivity — that a band-power deviation cannot represent. That is the honest limit of the current descriptor vocabulary, and the right place to look next.
