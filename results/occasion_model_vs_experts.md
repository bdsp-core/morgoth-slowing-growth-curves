# Phase A/B — our normative score vs the 18-expert panel (external test set)

100 of 100 EEGs scored. Pipeline unchanged; norms from our cohort; **no refitting, no threshold tuning on these data**. Predictions P1–P10 were fixed in `docs/phaseA_preregistration.md` before this ran.


## generalized slowing (expert majority prevalence 0.19, n=100)

| score | AUROC [95% CI] | n |
|---|---|---|
| `gen_TAR_W_routine` | 0.871 [0.785, 0.942] | 95 |
| `gen_logdelta_N1_routine` | 0.877 [0.776, 0.955] | 96 |
| `gen_combo_WN1_routine` **(pre-specified primary)** | 0.903 [0.832, 0.958] | 100 |
| `gen_TAR_allstage_routine` | 0.870 [0.769, 0.954] | 100 |
| `gen_log_delta_allstage_routine` | 0.907 [0.839, 0.958] | 100 |
| `gen_TAR_W_union` | 0.827 [0.727, 0.911] | 95 |
| `gen_logdelta_N1_union` | 0.737 [0.615, 0.856] | 96 |
| `gen_combo_WN1_union` | 0.828 [0.731, 0.914] | 100 |
| `gen_TAR_allstage_union` | 0.828 [0.723, 0.923] | 100 |
| `gen_log_delta_allstage_union` | 0.760 [0.629, 0.871] | 100 |

*Best-on-test is `gen_combo_WN1_routine` (0.903); it was selected using these labels and is therefore OPTIMISTIC. All pre-registered verdicts below use the pre-specified primary `gen_combo_WN1_routine` (0.903).*

**Operating point** for prespecified primary score `gen_combo_WN1_routine` (n=100):

| calls | bal. accuracy | sens | spec | κ vs each expert (median) |
|---|---|---|---|---|
| naive z>2 | 0.646 | 0.316 | 0.975 | — |
| **LOO Youden (P10)** | **0.835** | 0.842 | 0.827 | 0.459 |
| *average expert vs consensus* | *0.809* | — | — | *0.451* (expert–expert) |

- P10 (recalibration gain ≥ 0.05 over naive z>2): gain = **+0.189** → HOLDS
- κ_ae (median 0.459) vs κ_ee (median 0.451); attenuation benchmark √κ_ee = 0.672

**Phase B — consensus proportion (conspicuity):** Spearman ρ = **0.652** (p=2.0e-13, n=100) using `gen_combo_WN1_routine`.
- P6 (ρ ≥ 0.45; fails if < 0.30): HOLDS
- P7 (exceeds the report-adjective severity ρ = 0.050; fails if ≤ 0.15): HOLDS

## focal slowing (expert majority prevalence 0.14, n=100)

| score | AUROC [95% CI] | n |
|---|---|---|
| `foc_max_TAR_routine` | 0.627 [0.473, 0.780] | 100 |
| `foc_asym_TAR_routine` **(pre-specified primary)** | 0.738 [0.574, 0.882] | 100 |
| `foc_max_log_delta_routine` | 0.591 [0.411, 0.758] | 100 |
| `foc_asym_log_delta_routine` | 0.831 [0.738, 0.910] | 100 |
| `foc_max_TAR_union` | 0.571 [0.394, 0.744] | 100 |
| `foc_asym_TAR_union` | 0.711 [0.547, 0.865] | 100 |
| `foc_max_log_delta_union` | 0.474 [0.321, 0.641] | 100 |
| `foc_asym_log_delta_union` | 0.809 [0.699, 0.905] | 100 |

*Best-on-test is `foc_asym_log_delta_routine` (0.831); it was selected using these labels and is therefore OPTIMISTIC. All pre-registered verdicts below use the pre-specified primary `foc_asym_TAR_routine` (0.738).*

**Operating point** for prespecified primary score `foc_asym_TAR_routine` (n=100):

| calls | bal. accuracy | sens | spec | κ vs each expert (median) |
|---|---|---|---|---|
| naive z>2 | 0.500 | 0.000 | 1.000 | — |
| **LOO Youden (P10)** | **0.564** | 0.500 | 0.628 | 0.129 |
| *average expert vs consensus* | *0.801* | — | — | *0.394* (expert–expert) |

- P10 (recalibration gain ≥ 0.05 over naive z>2): gain = **+0.064** → HOLDS
- κ_ae (median 0.129) vs κ_ee (median 0.394); attenuation benchmark √κ_ee = 0.628

**Phase B — consensus proportion (conspicuity):** Spearman ρ = **0.398** (p=4.2e-05, n=100) using `foc_asym_TAR_routine`.

## Pre-registered predictions

- **P1** generalized AUROC 0.85–0.93 (fails <0.80): `gen_combo_WN1_routine` = **0.903** → HOLDS
- **P2** focal AUROC 0.70–0.85 and clearly < generalized: `foc_asym_TAR_routine` = **0.738** → HOLDS
- **P3** (generalized) at the mean expert's specificity (0.884) our sensitivity is **0.684** vs the expert's 0.735 → the mean expert point lies ABOVE our ROC → FAILS
- **P3** (focal) at the mean expert's specificity (0.899) our sensitivity is **0.429** vs the expert's 0.703 → the mean expert point lies ABOVE our ROC
- **P4** we should not beat Morgoth's focal AUROC (0.923): ours 0.738 (primary) / 0.831 (best-on-test) → HOLDS

**P5 — W/N1 restriction vs all-stage, like-for-like (routine reference):**

| feature | W/N1-restricted | all-stage | winner |
|---|---|---|---|
| TAR | 0.871 | 0.870 | W/N1 |
| log_delta | 0.877 | 0.907 | all-stage |

- **P5** predicted W/N1 beats all-stage for generalized slowing → **FAILS** (1/2 features). The all-stage score already compares every segment to *its own stage's* norm, so discarding sleep buys nothing here — and the experts read the whole study. **What does matter is the REFERENCE POPULATION**, below.

**The vigilance-matched REFERENCE is what carries the effect** (same scores, routine-alert vs union normals):

| score | routine (alert) ref | union ref | Δ |
|---|---|---|---|
| `gen_TAR_W` | 0.871 | 0.827 | **+0.044** |
| `gen_logdelta_N1` | 0.877 | 0.737 | **+0.140** |
| `gen_combo_WN1` | 0.903 | 0.828 | **+0.075** |
| `gen_TAR_allstage` | 0.870 | 0.828 | **+0.042** |
| `gen_log_delta_allstage` | 0.907 | 0.760 | **+0.147** |
