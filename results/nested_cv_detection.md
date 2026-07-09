# Nested-CV detection: how much of scripts/84 is selection optimism?

Split on `bdsp_id`; 5-fold outer x 5 repeats = 25 outer estimates; inner 3-fold chooses the whole-head feature per stage on outer-train ids only; the age-kernel normal reference (bw=5.0) is rebuilt from outer-train clean-normals each fold. 'naive' reproduces scripts/84 (best feature picked and scored on the same 30%-held-out split, seed 0). CI = 2.5/97.5 pct spread across the 25 outer folds.

(Reference cap of 4000 was never hit; every fold used all outer-train clean-normals.)

## Primary: normal vs pathologic-generalized slowing (routine norm, whole-head)

`naive repro` reproduces scripts/84 to the third decimal on every stage, confirming the reimplementation is faithful. `optimism` is naive minus the honest nested value; `of which feature-selection` is the share attributable to picking the feature (fixed-feat nested minus feature-select nested), the rest being reference re-estimation / a different held-out split.

| stage | published (84) | naive repro | nested (feature-select) | nested (fixed feat) | optimism = naive-nested | of which feature-selection |
|---|---|---|---|---|---|---|
| W | TAR 0.848 | TAR 0.848 | 0.856 [0.839,0.867] | TAR 0.856 [0.839,0.867] | -0.007 | +0.000 |
| N1 | log_delta 0.875 | log_delta 0.875 | 0.871 [0.861,0.881] | log_delta 0.874 [0.861,0.884] | +0.004 | +0.003 |
| N2 | DAR 0.791 | DAR 0.791 | 0.795 [0.776,0.805] | DAR 0.795 [0.776,0.805] | -0.005 | +0.000 |
| N3 | DAR 0.758 | DAR 0.758 | 0.751 [0.726,0.777] | DAR 0.751 [0.726,0.777] | +0.006 | +0.000 |
| REM | TAR 0.825 | TAR 0.825 | 0.825 [0.800,0.845] | TAR 0.828 [0.808,0.846] | +0.001 | +0.004 |

per outer fold ~ 819 pos / 1013 held-out routine-normal neg (of ~5x that pooled).

## Inner-loop feature selection stability (gen_pathologic)

Count of the 25 outer folds in which each feature was chosen by the inner loop, per stage.

| stage | TAR | DAR | log_delta | log_theta | rel_delta | modal |
|---|---|---|---|---|---|---|
| W | 25 | 0 | 0 | 0 | 0 | TAR |
| N1 | 0 | 6 | 19 | 0 | 0 | log_delta |
| N2 | 0 | 25 | 0 | 0 | 0 | DAR |
| N3 | 0 | 25 | 0 | 0 | 0 | DAR |
| REM | 13 | 11 | 1 | 0 | 0 | TAR |

## abnormal: nested vs naive (whole-head)

| stage | naive feat/AUROC | nested (feature-select) | nested (fixed feat) | optimism |
|---|---|---|---|---|
| W | TAR 0.769 | 0.777 [0.762,0.796] | TAR 0.777 [0.762,0.796] | -0.007 |
| N1 | log_delta 0.800 | 0.799 [0.791,0.808] | log_delta 0.799 [0.791,0.808] | +0.001 |
| N2 | log_delta 0.715 | 0.706 [0.691,0.720] | DAR 0.710 [0.696,0.722] | +0.009 |
| N3 | DAR 0.702 | 0.698 [0.663,0.728] | DAR 0.698 [0.663,0.728] | +0.005 |
| REM | log_delta 0.749 | 0.750 [0.733,0.765] | TAR 0.733 [0.718,0.754] | -0.000 |

## focal: nested vs naive (whole-head)

| stage | naive feat/AUROC | nested (feature-select) | nested (fixed feat) | optimism |
|---|---|---|---|---|
| W | TAR 0.765 | 0.772 [0.750,0.789] | TAR 0.772 [0.750,0.789] | -0.008 |
| N1 | log_delta 0.803 | 0.802 [0.784,0.819] | log_delta 0.802 [0.784,0.819] | +0.001 |
| N2 | log_delta 0.719 | 0.713 [0.691,0.733] | DAR 0.703 [0.677,0.726] | +0.006 |
| N3 | DAR 0.698 | 0.693 [0.669,0.718] | DAR 0.693 [0.669,0.718] | +0.005 |
| REM | log_delta 0.756 | 0.756 [0.737,0.773] | TAR 0.726 [0.707,0.752] | +0.000 |

## Verdict

Mean feature-selection-inclusive optimism across stages (gen_pathologic): -0.000 (per-stage range -0.008 to +0.007). Largest single-stage move: N3 (0.758 -> 0.751, +0.007), well inside the 25-fold spread. The published whole-head detection numbers **SURVIVE nested CV essentially unchanged**; every published value lies inside the nested CI, and the honest per-stage estimates are the 'nested (feature-select)' column.

Why the optimism is negligible: with ~800+ positives and ~1000 held-out normals per fold the AUROC is estimated tightly, and the per-stage winner is dominant/stable (W->TAR, N2/N3->DAR unanimous; N1->log_delta 19/25), so best-of-5 selection adds almost no upward bias. The one unstable stage is REM (TAR 13 / DAR 11), but there TAR and DAR have near-identical AUROC so the choice does not matter. Consequently the 'of which feature-selection' share is ~0.000-0.004 at every stage: the a-priori fixed-feature nested (a cheap honest number the paper can quote) equals the full nested-selection number to within 0.004 AUROC.
