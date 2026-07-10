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

---

## 1a. Operating flow — gate, branch, describe (MBW spec, 2026-07-10)

Morgoth runs first and **selects which description to build**. The descriptors are then computed only for the
branch that fired.

```
Morgoth gate
├─ generalized slowing?  → describe GENERALIZED:  spatial distribution (anterior / posterior / diffuse),
│                                                  band (δ / θ / mixed), prevalence, persistence, per stage
├─ focal slowing?        → describe FOCAL:         side (L/R), region, band, prevalence, persistence, per stage
└─ neither               → "no pathological slowing"
```

*(The two branches are independent — a recording may fire both, and in our cohort 61% of focal recordings
also have generalized slowing, so both descriptions can run.)*

**Consistency constraint (new, and load-bearing).** The descriptor must agree with the gate's decision. A
focal branch may report *side, region, band, prevalence*; it may **not** report a generalized spatial
gradient, and it may never report a non-slowing feature ("increased alpha", etc.). Enforced structurally: each
branch has a fixed, small descriptor set drawn only from the slowing axes (δ excess, θ excess, α attenuation)
and their regional contrasts. Nothing outside `docs/claims_table.md` is emitted.

**Anterior/posterior gradient** (generalized branch) is buildable from existing channel-level features:
`AP = S(anterior chain) − S(posterior chain)`, anterior = {Fp1-F3, Fp2-F4, Fp1-F7, Fp2-F8, F3-C3, F4-C4,
Fz-Cz}, posterior = {C3-P3, C4-P4, P3-O1, P4-O2, T5-O1, T6-O2, Cz-Pz}. Frontally-predominant if AP above the
normal 95th centile, posterior if below the 5th, diffuse otherwise. Same normal-referenced, per-stage logic
as every other descriptor. Not yet built or validated.

**Do we still need the linear predictor?** For *description*, no. Once Morgoth owns detection, the linear
predictor's only job (a detection benchmark) is gone. The description IS the three normed axes reported
individually — δ excess, θ excess, α attenuation — because those are the clauses. Keep a single scalar
`amount` only as a convenience summary (equal-weight or the frozen `w`), clearly secondary to the components.
This is the pruning the architecture wants: the supervised score survives only as the thing that told us
*which* features to keep, not as an output.

## 1b. Corner cases — measured, not hypothetical

At Morgoth's shipped `p_slowing ≥ 0.30` (loose) vs our "marked slowing" = amount > 2 SD in > 20% of alert
windows, on 10,318 recordings with both:

| case | definition | frequency | what it is |
|---|---|---|---|
| **1** | we find marked slowing, gate says none | **1.9%** | genuine flag-for-review; 40% are report-focal (whole-head over-reads a strong focal signal), rest worth a look |
| **2** | gate says slowing, we find ~none | **12.9%** | mostly a **threshold artifact** — `p ≥ 0.30` calls 55.5% of all EEGs "slowing"; at `p ≥ 0.9` only 14% are, and only 4% of case-2 recordings carry a regional excess our whole-head amount missed |

Consequences: (a) the gate threshold must be set to an operating point, not left at 0.30; (b) corner-case-2
counting must use the **branch-appropriate** score (regional excess for focal, AP-aware for generalized), not
whole-head amount, or focal slowing is systematically undercounted; (c) both corner cases become **flag-for-
review** outputs, which is a feature — the system says "I disagree with the gate here" rather than
fabricating a description.

## 1c. Stage-specific detection — feasible, and evaluable

Morgoth gates at the recording level and is not stage-specific. Our field IS: `S` is normed per stage, so we
can emit a per-stage present/absent call (prevalence above the normal 95th centile within that stage).
**Committed plan (MBW 2026-07-10).** We WILL emit a per-stage present/absent slowing call and validate it:
1. `scripts/111_stage_specific.py` — per-stage prevalence call from the field.
2. Extract, from report text, the state a report localises slowing to (wake-only / sleep / both / generalised
   across states); a clause-scoped, negation-aware scan (reuse `scripts/95` machinery), counting how many
   reports carry a state-specific slowing statement — this is the denominator that decides how strong a test
   is possible. Read in chunks with a hard row cap so it cannot time out.
3. Evaluate our per-stage calls against those state labels (directional AUROC / concordance), and re-use the
   spindle-verified V4a result (wake-reported slowing → genuine N2 excess, AUROC 0.85) as the anchor.

---

## 1d. Setting the operating points to minimise "flag for review" (MBW point 3)

Two thresholds jointly determine the corner-case rate: the **gate cutoff** `τ_M` on Morgoth's p_slowing, and
our **descriptor cutoff** `τ_S` (the amount/prevalence above which we call slowing "present"). At the shipped
`τ_M = 0.30` the corner cases total ~15%; that is a threshold problem, not a disagreement.

