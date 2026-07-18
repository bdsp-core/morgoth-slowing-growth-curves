# The claims table — what the report sentence is allowed to say

Every clause the system can emit, the exact metric behind it, its validation status, and a verdict.
**Nothing may appear in a generated sentence, a figure, or the manuscript unless it is ALLOWED here.**

This table is the governance device. When a new analysis lands, it updates a row — it does not add a claim.

Status key: **ALLOWED** (validated, may be asserted) · **PROVISIONAL** (measured, reliability not yet
established; may be reported with its uncertainty, never as a clinical assertion) · **FORBIDDEN** (tested and
failed, or untestable against the available standard).

---

## The prior constraint: two objects, one rule

| object | what it is | may be used for | may NOT be used for |
|---|---|---|---|
| **`z` / `S`** | deviation from age-, stage- and region-matched clinician-normals. **Unsupervised** — fit to nothing but the normal population. | every descriptive claim; the argument that we detect slowing readers do not name (§3.4e) | — |
| **Morgoth** | expert-calibrated foundation model | detection: presence, focal vs generalized | any claim about seeing what experts miss (it is trained on their calls) |
| **a supervised score on z** | e.g. the retired `S(focal)` | detection benchmarks only | descriptive claims; anything about expert blind spots |

Violating this makes the paper circular. It is not a stylistic preference.

---

## Clause-by-clause

| # | clause the sentence would say | metric | evidence | status |
|---|---|---|---|---|
| 1 | *"There is slowing."* | Morgoth gate | AUROC **0.853** vs 18-expert majority (generalized); **0.908** (focal) — canonical Figure-2 panel eval (our Morgoth-free detector reaches 0.946 / 0.923) | **ALLOWED** — the gate's claim |
| 2 | *"…focal"* / *"…generalized"* | Morgoth gate | as above | **ALLOWED** — the gate's claim |
| 2b | focal-vs-generalized **from our spectral features** | `S(focal)` | **0.477 (chance)** for exclusively-focal vs generalized; global amount runs *backwards* for focality (AUROC 0.183) | **FORBIDDEN** — detector retired |
| 3 | *"2.1 SD above age- and stage-matched normal (94th centile)"* | `S = w·(δ excess, θ excess, α attenuation)`, wake-fit, α-attenuation in wake only; re-standardised against normals of that age & stage. Flat/suppressed segments excluded up front | **split-half ρ/ICC 0.97** (scripts/108); calibration normals −0.09 SD; dose-response ρ 0.447 (−0.08→+0.31→+0.81); conspicuity ρ **0.549** vs the 18-expert consensus proportion (amount), 0.652 (sparse score) | **ALLOWED** — validated as a reliable measurement |
| 3b | *"…with paucity of faster activity"* | the α-attenuation component, **wake only** | `corr(z_TAR − z_θ, −z_α) = 0.985` — what TAR measured all along. Restricted to wake: alpha is the posterior dominant rhythm (gone by N2), and sedatives that cause slowing also *generate* alpha (propofol/benzodiazepines) | **ALLOWED** as a named component of (3), **wake only** |
| 4 | *"left temporal"* — **side** | argmax of background excess `E(r) = S(r) − mean S over the other lobes`; signed temporal asymmetry | side recovered in **79.4%** of lateralized focal recordings; signed asymmetry AUROC **0.881**, fit to nothing | **ALLOWED** (side) |
| 4b | *"left temporal"* — **lobe** | same | focal slowing raises the *contralateral* hemisphere by +0.5 to +0.8 SD; parasagittal chain lateralizes almost as well as temporal. The signal is **hemispheric, not lobar** | **PROVISIONAL** — report as "maximum-deviation lobe", never as a resolved localization |
| 4c | focal **excess magnitude** | `E` in SD | exclusively-focal vs generalized **0.692** (from 0.477) | **PROVISIONAL** — reliability untested |
| 4d | *"frontally predominant"* / *"posteriorly predominant"* / *"diffuse"* (generalized) | AP = S(anterior chain) − S(posterior chain), thresholded at the normal 5th/95th centile | recovers the report's anterior-vs-posterior call at AUROC **0.604** [0.568, 0.642]; directionally correct (anterior +0.19 vs posterior −0.37) but weak, and the expert ceiling for A/P predominance is unmeasured | **PROVISIONAL** — report "diffuse" as the default (correctly the majority); assert predominance only when AP clears the normal centile, and flag it as low-confidence |
| 5 | *"delta-predominant"* / *"theta-predominant"* / *"mixed"* | band index | on 2,053 clean-paired report-band-labelled recordings: best feature is **rel_θ − rel_δ at AUROC 0.639** [0.616, 0.662]; z_θ − z_δ 0.625. My proposed **excess-power share `ΔP_θ/(ΔP_δ+ΔP_θ)` FAILED (0.479)** — linear ΔP is dominated by delta's dynamic range. Expert-expert κ for band is 0.09–0.38 | **PROVISIONAL** — a relative-power difference is weakly informative (~0.64) and roughly at the (low) human ceiling; may be reported as a **low-confidence** δ/θ/mixed call. Still pending the 7–8 Hz re-extraction (`scripts/109`) to see if closing the hole helps |
| 6 | *"present in 48% of segments"* | fraction of that stage's segments with `S` above the 95th centile of normals at that age & stage | **split-half ICC 0.94** (scripts/108); normals 0.047 by construction; focal N1 0.31, generalized N1 0.41 | **ALLOWED** as a percentage; assert presence only above the normal rate |
| 6b | *"frequent"* / *"occasional"* / *"continuous"* (ACNS words) | mapping of (6) to report vocabulary | prevalence vs the reader's frequency word: ρ = **0.077**. The reliability of those words has never been measured, so no ceiling exists | **FORBIDDEN** |
| 7 | *"longest run 3.8 min over 4 episodes"* | run-length structure of supra-threshold segments | split-half ρ 0.76 / ICC 0.90; ~0 in normals, rises with severity (`scripts/108`). Caveat: the parity split partly breaks true run structure, so this over-states physical-run reliability | **PROVISIONAL** — report run/episodes, but as approximate |
| 8 | *"accentuated in N2"* / *"present only during sleep"* | stage maximising (3); per-stage present = prevalence > normal rate in that stage | per-stage present rate is dose-responsive in every stage (N1 focal 0.46 / gen 0.60 vs normal 0.13; N2 0.41/0.43; REM 0.42/0.56 — `scripts/111`). V4a: on **spindle-verified** N2, cases exceed held-out normals at AUROC **0.854/0.844** | **ALLOWED** |
| 8b | *validating stage-specificity against the report's stated state* | wake_slow / sleep_slow from report text | **not usable** ground truth: `wake_slow` just re-encodes abnormal-vs-normal (95% abnormal); `sleep_slow` is contaminated by normal drowsiness (flags 2,864 / 4,798 clean-normals). Directional tests at/below chance (`scripts/111`) | **FORBIDDEN** as validation — the sleep anchor is V4a (spindle-verified), not report text |
| 9 | *"mild"* / *"moderate"* / *"marked"* | severity adjective | ρ = **0.050** (n.s.); **168** feature × statistic × normalization × stratum combinations, best |ρ| = 0.179, fails Bonferroni, wrong sign. A reader re-reading the same EEG reproduces their own slowing call at κ 0.56–0.64 | **FORBIDDEN** — report SD and centile |
| 10 | *"peak N SD"* | max over segments | a maximum over hundreds of segments; observed max 19.4 SD = artifact | **FORBIDDEN** — use the p90 |
| 11 | *"focal by pattern; no lateralizing spectral excess"* | gate fires focal, `E` below the 97th centile of normals | the abstain path | **ALLOWED** — and required, so the system never invents a lobe |

