> ⚠ **SUPERSEDED — historical only.** This doc asserts facts now overridden by `docs/analysis_plan.md` (the SAP) and `docs/claims_table.md` (e.g. theta = 4–8 Hz; severity adjectives / ACNS frequency words / band-from-our-features are FORBIDDEN output; artifact segments are flagged not stripped; zero reuse of prior derived tables). Do not implement from this file. Retained for provenance.

# Report architecture: Morgoth as gate, normative features as description

## The design: Morgoth decides *whether/what*, our features decide *how to describe*

Separate **detection** (Morgoth, validated against expert reports) from **description** (our
normative features). Morgoth chooses which branches to open; our features supply the adjectives and
the quantitative parenthetical.

### Three-tier gate (hierarchical), using all the heads
```
                 ┌───────────────────────────┐  abnormal
 EEG ─► TIER 1:  │ NORMAL.pth (+ _EEGlevel)   │──────────►┌───────────────────────────┐  slowing
                 │ normal vs abnormal          │           │ TIER 2: SLOWING.pth        │─────────►  TIER 3
                 └───────────────────────────┘           │ pathological slowing?       │
                        │ normal                          └───────────────────────────┘
                        ▼                                        │ no slowing
                 "Normal EEG."                                   ▼
                                                    "Abnormal, but not due to slowing"
                                                    (out of scope — other heads)

 TIER 3:  FOC_SLOWING_EEGlevel.pth  &  GEN_SLOWING_EEGlevel.pth  → P(focal), P(generalized)
          → choose branch(es): focal / generalized / both → DESCRIBE with normative features
```
- **Tier 1 — normal vs abnormal** (`NORMAL.pth` + `NORMAL_EEGlevel.pth`): is the EEG abnormal at all?
  If normal, say so and stop. (Separate head from slowing — an EEG can be abnormal for non-slowing
  reasons, or normal.)
- **Tier 2 — slowing present?** (`SLOWING.pth` + EEG-level): is there *pathological slowing*
  specifically? Only this gates our slowing description. High specificity to expert reporting → we
  don't over-call slowing on normative-deviation alone.
- **Tier 3 — focal vs generalized** (`FOC_SLOWING_EEGlevel.pth`, `GEN_SLOWING_EEGlevel.pth`): sets
  the topographic branch(es). P(focal)/P(generalized) can both fire (multifocal / mixed).

Each head is two-stage: a **window-level** model (reads raw `.mat`, same MPS path as staging) →
an **EEG-level** aggregator (`EEG_level_head.py`) → one probability per recording.

### DESCRIBE with normative features (only the branch(es) Tier 3 opened)
Our features answer what a binary head can't: **where** (region+side from regional burden +
asymmetry z), **band** (δ/θ/mixed), **severity** (patient z), **prevalence/intermittency** (ACNS
words), **persistence** (longest run, #episodes), and **state-dependence** (wake vs only-in-sleep;
stage most accentuated). For generalized: add "paucity of faster activity" when relative α/θ is low.

### Why gate + describe beats either alone
Our z-scores are *sensitive* but not calibrated to how experts *report*; Morgoth is *calibrated to
expert calls* but can't describe. Consistency is also a signal: if Morgoth says focal but our
asymmetry z ≈ 0, lower confidence / recommend morphology review. Calibrate each gate threshold on the
labeled cohort (normal/focal/general folders) to the desired operating point.

## What to describe (the report axes)
Once gated in, the sentence is assembled from (feature_spec.md §3, §6, §8):
- **Location / laterality** — region + side (from regional burden + asymmetry z).
- **Band / type** — delta vs theta vs mixed vs low-frequency.
- **Severity** — patient-level z (mild / moderate / marked).
- **Prevalence / intermittency** — % of usable time abnormal → ACNS words (rare … continuous).
- **Persistence** — longest continuous run, number of episodes, median episode duration.
- **State-dependence** *(new, enabled by staging)* — present in wake vs only in sleep; the stage
  where it is most accentuated (max per-stage burden). E.g. *"…only during sleep, accentuated in N2."*

## Which features to keep (feature selection)
We deliberately compute more features than we'll report. To prune, your idea is sound — **distill a
target into our features and read importances** — with these refinements:

1. **Two targets, compared:**
   - **Morgoth P(slowing)** (regression/soft label) — "which of our features reconstruct the expert-
     matched detector" (knowledge distillation).
   - **Expert labels** (normal/focal/general folders) — ground truth, to check Morgoth isn't leading
     us astray.
2. **Models with built-in selection + honest importance:**
   - **L1-logistic (LASSO)** for a sparse, directly-selected set.
   - **Gradient boosting + SHAP** for nonlinear importance and interactions.
3. **Handle multicollinearity (critical here):** our features are highly correlated (log_delta,
   rel_delta, DAR, TAR all track slowing). Raw importances split credit arbitrarily. Fixes:
   - **Cluster features** (by correlation) and keep one interpretable representative per cluster.
   - **Stability selection** (bootstrap the LASSO; keep features chosen in ≥X% of resamples) for
     robustness to correlated swaps.
4. **Two-track keep-list:** don't select purely on detection AUC — a feature can be *description-
   essential* (laterality, band, stage-accentuation, persistence) even if redundant for detection.
   - **Track A (detection):** the sparse distilled set that reproduces the gate.
   - **Track B (description):** always retain one feature per clinical axis (location, side, band,
     prevalence, persistence, stage) so the sentence stays complete.
5. **Validate the pruned set** end-to-end: does gate + pruned-features still reproduce expert
   focal/general labels as well as the full set? Report the drop.

## Concrete plan (this repo)
- `scripts/07b_run_morgoth_slowing.py` — run `SLOWING.pth` / `FOC_/GEN_SLOWING_EEGlevel.pth` on the
  cohort (same Mac/MPS path as staging) → per-recording P(slowing) + focal/gen probs.
- `scripts/08_feature_selection.py` — distill both targets into our features (LASSO + GBM/SHAP +
  stability selection + correlation clustering) → ranked, de-duplicated keep-list; two-track output.
- Wire the gate into `scripts/05` scoring: emit a description only when the gate fires; compose the
  sentence from the kept features incl. stage-dependence.