Optimisation (to be run in `scripts/112_operating_points.py`):
1. Fix `τ_S` at its **principled** value — the point where our per-stage prevalence exceeds the normal 95th
   centile — because that has a meaning (false-positive rate 5% in normals *by construction*) and should not
   be tuned to match the gate.
2. Sweep `τ_M`, and for each value compute the two corner-case rates using the **branch-appropriate** score
   (regional excess for focal, AP-aware for generalized — NOT whole-head, which undercounts focal).
3. Choose `τ_M` at the knee that minimises `case1 + case2` subject to the gate's own sensitivity staying at a
   clinically acceptable level (do not sacrifice detection to look tidy). Report the frontier, not a single
   point, so the trade-off is visible.
4. Sanity target: corner cases **2–5% total**. If the minimum is far above that, the disagreement is real and
   is a finding — but §1b shows most of it is the loose 0.30 cutoff, so we expect the knee to land low.
Both corner cases remain **flag-for-review** outputs at whatever `τ_M` is chosen; the goal is to make that set
small and genuinely surprising, not to eliminate it.

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
| 3 | **Band** | **primary principle (MBW): pick the feature(s) most correlated with the report's band word.** Redefine as the share of EXCESS power `ΔP_θ/(ΔP_δ+ΔP_θ)` in linear units vs the age/stage normal mean, AFTER the 7–8 Hz fix. The old z-difference index is deprecated. | continuous index; δ-predominant / mixed / θ-predominant, only if it clears the ceiling-referenced bar |
| 4 | **Prevalence** | fraction of that stage's segments with `S` above the 95th centile of normals at that age and stage | % of segments; ACNS-style word only as a gloss |
| 5 | **Persistence** | run-length structure of supra-threshold segments | longest run (min), number of episodes, median episode length |
| 6 | **Stage-accentuation** | the stage maximising descriptor 1; whether slowing is present *only* in sleep | named stage; "present only during sleep" |

**Alpha in sleep, and sedation (2026-07-10).** The alpha-attenuation axis is computed **in wake only**.
Two reasons: (i) alpha is the posterior dominant rhythm, expected in wake, normally attenuated by N1 and gone
by N2 — so "low alpha vs normal-for-stage" is not a slowing sign in sleep, and abnormal patients' disrupted,
lighter sleep retains wake-like alpha the stager still calls N1/N2, which made the raw sleep a_atten reversed;
(ii) **sedatives that cause slowing also generate alpha** — propofol and benzodiazepines induce anterior/
diffuse alpha (and beta) alongside slowing, so alpha power is not a clean inverse marker of slowing under
sedation. Both point the same way: treat alpha attenuation as a wake sign, and describe sleep slowing by
delta and theta excess. This is stated in the manuscript.

**Flat / suppressed / disconnected segments are removed up front (2026-07-10).** 6.5% of cohort segments
(22–32% of abnormal *wake*) are flat — every band at the eps floor, near-zero power. These are
suppression / disconnection / dead epochs, not slowing. `features/artifact.py::usable_mask` now rejects them
at extraction (a per-channel std guard, added because the peak-to-peak check missed zero-power segments), and
the existing derived table was stripped (`segment_features` 6.5% removed; backup retained). **This pipeline is
for slowing only:** recordings that are predominantly burst-suppression or disconnection are handled by a
dedicated detector upstream and must not enter here. `data/derived/high_flat_recordings.parquet` flags the
1,317 recordings with > 30% flat segments as candidates for that review.

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

## 6. Build order (MBW-approved 2026-07-10)

| # | script | produces |
|---|---|---|
| 0 | `107b` diagnose the **N1 anomaly** (alpha attenuation reversed in abnormal N1) | root cause + fix; GATES everything per-stage |
| 1 | `112_operating_points.py` | the gate/descriptor thresholds that minimise flag-for-review (§1d) |
| 2 | `113_gated_describe.py` | gated per-branch descriptors + anterior/posterior gradient |
| 3 | `109_band_edges_test.py` | the 7–8 Hz fix; then band = feature most correlated with the report band word |
| 4 | `111_stage_specific.py` + report-state scan | per-stage present/absent call and its validation (§1c) |
| 5 | `108_descriptor_validation.py` | split-half reliability, dose-response, external panel concordance |
| 6 | `110_generate_sentence.py` | gate → descriptors → sentence, strictly against `docs/claims_table.md` |

The description linear predictor is retired (§1a): descriptors are the three normed axes reported
individually, plus their regional contrasts.