---

## Immediate consequences

1. **`results/example_reports_final.md` is retired.** It emits *"Rare mild generalized mixed theta/delta
   slowing — peak 0.0 SD above age/stage-matched norms"* on normal-labeled recordings: an adjective (9,
   forbidden), a frequency word (6b, forbidden), a band (5, forbidden), and a peak statistic (10, forbidden),
   asserting slowing at **zero deviation**. Four violations in one sentence. Archived as exploratory.
2. **`src/morgoth_slowing/report/phrase.py` must be rewritten** against this table (`scripts/110`).
3. **No band language ships** until the 7–8 Hz fix and the excess-power redefinition are tested
   (`scripts/109`), and then only if the fixed index clears a bar set *before* the test.
4. **N1 resolved.** The apparent N1 alpha reversal was two artifacts, both fixed: (a) 22–32% of abnormal
   *wake* segments were flat/suppressed and slipped past artifact rejection — now removed up front; (b) alpha
   in sleep is confounded (disrupted sleep retains wake-like alpha; sedation generates alpha), so the
   alpha-attenuation axis is **wake only**. In N1–REM, slowing is delta and theta excess. Calibration holds.

## The sentence this table permits, today

> *Left-sided slowing, maximal in the temporal chain: 2.1 SD above age- and stage-matched normal (94th
> centile), with paucity of faster activity; present in 48% of alert segments; longest run 3.8 min over 4
> episodes; accentuated in N2, where it reaches 3.0 SD.*

No adjective. No band. No frequency word. No peak. Every clause a number with a reference population.
