# Stage-specific slowing: per-stage present/absent call and its report-state validation

The deviation field norms `S` per stage (scripts/107), so we can emit a per-stage present/absent slowing call: **slowing present in stage X iff prevalence_X > 0.10** (double the 5% false-positive rate baked into the normal 95th-centile threshold). Morgoth gates the recording; this is the piece Morgoth cannot do (docs/description_architecture.md §1c).

## Part A — per-stage present rate, by group

Fraction of recordings called slowing-present in each stage (denominator = recordings staged in that stage). Groups per scripts/107 (`clean_normal` / `has_focal_slow` / `gen_class==pathologic`).

| stage | clean-normal | focal | generalized |
|---|---|---|---|
| W | 0.123 (n=3918) | 0.175 (n=2684) | 0.256 (n=889) |
| N1 | 0.128 (n=1977) | 0.462 (n=1731) | 0.603 (n=778) |
| N2 | 0.127 (n=1595) | 0.414 (n=1899) | 0.427 (n=939) |
| N3 | 0.115 (n=278) | 0.312 (n=874) | 0.292 (n=595) |
| REM | 0.122 (n=1098) | 0.424 (n=656) | 0.556 (n=189) |

**Calibration.** With the threshold at the normal 95th centile, a clean-normal recording is called present iff >10% of its segments in that stage exceed it — well above the 5% expected by chance — so clean-normals sit low by construction (W present rate 0.123). Focal and generalized rise above them in every stage, and the call fires in **sleep as well as wake** — the stage-specific capability the architecture asked for.

## Part B — report-state scan: the validation denominator

Clause-scoped, negation-aware scan of the raw report text (reusing scripts/95: split on `[.;\n]`, 40-char pre-`slow` negation window). `wake_slow` = a non-negated slowing clause names a wake word (awake/wakefulness/alert); `sleep_slow` = names a sleep word (sleep/drows*/somnolen*/N2/N3/stage 2/stage 3). Only the two booleans are written (`data/derived/report_state_labels.parquet`); raw text never leaves the scan.

**104,984 reports** contain a non-negated slowing clause. Of those, the state the report localises slowing to:

| localization | reports | share of slowing reports |
|---|---|---|
| wake only | 4,706 | 4.5% |
| sleep only | 42,299 | 40.3% |
| both wake and sleep | 11,118 | 10.6% |
| unspecified (slowing named, no state word) | 46,861 | 44.6% |

Any wake mention: **15,824**; any sleep mention: **53,417**. A sleep word co-occurs with slowing in **51%** of slowing reports — so 'sleep-localized slowing' looks *common*, not rare. **That count is misleading, and Part C shows why:** physiological drowsiness and sleep ARE slow, and reports routinely say so ('slowing with drowsiness/sleep' is a normal finding). The raw sleep-word co-occurrence therefore does NOT isolate pathological sleep slowing. The wake mention is the rarer but cleaner signal.

## Part C — directional validation (clean_pair, reports only)

Join per-stage calls to report-state labels on `bdsp_id`+`date` (date = cohort_metadata `eeg_datetime[:8]`), restrict to `clean_pair` recordings carrying a report: **n=9,928** (report localises wake slowing: 1,448; sleep slowing: 5,575).

### C0 — first, is each report-state label a pathology marker at all?

Abnormal rate (`is_abnormal`) among recordings the report does / doesn't localize slowing to a state — a prerequisite for using the label as ground truth:

| report label | abnormal rate if TRUE | abnormal rate if FALSE | clean-normals flagged |
|---|---|---|---|
| wake_slow | **0.95** | 0.39 | 41 |
| sleep_slow | 0.46 | 0.50 | 2,864 of 4,798 clean-normals |

**`wake_slow` is a clean pathology marker** (95% abnormal vs 39%; only 41 clean-normals flagged). **`sleep_slow` is not** — its abnormal rate (0.46) is no higher than its complement (0.50), and it flags MORE clean-normals (2,864) than it leaves unflagged (1,934). Report 'sleep slowing' is dominated by *normal physiological* sleep slowing, so it cannot serve as a pathological-sleep-slowing denominator.

### C1 — directional tests (full population)

Score = the field's stage prevalence; label = the report's state localization. 'Without' = every other reported clean_pair recording (includes normals), so a positive AUROC here blends state-concordance with generic abnormal-vs-normal separation.

