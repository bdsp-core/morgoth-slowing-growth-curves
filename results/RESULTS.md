# Results — v1 (stage-agnostic)

Growth curves + discrimination for EEG slowing, built from the Growth_curves feature set
(12,379 recordings: normal 4,916 / focal_slow 2,067 / general_slow 5,396). Fully reproducible:
`scripts/03_compute_features.py → 04_fit_reference_models.py → 06_discrimination.py → 05_score_patients.py`.

**Scope:** v1 is **stage-agnostic** — the Growth_curves set is unstaged (all "Other"). Sleep-stage
stratification is being added by staging the raw EEG with morgoth2 (see docs/sleep_staging.md);
until then, curves pool all wake/sleep segments. Everything below is age- and sex-conditioned.

## 1. Cohort — see [Table 1](../README.md#table-1--cohort-characteristics)
Sex ~50/50 across groups. Controls skew ~20 yr younger than the slowing groups → **age adjustment is
essential**, which is why all scoring is done vs the age×sex normal curve.

## 2. Growth curves validate against known development
Absolute delta power (`figures/curves/log_delta__whole_head.png`) shows the textbook trajectory:
**high in infancy (~3.1 log units), steep decline through childhood to a plateau by ~30, slight
elderly uptick** — and the slowing groups sit clearly above the normal band. The normal-referenced z
is **centered on 0 for normals (median 0.03)** and elevated for focal (0.93) and generalized (1.02),
confirming the reference model is well calibrated. Curves for 8 features × 5 regions are in
`figures/curves/`.

## 3. Which features discriminate? (age & sex adjusted AUC)
Top features (full table: [discrimination.md](discrimination.md)). `auc_adj` = AUC of the
normal-referenced z; `auc_raw` = unadjusted (age-confounded).

| feature | region | pair | AUC (adj) | AUC (raw) |
|---|---|---|---|---|
| **log_delta** (absolute δ power) | whole_head | normal vs generalized | **0.75** | 0.68 |
| log_delta | L_temporal | normal vs focal | 0.74 | 0.64 |
| log_theta | whole_head | normal vs focal | 0.74 | 0.64 |
| **TAR** (θ/α) | L_temporal | normal vs generalized | 0.73 | 0.71 |
| log_theta | L_temporal | normal vs focal | 0.73 | 0.64 |

**Findings.** (1) **Absolute delta and theta power are the strongest single markers** of slowing
(AUC ≈ 0.73–0.75). (2) **Age/sex adjustment clearly helps** (0.75 vs 0.68 raw), confirming the age
confound. (3) The **theta/alpha ratio (TAR)** is a strong ratio marker. (4) Relative-power and
whole-head-vs-regional differences are secondary here — expected, since v1 pools sleep stages
(sleep delta dilutes the pathological signal; stratifying by stage should sharpen this).

## 4. Topography classifier (provisional)
`topo_class` (focal / lateralized / generalized / multifocal / none) vs true label:

```
topo_class    focal  generalized  lateralized  multifocal  none
normal           61           61            9           1  4784   (97% correctly "none")
focal_slow      134           81           34           7  1769
general_slow    281          324           39          16  4426
```
**High specificity (97% of normals → none), low sensitivity** at the strict z>2 / dominance
thresholds — most abnormal recordings' *median* z stays below threshold because slowing is often
intermittent/focal. This is the expected v1 behavior and the two clear next steps are (a) calibrate
thresholds against expert labels and (b) use **segment-level burden** (already computed) rather than
the recording median to recover sensitivity for intermittent slowing.

## 5. Report generation
`report/phrase.py` turns the scoring table into sentences (examples:
[example_reports.md](example_reports.md)), e.g.:
> *Record: continuous moderate generalized delta slowing, present in 100% of segments; generalized
> burden 3.7 SD above norms.*
> *Record: frequent moderate left temporal delta slowing … left–right asymmetry 3.8 SD above normal.*

## 6. Limitations / next
- **Stage-agnostic** (biggest one) — staging in progress via morgoth2 on the raw EEG + Apple GPU.
- Topography thresholds uncalibrated; use segment burden for sensitivity.
- Empirical-percentile→z replaced by parametric weighted-Gaussian z (unbounded); revisit for
  non-Gaussian features.
- `focal` detection is weak — asymmetry signal needs the segment-level + finer subregions.
