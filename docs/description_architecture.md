# The description architecture — one object, six descriptors, one learned direction

Written 2026-07-10, in answer to: *do we have a coherent comprehensive plan, or do we need to rethink?*

**Honest answer: we had the pieces, not the plan.** Detection, severity, band, prevalence, localization and
stage-accentuation were each built by a different script with a different target and a different notion of
what counts as ground truth. Two of them contradict each other. This document fixes the frame so we stop
drifting.

---

## 1. Division of labour

| stage | question | who answers it | why |
|---|---|---|---|
| **Gate** | Is there slowing? Is it focal or generalized? | **Morgoth** | Topography and morphology. Morgoth reaches AUROC 0.923 focal / 0.900 generalized against an 18-expert majority. Our spectral features reach 0.848 / 0.909 — and *cannot* separate exclusively-focal from generalized at all (0.477, chance), because global slowing amount runs backwards for focality (AUROC 0.183). |
| **Describe** | Where, how much, in which band, how often, how persistent, in which stage? | **the deviation field** | These are *measurements*, not classifications. None of them needs a label. |

**The rule (already in Methods §2.7b):** a quantity trained to predict the expert's call may never be used to
argue that we see what the expert misses. Detection is Morgoth's. Description is measurement.

---

## 2. The single object: the deviation field

Everything we describe is a **functional of one array**:

```
Z[segment, region, feature]  =  ( x - mu(age, stage, region, feature) ) / sd(age, stage, region, feature)
```

Each 15-s segment carries a sleep stage. Each z is referenced to clinician-normals **of that age, in that
stage, in that region**. Nothing else in the description pipeline is fit to anything.

**One learned direction.** `w` is an L1 logistic direction over the five spectral features, learned once
(clean-normal vs any pathologic slowing, whole-head). It answers "how much slowing is here", and it is then
applied unchanged to every segment and every region:

```
S(segment, region)  =  w · Z[segment, region, :]
```

No other supervised head exists in the description pipeline. Every descriptor below is an aggregation or a
contrast of `S` and its band components.

---

## 3. The six descriptors

Each is reported **per sleep stage** (the reader's expectation is stage-dependent, and so is ours).

| # | descriptor | definition | reported as |
|---|---|---|---|
| 1 | **Amount / excess** | median and p90 of `S` over that stage's segments | SD above age- and stage-matched normal, plus its centile in the clinician-normal distribution |
| 2 | **Location** | `E(r) = S(r) − mean S over the *other* lobes`; take argmax | region + side, with the excess in SD |
| 3 | **Band** | from the *excess*: `BI = (z_θ − z_δ) / (|z_θ| + |z_δ|)` over supra-threshold segments | continuous index in [−1, +1]; delta-predominant / mixed / theta-predominant |
| 4 | **Prevalence** | fraction of that stage's segments with `S` above the 95th centile of normals at that age and stage | % of segments; ACNS-style word only as a gloss |
| 5 | **Persistence** | run-length structure of supra-threshold segments | longest run (min), number of episodes, median episode length |
| 6 | **Stage-accentuation** | the stage maximising descriptor 1; whether slowing is present *only* in sleep | named stage; "present only during sleep" |

Two design points that were previously wrong and are now fixed:

- **Location must be an excess, not an absolute deviation.** In a globally slow brain, the argmax over
  absolute lobar `S` lands somewhere every time and means nothing. `E` is invariant to how slow the brain is.
  Empirically this moves exclusively-focal-vs-generalized from 0.477 (chance) to **0.692**, and the argmax of
  `E` recovers the reported side in **79.4%** of lateralized focal recordings with no training at all
  (signed temporal asymmetry: AUROC **0.881**).
- **The background must exclude the region being scored.** `whole_head` contains the focal lobe, which
  attenuates `E`. Use the mean of the *other* lobes.

---

## 4. Validation policy — and the two places the reader cannot be the standard

We validate in this order, and we say which is which.

1. **Measurement validity (no labels).** Split-half reliability within a recording; stability of the
   descriptor across a recording's own stages; behaviour on clinician-normals (a descriptor must be
   unremarkable in normals by construction).
2. **Construct validity.** Dose-response across report strata (done: z rises −0.11 → +0.43 → +1.49).
   Conspicuity: our score tracks the *proportion of 18 experts who saw the slowing* at ρ = 0.66.
3. **Concordance with the reader's language, referenced to the human ceiling.** Never "accuracy".

**Band.** Two electroencephalographers who both call slowing agree on its band 54% of the time (focal) and
27% (generalized); pairwise κ is 0.09–0.38. **The reader cannot be the criterion for band.** We therefore
report the band index as a *measurement*, validate it as one, and report its concordance with report language
against that ceiling. A cheap and probably-important fix first: our band edges leave a **7–8 Hz hole**
(`theta = 4–7`, `alpha = 8–13`). Clinical theta runs to 8 Hz. Slowing at 7–7.9 Hz is currently discarded, and
this is a plausible contributor to the band failure. **Test: widen theta to 4–8 Hz and recompute.**

**Prevalence / frequency.** Our prevalence correlates with the reader's frequency word at ρ = 0.077 —
significant, negligible. We have never measured how reliably readers use those words, so we do not know the
ceiling. Until we do, prevalence is reported as a measurement (with its own reliability), and the ρ = 0.077 is
reported as a fact about the *words*, not about the measurement.

**Severity.** Null (ρ = 0.05 across 168 combinations). A reader re-reading the same EEG reproduces their own
slowing call at κ 0.56–0.64. We report SD and centile, not an adjective. This stands.

---

## 5. What the sentence becomes

> *Left temporal slowing, delta-predominant, present in 48% of alert segments; 2.1 SD above age- and
> stage-matched norms at that lobe (94th centile) and 0.8 SD above this recording's own background; longest
> run 3.8 min over 4 episodes; accentuated in N2, where it reaches 3.0 SD.*

Every clause is a number with a reference population. No adjective we cannot defend, no band claim beyond
what the index supports, and an explicit **abstain path**: if Morgoth gates focal but `E` is unremarkable
against normals, the system says *"focal by pattern; no lateralizing spectral excess above the 97th centile
of normals"* rather than inventing a lobe.

---

## 6. Build order

| script | produces | status |
|---|---|---|
| `107_deviation_field.py` | the per-segment field, `w`, the normal thresholds, and the six descriptors per (recording, stage) | **this change** |
| `108_descriptor_validation.py` | split-half reliability, dose-response, conspicuity, concordance-vs-ceiling, external check on the expert panel | next |
| `109_band_edges_test.py` | does widening theta to 4–8 Hz rescue the band index? | next |
| `110_generate_sentence.py` | gate + descriptors → the sentence, with the abstain path | after 108 |

Retired by this plan: the trained **focal detector** (`S(focal)` in `scripts/103`). It was ill-posed — its
negative class shares its positive class's dominant signal, so the score had to rise with slowing and fall
with global slowing at the same time. `S(generalized)` survives, as the amount direction `w`.