| report localizes | field score | AUROC [95% CI] | median present vs absent | MWU p | n pos/neg |
|---|---|---|---|---|---|
| WAKE slowing | W prevalence (the plan's test) | 0.503 [0.489,0.518] | 0.000 vs 0.000 | 6.55e-01 | 1140/6266 |
| WAKE slowing | N1 prevalence | 0.566 [0.546,0.586] | 0.000 vs 0.000 | 5.02e-11 | 753/3606 |
| WAKE slowing | best-stage prevalence | 0.569 [0.553,0.585] | 0.059 vs 0.000 | 1.83e-19 | 1408/8182 |
| SLEEP slowing | N2/N3 prevalence (the plan's test) | 0.433 [0.419,0.448] | 0.000 vs 0.000 | 3.02e-18 | 2351/2134 |
| SLEEP slowing | N2 prevalence | 0.433 [0.418,0.449] | 0.000 vs 0.000 | 1.30e-16 | 2217/1838 |
| SLEEP slowing | best-stage prevalence | 0.453 [0.442,0.465] | 0.000 vs 0.026 | 2.04e-17 | 5362/4228 |

The field's per-stage prevalence is heavily zero-inflated (median 0 in every stage), so read the AUROCs, not the medians. **The plan's wake->W test is at chance** (AUROC 0.503): report wake-slowing does not track the field's *W-specific* call, because the field puts most detected slowing in N1/N2 (Part A: focal N1 present rate 0.46 vs W 0.18). It shows a modest signal against N1 / best-stage (0.566 / 0.569) — but that is mostly the abnormal-vs-normal leakage (wake_slow is 95% abnormal). **The plan's sleep->N2/N3 test runs BELOW chance** (0.433) — the direct consequence of C0: reports that name sleep slowing are enriched for *normals*, which have low pathological N2/N3 prevalence.

### C2 — confound-free concordance (within abnormal recordings only)

Restricting to abnormal recordings (**n=4,719**) removes the abnormal-vs-normal leakage and asks the pure question: *given the recording is abnormal, does the report's state localization agree with the field's per-stage localization?*

| report localizes | field score | AUROC [95% CI] | n pos/neg |
|---|---|---|---|
| WAKE slowing | W prevalence | 0.487 [0.470,0.504] | 1083/2201 |
| WAKE slowing | N1 prevalence | 0.452 [0.428,0.476] | 718/1517 |
| SLEEP slowing | N2/N3 prevalence | 0.451 [0.431,0.472] | 1237/1392 |
| SLEEP slowing | N2 prevalence | 0.443 [0.422,0.466] | 1162/1154 |

**Every within-abnormal concordance sits at or below 0.5.** The report's state-localization and the field's per-stage prevalence do not agree at the recording level once abnormal-vs-normal is removed. This is the reader-reliability limit V4a is built around: readers localize slowing to a *state* coarsely and inconsistently (sleep especially), so report text is not a usable criterion for a *stage-specific* call.

## What is and isn't possible

- **The per-stage present/absent call itself (Part A) is sound** — calibrated to the normal 95th centile and dose-responsive across groups in every stage, including sleep (focal/gen N2 present rate 0.41/0.43 vs clean-normal 0.13). Its validity rests on construct validity, not on report text.

- **Report WAKE-slowing validates abnormal-vs-normal, not stage.** `wake_slow` is a clean pathology flag (95% abnormal) but at chance against the field's W-specific call (AUROC 0.503; 0.487 within abnormals) — it says the recording is slow, not that the slowing lives in wake.

- **A report-text SLEEP-specific test is not achievable, and not merely underpowered.** 5,575 reports localize slowing to sleep (a large denominator), but the label is *contaminated*: normal physiological sleep is slow and reports say so, so `sleep_slow` flags normals as much as abnormals and runs below chance against pathological N2/N3 prevalence (0.433). No clause-scoping fixes this — the words for physiological and pathological sleep slowing are the same.

- **The decisive sleep anchor is therefore not report text but the spindle-verified V4a result** (results/v4a_wake_sleep.md), cited not recomputed: recordings whose report names slowing in WAKE and never mentions sleep still carry genuine N2 excess on spindle-verified true-N2 segments (**AUROC 0.85**, an independent delta-free marker that the stage is truly N2). That within-subject, spindle-gated design — precisely because it does NOT rely on the reader localizing sleep slowing — is what establishes that stage-specific sleep slowing is real where the reader was silent.

