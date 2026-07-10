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
| 1 | *"There is slowing."* | Morgoth gate | AUROC **0.900** vs 18-expert majority (generalized); **0.923** (focal) | **ALLOWED** — the gate's claim |
| 2 | *"…focal"* / *"…generalized"* | Morgoth gate | as above | **ALLOWED** — the gate's claim |
| 2b | focal-vs-generalized **from our spectral features** | `S(focal)` | **0.477 (chance)** for exclusively-focal vs generalized; global amount runs *backwards* for focality (AUROC 0.183) | **FORBIDDEN** — detector retired |
| 3 | *"2.1 SD above age- and stage-matched normal (94th centile)"* | `S = 0.80·z_δ + 2.82·z_θ + 4.72·α-attenuation`, re-standardised against normals of that age & stage | calibration: normals **−0.05 SD**, prevalence **0.047** vs 0.05 target. Dose-response ρ 0.50–0.55. Conspicuity ρ **0.652** vs the 18-expert consensus proportion | **ALLOWED** |
| 3b | *"…with paucity of faster activity"* | the α-attenuation component (weight **4.72**, the largest of the three) | `corr(z_TAR − z_θ, −z_α) = 0.985` — this is what TAR was measuring all along | **ALLOWED** as a named component of (3) |
| 4 | *"left temporal"* — **side** | argmax of background excess `E(r) = S(r) − mean S over the other lobes`; signed temporal asymmetry | side recovered in **79.4%** of lateralized focal recordings; signed asymmetry AUROC **0.881**, fit to nothing | **ALLOWED** (side) |
| 4b | *"left temporal"* — **lobe** | same | focal slowing raises the *contralateral* hemisphere by +0.5 to +0.8 SD; parasagittal chain lateralizes almost as well as temporal. The signal is **hemispheric, not lobar** | **PROVISIONAL** — report as "maximum-deviation lobe", never as a resolved localization |
| 4c | focal **excess magnitude** | `E` in SD | exclusively-focal vs generalized **0.692** (from 0.477) | **PROVISIONAL** — reliability untested |
| 4d | *"frontally predominant"* / *"posteriorly predominant"* / *"diffuse"* (generalized) | AP = S(anterior chain) − S(posterior chain), thresholded at the normal 5th/95th centile | recovers the report's anterior-vs-posterior call at AUROC **0.604** [0.568, 0.642]; directionally correct (anterior +0.19 vs posterior −0.37) but weak, and the expert ceiling for A/P predominance is unmeasured | **PROVISIONAL** — report "diffuse" as the default (correctly the majority); assert predominance only when AP clears the normal centile, and flag it as low-confidence |
| 5 | *"delta-predominant"* / *"theta-predominant"* / *"mixed"* | band index | current index (z_θ − z_δ) separates report-theta from report-delta at AUROC **0.579** / 0.556. Expert-expert exact band match is itself only 0.541 / 0.266 (κ 0.09–0.38) | **FORBIDDEN** pending two fixes: (i) the **7–8 Hz hole** (θ = 4–7, α = 8–13 — clinical theta runs to 8); (ii) the index must be the **share of excess power** `ΔP_θ/(ΔP_δ+ΔP_θ)` in linear units, not a difference of collinear z's (r = 0.87) |
| 6 | *"present in 48% of segments"* | fraction of that stage's segments with `S` above the 95th centile of normals at that age & stage | normals average **0.047** by construction; focal 0.289, generalized 0.419 | **ALLOWED** as a percentage |
| 6b | *"frequent"* / *"occasional"* / *"continuous"* (ACNS words) | mapping of (6) to report vocabulary | prevalence vs the reader's frequency word: ρ = **0.077**. The reliability of those words has never been measured, so no ceiling exists | **FORBIDDEN** |
| 7 | *"longest run 3.8 min over 4 episodes"* | run-length structure of supra-threshold segments | measured; normals 0.00 min, focal 0.47, generalized 1.40 | **PROVISIONAL** — needs split-half reliability (`scripts/108`) |
| 8 | *"accentuated in N2"* / *"present only during sleep"* | stage maximising (3); alert prevalence < 5% | V4a: on **spindle-verified** N2, cases exceed held-out normals at AUROC **0.854** (log δ) / **0.844** (DAR), undiminished from all-N2 | **ALLOWED** |
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
4. **N1 numbers are on hold.** Alpha attenuation is *negative* in focal (−0.34) and generalized (−0.20) but
   positive in normals (+0.04) in N1 — abnormal N1 has *more* alpha than normal N1. Unexplained; possibly a
   staging artifact. Resolve before any N1 clause ships.

## The sentence this table permits, today

> *Left-sided slowing, maximal in the temporal chain: 2.1 SD above age- and stage-matched normal (94th
> centile), with paucity of faster activity; present in 48% of alert segments; longest run 3.8 min over 4
> episodes; accentuated in N2, where it reaches 3.0 SD.*

No adjective. No band. No frequency word. No peak. Every clause a number with a reference population.
