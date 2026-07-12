# Audit Report 1 — SAP fidelity review and interpretation of findings

**Date:** 2026-07-11
**Auditor:** Claude (Fable 5 sub-agents ×5, synthesis by Opus 4.8)
**Scope:** `docs/analysis_plan.md` (SAP v1.0, 664 lines, §1–13 + Appendix A) vs. the implementing code, plus a scientific interpretation of the findings to date.
**Method:** five independent adversarial audits (§1–3 cohort/labels/manifest; §4–5 pipeline/features; §6–7 norms/gate/describe; §8–13 statistics/figures/build-order; results interpretation), followed by direct verification of the load-bearing claims by the synthesizing auditor.
**Constraint:** read-only. No code, data, or document was modified. This file is the only artifact created.

---

## 0. Verdict in one paragraph

The **fleet pipeline** (`scripts/31_segment_master_worker.py` + `src/morgoth_slowing/`) is a careful, well-tested, largely faithful implementation of SAP §4–5: segmentation, the 24-hour coverage cap, the θ 4–8 Hz band-edge fix, flag-don't-strip artifact handling, the van Putten metric module, and the `segment_master` schema are all correct and guarded by tests. That is real engineering discipline and it should be said first. **But nothing consumes it.** Every number currently in `results/` and `docs/manuscript_draft.md` is computed from the legacy `bdsp_id`-keyed derived tables that SAP §13 and Appendix A pitfall 5 explicitly forbid — so the SAP's central governing principle ("one clean-room computation, zero reuse") is not yet satisfied by a single reported result. On top of that, three independent violations each threaten a primary conclusion: the **amount score `S` is fit by logistic regression on report labels**, which makes the paper's signature "readers under-report slowing" claim circular by the project's own rule; the **normative model is a Gaussian kernel mean/SD, not the pre-registered GAMLSS/BCT**, so every emitted centile is misstated; and there is **no k-fold cross-fitting**, making the headline calibration check tautological. Finally — and most urgently — an **uncommitted re-run performed last night has silently collapsed the paper's headline detection AUROC from 0.848 to 0.638**, and the manuscript still quotes the old number. Nothing should be submitted until that is explained.

---

## 1. The most urgent finding: the headline result has silently collapsed

This was verified directly by the synthesizing auditor, not merely reported by a sub-agent.

The committed (HEAD) results agree with the manuscript. The **uncommitted working-tree results, regenerated 2026-07-11 at 21:38–21:55**, do not:

| Quantity | Committed at HEAD (= manuscript) | Working tree, regenerated 21:38–21:55 |
|---|---|---|
| Generalized detection, W, TAR, routine ref | **0.848** [0.834, 0.860], n=3883/1451 | **0.638** [0.623, 0.654], n=4123/1405 |
| Generalized detection, N1 | **0.852** | **0.648** |
| Sparse score, nested-CV AUROC | **0.933** [0.922, 0.946] | **0.683** [0.667, 0.699] |
| Sparse score, parsimonious model | 3 features | **6 features**, 0.670 |

`docs/manuscript_draft.md:172` still asserts *"AUROC 0.848 in W (TAR) and 0.875 in N1 (log delta) … positives n = 3,883, negatives n = 1,451"*, and `scripts/96_nested_cv_detection.py:42-43` hardcodes `PUBLISHED = {"W": ("TAR", 0.848), "N1": ("log_delta", 0.875)}` as stale constants. The underlying `data/derived/channel_stage_features.parquet` and `labels_unified.parquet` were both rewritten at **21:55**.

**This is roughly a −0.21 AUROC move, an order of magnitude outside the bootstrap CI. It is not noise. One of the two numbers is wrong, and the repo does not currently say which.**

### What it is *not*

I tested the most obvious candidate — that the rebuilt feature table now pools the `expansion` cohort with `cohort`, which SAP §8.1:421-422 explicitly warns against ("ratio features are **not** pooled across sources with different acquisition"). Decomposing the current table:

| Subset | n_pos | n_neg | AUROC (TAR, whole-head, W) |
|---|---|---|---|
| Pooled (cohort + expansion) | 7162 | 4770 | 0.667 |
| **Cohort only** | 5398 | 4193 | **0.643** |
| Expansion only | 1764 | 577 | 0.671 |

**Cohort-only is still 0.643.** The collapse is intrinsic to the recomputed features/labels, not an artifact of pooling.

The SAP's warning is nonetheless *vindicated* and should be honored: the two sources have a genuine acquisition shift. Among **clean-normals**, whole-head wake TAR has median **0.871** in `cohort` but **1.423** in `expansion` — the expansion normals look "slower" than the cohort's abnormals do. Pooling them into one normative reference will distort the growth curves. Keep the norms `src`-stratified, or harmonize before pooling.

### What it most likely *is*

The leading hypothesis, and it is a good one, comes from the project's own documentation. `docs/claims_table.md:60-63` ("N1 resolved") records that **22–32% of abnormal *wake* segments were flat/suppressed and had been slipping past artifact rejection — and are now removed up front.** Those are exactly the segments that inflate delta/DAR/TAR in the abnormal group. The timing and the magnitude both fit.

If that is confirmed, the honest reading is uncomfortable but scientifically important:

> **A large share of the original 0.85–0.88 detection signal was suppression/electrode artifact, not slowing.**

This is not written down anywhere as a finding, and it should be. It reframes the paper's headline from *"we detect slowing at 0.87"* to *"we detect slowing at ~0.65, and the previously reported 0.87 — ours and, by implication, much of the prior qEEG slowing literature that did not remove suppressed segments — was partly artifact."* That is a **more interesting and more defensible paper** than the one currently drafted.

**Action (highest priority in the project):** run the ablation. Recompute detection toggling, one at a time: (a) flat/suppressed-segment rejection, (b) the θ 4–7 → 4–8 Hz band edge, (c) the `gen_pathologic` relabel, (d) expansion inclusion. Attribute the 0.21. Until this is done, no AUROC in the manuscript can be defended.

---

## 2. Provenance: the SAP's central rule is not yet in force

**SAP §13:642 and Appendix A pitfall 5:** *"No reuse of `segment_features` / `channel_stage_features` / `gate_probs` or any prior aggregate. Write everything fresh → `segment_master`."*

Every headline script reads exactly the banned tables:

| Script | Reads | Role |
|---|---|---|
| `84_vigilance_matched_detection.py:52` | `channel_stage_features.parquet` | **primary detection (P1)** |
| `85_table1_and_dose_response.py:33` | `channel_stage_features.parquet` | **Table 1** |
| `103_sparse_slowing_score.py:184` | `channel_stage_features.parquet` | sparse detector |
| `107_deviation_field.py:75` | `segment_features.parquet` | **the deviation field / `z`** |
| `108_descriptor_validation.py:103` | `segment_features.parquet` | descriptor reliability |
| `112_operating_points.py:23` | `gate_probs.parquet` | operating points |
| `47_vanputten_comparison.py:31-66` | `recording_features`, `adjusted_z`, `gate_probs` | **Table 6 / S7** |

Not one reads `segment_master` or `io/canonical.py`. The only live consumer of the canonical path is `scripts/32_segmaster_summary.py`, which self-describes at line 6 as *"NOT a statistical result (pilot n is small) — it proves the flow."*

The legacy tables are **first-600 s lineage, `bdsp_id`-keyed (patient, not recording), and flat-segments-stripped** — i.e. they instantiate pitfalls 1, 2, 3 and 4 simultaneously. `docs/DATA_INVENTORY.md:50-56` compounds this by advertising them under the heading **"Canonical tables (use these)"**, and `scripts/101_verify_figures_regenerate.py:12-33` — the reproducibility gate — *certifies* figures as regenerating from them.

The fleet run is incomplete: `segment_master` has ~17,971 partitions and `segment_summary` ~3,186, against a frozen manifest of 27,524.

`docs/RUN_READINESS.md:17-19` is honest about this (*"the downstream analysis scripts still read legacy `bdsp_id` tables… the analysis layer is a separate, post-run rebuild"*). That is a defensible plan. **But it means the current manuscript has no SAP-compliant number in it, and the DATA_INVENTORY heading actively misleads the next person.**

---

## 3. Findings that threaten a primary conclusion

### 3.1 `S` is supervised on report labels — the signature claim is circular — **VIOLATED**

**SAP §1:35-37:** *"`z` / `S` — the **unsupervised** normative deviation and the amount score. Because they are fit only to clinician-labeled normals and **never see the report label of abnormal cases**, they may support the claim 'we measure slowing readers under-report.'"* **§7.3:392:** *"Any 'we see what readers miss' result must trace to the unsupervised path."*

`scripts/107_deviation_field.py:136-148` builds the training target **from the report labels of abnormal cases** and fits `w` by L1 logistic regression:

```python
slow = ((L.gen_class == "pathologic") | (L.has_focal_slow == 1)) & L.clean_pair
keep = (slow | (L.clean_normal == True)).values
X = rec[keep]; y = slow[keep].astype(int).values
...
LogisticRegression(penalty="l1", ...).fit(X, y)
```

`S = w·z` (`107:158-159`) is the **amount** descriptor — claims-table row 3, the SD+centile in every generated sentence (`110:82-84`), the conspicuity correlation (ρ 0.549), and the V4a sleep-slowing result. `docs/claims_table.md:18` states of `z`/`S`: *"**Unsupervised** — fit to nothing but the normal population."* **That statement is false for `S`.**

By the project's own standard (`claims_table.md:22`: *"Violating this makes the paper circular. It is not a stylistic preference."*), P6, V4a and graded-conspicuity are currently circular.

**Aggravating factor — `S` names two different objects.** The SAP and claims table write "`z` / `S`" as one row meaning the *hand-weighted amount* score. The code and `sparse_slowing_score.md` use `S` for the *supervised L1 predictor*. The circularity guard is written in terms of a symbol that means two different things. **Fix the nomenclature before the next draft, or this will recur.**

**Fix:** rebuild the readers-miss claim on `z` alone (which *is* genuinely unsupervised — `107:100-119` — and the claim is defensible there), or learn `w` without report labels (e.g. first PC of the normal deviation field), or retract the claim.

### 3.2 The normative model is not GAMLSS — **VIOLATED**

**SAP §6.1:350-352:** *"GAMLSS with a **BCT (Box–Cox-t) / LMS** family per (stage × region × feature): μ, σ, ν, τ as penalized smooth functions of age."*

`scripts/gamlss_fit.R` is genuine GAMLSS/BCT. Its **only caller in the repo** is `scripts/76_keystone_growth_grid.py:54` — the Figure 2 script — restricted to one region (central) and 3 features.

Every analytical number instead comes from `scripts/107_deviation_field.py:50-59`: a **Gaussian-kernel-weighted mean and SD**. No BCT, no ν, no τ, normal-theory z. This is not a fallback — R is never invoked from the analysis pipeline at all.

The consequence is concrete: `110_generate_sentence.py:29-30` converts that z to a centile assuming normality (`norm.cdf(sd)*100`). `gamlss_fit.R:23-24` states precisely why BCT was chosen — *"young ages are far more right-skewed than old, and a constant nu biases the median high there."* **Every "Nth centile" the system emits is therefore misstated, and worst in children** — the regime where pediatric detection is already weakest.

`docs/manuscript_draft.md:100` claims GAMLSS/LMS "for each feature × region × sleep stage" (true only for one figure), and `docs/data_dictionary.md:160-189` documents a `norms` table with `mu/sigma/nu/tau` that **no script produces** — an orphan schema, itself a §5.5 violation.

**Fix:** route the deviation field through `gamlss_fit.R`, or stop calling it GAMLSS/LMS in the manuscript, the data dictionary, and the SAP. Also note `gamlss_fit.R` leaves τ constant (only μ, σ, ν get age formulas), so even the figure path does not meet §6.1 as written.

### 3.3 No cross-fitting — the calibration check is tautological — **VIOLATED**

**SAP §6.3:362-363:** *"Fit on `clean_normal` only; **k-fold cross-fitting** so a normal recording's own z uses out-of-fold parameters (no self-normalization optimism)."*

The `clean_normal`-only half is honored everywhere. The cross-fitting half is **absent** from the deviation-field path: `107:104` fits μ/σ on all clean-normals; `107:111-119` then scores those same normals with them. Same for the S re-standardization (`107:164-172`) and the 95th-centile prevalence threshold (`107:177-179`).

So the headline calibration result — *"clean-normals must average ~0.05 prevalence: observed 0.047"* (`107:264-268`) — is circular by construction; the 95th centile was **defined** on those recordings. The repo concedes this ("by construction"), which is honest, but §6.3 demanded out-of-fold parameters precisely so the number would *mean* something.

**The team already knows how:** `scripts/103_sparse_slowing_score.py:216` rebuilds the normal reference from train-fold normals only inside nested CV. The supervised detector has the guard; the unsupervised deviation field — which the paper leans on harder — does not.

### 3.4 Multiplicity correction does not exist — **NOT-IMPLEMENTED**

**SAP §8.6:480:** *"BH-FDR within families."* `grep -rn "fdr|multipletests|bonferroni|benjamini|holm" scripts/ src/` → **zero hits.**

Worst offender: `scripts/89_severity_axis_sweep.py` runs **7 features × 4 statistics × 2 scales × 3 strata** and reports *"Largest |rho| anywhere in the sweep"* (line 108) plus the "best 12 combinations" with **raw p-values** (line 112). A max-over-168 statistic reported with its uncorrected p is a textbook winner's curse. (The severity *null* is unaffected and stands — see §5 — but the inference machinery around it does not.)

### 3.5 Confidence intervals are not what §8 promises — **VIOLATED**

**SAP §8:414:** *"All CIs by stratified bootstrap over recordings (patient-clustered where a patient has multiple recordings)."*

- `84:41-48` resamples **rows**, unstratified and unclustered. (In practice one row ≈ one patient-stage, so it is approximately patient-level *by accident, not design*.)
- `96:252,274` and `103:267` — the reported "95% CI" is the **2.5/97.5 percentile across CV folds**. Fold-to-fold spread of overlapping resamples of one dataset is **not a confidence interval**; it has no coverage guarantee. At 5 folds (`103`) a 2.5th percentile is meaningless.
- `47_vanputten_comparison.py` and `results/vanputten_comparison.md` report **no CIs at all** — which makes the §8.7 adoption rule ("ΔAUROC > 0.02 with CIs excluding 0") **unadjudicable by construction**.

---

## 4. Findings that threaten a specific result

### 4.1 The `eeg_id` recording key exists in one script; 40 others collapse to the patient — **VIOLATED**

**SAP §3.3:127:** *"`eeg_id` is the recording key for every analysis."* **PITFALL 1** is report broadcast.

`scripts/88_report_pairing_audit.py` correctly keys on `eeg_id`. **No consumer honors it.** `drop_duplicates("bdsp_id")` appears **40 times** across non-archive scripts (`107:81`, `108:185`, `103:187`, `111:171`, `102:51`, `84:54`, …). On a table with one row per recording, that keeps an **arbitrary** EEG's label and applies it to the patient's other EEGs' features.

Scale: **3,090 patients contribute >1 EEG, accounting for 7,071 EEGs (26% of the manifest).** The repo knows — `scripts/99_exclude_multirecording_patients.py:3-8` says so explicitly, and its chosen remedy (drop those patients) is **not the SAP's remedy** and is nowhere pre-registered. Worse, `99`'s exclusion list is applied by only 13 of 25 label-consuming scripts — **not** by `84` (primary detection), `85` (Table 1), `96`, `47`, `112`, or `111` (the P6 "readers under-report" claim).

Because restudied patients skew abnormal (`99:45-49` checks for exactly this), the mislabeling is **non-random**.

### 4.2 The mandatory `clean_pair` filter is opt-in, and off by default — **VIOLATED**

**SAP §3.3:131:** *"**all** label-dependent analyses filter to `clean_pair`."*

`scripts/84_vigilance_matched_detection.py:60`: `if os.environ.get("CLEAN_PAIR") == "1":` — the SAP's mandatory filter is an **environment variable**, defaulting off, in the primary-endpoint script whose own comment (`84:56-58`) concedes *"17.2% of routine recordings carry a report broadcast from a sibling study."* It is also applied by `bdsp_id` membership, so it cannot separate a patient's clean EEG from their broadcast one.

### 4.3 `canonical.to_regions` averages logs and ratios — a differential bias pointed at the primary contrast — **VIOLATED**

`src/morgoth_slowing/features/recording.py:4-5` states the project's own doctrine: *"recompute ratios FROM region-mean band powers (**correct; avoids averaging ratios**)."* It implements that.

`src/morgoth_slowing/io/canonical.py:69-76` — the function **the SAP names** (§5.1:291, §5.4:334) — does the opposite: it takes the already-derived `log_*`, `rel_*`, `log_DAR/TAR/DTR`, `DTABR`, `ADR` columns and `groupby(...).agg("mean")` on them. So `mean(log P)` = log of the *geometric* mean, and `rel_delta` becomes a mean-of-ratios rather than a ratio-of-means.

**The bias is not constant across groups.** The Jensen gap scales with across-channel log-power variance — which is *what focality is*. A focal recording's `whole_head log_delta` is depressed more than a normal's, manufacturing spurious separation in the very contrast the paper reports. Two live scripts (`97:85`, `95b:125`) already use the other (correct) path, so the repo currently computes region features two incompatible ways.

### 4.4 The `posterior` label class is silently dropped — a bug misdiagnosed as a data limitation — **VIOLATED**

`results/report_extracted_labels.csv` contains **`posterior`: n = 1,319**. But `results/region_detection.md` and `region_gated.md` show only `parietal` **n=4** and `occipital` **n=6** — the extractor emits `posterior` (per the 4-region taxonomy at `scripts/20:47-50`) while the region analyses still expect `parietal`/`occipital` (`src/morgoth_slowing/report/parse.py:10`, which parses both and folds neither into `posterior`).

Consequences: **macro-F1 = 0.253** is computed over a 5-class problem in which two classes have n=4 and n=6 (guaranteed F1≈0, dragging the macro down) while the real fourth class is **absent entirely**. The manuscript's Limitations paragraph blames *"region-stratified data collection"*. **It is a label-mapping bug, and it is hiding 1,319 cases.**

### 4.5 The §7.4 lateralization estimator was never built — **VIOLATED**

**SAP §7.4:399-404** pre-registers side from the **signed homologous-pair deviation** (`z_R − z_L`) plus signed `pdBSI` and per-pair `Q_ASYM`, abstaining below the normal 97th-centile asymmetry, stored as `pred_focal_side` + `side_margin`.

`107:208-226` instead computes `E(r) = S(r) − mean S over the other lobes`, argmaxes over 4 lobes, and reads the side **off the first letter of the winning lobe's name**. No homologous-pair difference. No `pdBSI`, no `Q_ASYM` (both are computed at `31:209` and then never used for the side call). No `bilateral` output is reachable. The reported *"side recovered in 79.4%"* is the accuracy of an **unregistered** estimator — while `claims_table.md:35` cites *"signed asymmetry AUROC 0.881"* as evidence for a clause the code does not compute.

### 4.6 The abstain threshold is calibrated on a different statistic than it tests — **VIOLATED**

`110:128` builds the null over **ALERT stages only** (`D[D.stage.isin(ALERT)]`); `110:62` computes the test statistic as a max over **all five stages**. A max over 5 is stochastically larger than a max over 2, so `E` is systematically inflated relative to its own threshold: **the system abstains less often than its calibration implies — it invents lobes and sides more often than claims-table row 11 guarantees.** This is a two-line fix with a direct patient-safety reading.

### 4.7 Band language ships in the emitted sentence — **VIOLATED**

`docs/claims_table.md:58`: *"**No band language ships**"*; the permitted sentence at `claims_table.md:65-71` closes with *"No adjective. **No band.** No frequency word. No peak."*

`110:91-92` computes the band word unconditionally and `110:112` splices it into the sentence as bare apposition (*"Left-sided slowing, theta-predominant; 2.1 SD above…"*). The `(low-confidence)` hedge exists **only in the internal provenance table**, never in the sentence a clinician reads.

### 4.8 Burst-suppression exclusion does not exist — **NOT-IMPLEMENTED**

**SAP §3.2:117-119** (restated for panels at :167-170): exclude recordings *predominantly* burst-suppression / electrocerebral inactivity — *"their low-frequency power is not 'slowing' in the intended sense."*

`grep -i "burst|suppress|isoelectric|electrocerebral"` across all Python → **no hits.** `features/artifact.py` rejects *flat segments* (a per-segment flag), which is not the recording-level routing §3.2 mandates. A record that is 50% burst clears the 20%-usable gate and enters the pipeline with its burst delta read as slowing — **precisely the failure the rule exists to prevent**, and plausibly a contributor to the artifact-inflated AUROC of §1.

### 4.9 The gate is uncalibrated, and is commented as if it were — **NOT-IMPLEMENTED**

**SAP §4.7:277-281:** *"fit a calibration map (Platt / isotonic) … **This is required before any operating-point or detection-AUROC claim** uses the gate probability as a score."*

No calibration of `p_slowing` exists anywhere (`92` fits a Platt map, but against the *legacy recording-level* `gate_probs`, not the per-segment gate). There is no `p_slowing_calibrated` column, and no schema slot for one. Meanwhile `scripts/31_segment_master_worker.py:162` annotates the raw softmax `# calibrated slowing probability` — directly contradicting the SAP.

AUROC is rank-invariant and survives monotone miscalibration, so the *AUROCs* are fine. **Operating points, thresholds, sensitivities at a cutoff, and any "P(slowing)=0.83"-style statement are not.**

### 4.10 §7.1's operating-point guarantee is never computed — **NOT-IMPLEMENTED**

**SAP §7.1:373-374:** operating points chosen so focal and generalized **FPR < 1% on clean-normals** (τ_gen ≈ 0.40, τ_foc ≈ 0.50).

`scripts/112_operating_points.py` sweeps τ and reports % gated, case-1, case-2b, and gate sensitivity — but has **no false-positive-rate-on-clean-normals column**. `clean_normal` is joined at `112:25-31` and then never used. `110:25` hardcodes `TAU_GEN, TAU_FOC = 0.40, 0.50` citing "scripts/112", **which does not derive them**. The SAP's stated <1% FPR guarantee is verified nowhere in the repo. Additionally, `115_case2_review_set.py` uses **τ_gen = 0.50** while `110` uses **0.40** — so the case-2 recordings sent to human reviewers were selected at a stricter gate than the shipped system's.

### 4.11 Missing electrodes are silently mean-filled — **VIOLATED (undocumented)**

`src/morgoth_slowing/io/edf.py:65,94-99` admits recordings with ≥15 of 19 channels and fills the absent ones with the **row-mean of the present channels**. Nothing records that this happened — no flag in `segment_master`, no field in the `.done` sidecar.

Mean-filling collapses a channel toward the head average, which **reduces its asymmetry**. A recording with a dropped left-temporal electrode gets artificially symmetric `pdBSI`/`Q_ASYM` and blunted left-temporal `log_DAR` — a false negative in exactly the focal-lateralization claim the paper makes. The rate is currently unmeasurable. `docs/data_dictionary.md:10` promises *"Missing = NaN, **never silently imputed**."*

### 4.12 Gate/stage windows are mapped with a one-window forward offset — **PARTIAL**

`31:126` (stage) and `31:168-171` (gate) map a segment's centre to a window by `int(c/step)`. Segment 0 (centre 7.5 s) → window 1 → `[5, 5+W)`. The centred mapping is `int((c − W/2)/step)`. `tests/test_segment_master.py:71` **asserts the offset** and calls it *"exact, offset-free"* — locking in the bug. Minor for sleep stage (slowly varying); **material for the gate**, where paroxysmal slowing is exactly the signal a 5-second shift corrupts.

---

## 5. Interpretation of the findings so far

### What I would believe as a reviewer

1. **The inter-rater ceiling.** 18 electroencephalographers, 100 EEGs: focal slowing Fleiss **κ = 0.373**, generalized **κ = 0.450**; within-rater re-read **0.563 / 0.642**; band agreement conditional on both raters calling slowing **54% focal / 27% generalized**. On EEGs whose *signed clinical report* said focal non-epileptiform, only **50.8%** of the panel marked focal slowing. These are **pipeline-independent** — computed from expert labels alone — so they survive everything above untouched. That slowing is the *least reliable* judgement experts make (well below epileptiform discharges at κ 0.585/0.739) is a genuine, publishable contribution and the paper's strongest defence of the severity null.

2. **Lateralization of focal slowing.** AUROC **0.890** supervised; **0.865** from a *single signed feature* (`asym_temporal_delta`) **fit to nothing**; n = 2,769; balanced accuracy 0.811. Model-free, large-N, unsupervised in the load-bearing version, and it **grew** on the re-run while everything else shrank. **This is the best result in the paper.**

3. **The regional deviation measurement.** Ipsilateral temporal z **+0.913** vs contralateral **+0.472** (Δ +0.440; Wilcoxon p = 5e-216; n = 2,540). Within-subject, so immune to the age/severity confound. And the authors draw the honest conclusion themselves: contralateral is *also* +0.5 SD and parasagittal lateralizes about as well as temporal → **the signal is hemispheric, not lobar.** That restraint is correct; keep it.

4. **The severity null.** ρ = 0.050 (n.s.) across 168 feature × statistic × normalization × stratum combinations; best |ρ| = 0.179, fails Bonferroni, **wrong sign**. A well-powered, well-executed negative — and the ceiling data explain *why* (the adjective is attached to a κ≈0.56 judgement). Publish it as a null.

5. **The growth curves themselves.** Physiologically textbook. Relative delta, TAR and DAR fall steeply through childhood and plateau by ~20–30 y; adult wake rel-delta lands at ~0.19–0.20 (the earlier 0.5–0.6 was the band-edge bug, now fixed). Stage ordering **W 0.20 < N1 0.25 < REM 0.28 < N2 0.42 < N3 0.47** is correct, and it **reproduces in the new fleet pilot** (n=111: W 0.324 / N1 0.390 / REM 0.394 / N2 0.407 / N3 0.448) — i.e. the ordering survives the pipeline change even though the detection AUROC did not. That is reassuring about the curves specifically.

### What I would not believe on current evidence

- **Any AUROC in the abstract.** 0.848/0.875 → 0.638/0.648 (§1).
- **"Vigilance-matched norms are a method requirement."** This is one of the paper's two central methodological claims, and the re-run kills it. The routine-minus-overnight reference effect is now **+0.000 (W), +0.006 (N1), +0.031 (N3), −0.002 (REM)** — not the +0.04 to +0.15 the manuscript reports. Union ≈ routine almost exactly, contradicting *"the union reference behaved like the overnight one."* REM runs the wrong way. **As written, Figure 2's thesis is not supported.**
- **The sparse score at 0.908.** It is 0.683, and the retained features changed completely — so the "frozen coefficients" shipped to the external panel test are now the *wrong* coefficients.
- **Every model-vs-expert number** (0.900 / 0.903 / 0.909 / 0.923). The source files (`occasion_human_ceiling.md`, `moe_human_ceiling.md`, `occasion_model_vs_experts.md`, `sparse_score_external.md`) are **deleted from the working tree** and not regenerated; the model that produced them has since changed by −0.2 AUROC in-cohort.
- **"Posterior foci are data-limited."** A label-mapping bug hiding 1,319 cases (§4.4).
- **"Lateralization is band-matched."** `results/lateralization_by_band.md` shows the **opposite** of the manuscript's sentence: on theta cases the *delta* classifier (0.843) **beats** the theta classifier (0.821), and the band-routed predictor (0.876) is *worse* than delta-only-always (0.877). The file's own face-validity test fails.
- **"74% left predominance."** Current labels: left 3,448 / right 2,336 = **59.6%**. A Discussion paragraph with five citations rests on 74%.
- **Pre-registered P1 ("detection AUROC ≥ 0.80; falsified if < 0.75").** On the DESCRIBE/normative path it is now **falsified**: 0.683 generalized, 0.752 focal, best single feature 0.694. Only the **Morgoth gate** (0.866) clears 0.80 — and Morgoth is not the paper's contribution. The paper must state which arm P1 refers to.

### Three things nobody has written down, in descending order of danger

**(a) Morgoth train/test overlap is never addressed — anywhere.** Morgoth was trained on MGB/BDSP clinical EEG against report-derived labels. This cohort *is* MGB and the evaluation labels *are* report-derived. Its in-cohort 0.866–0.885 — and plausibly its 0.900/0.923 on the panel — may be substantially inflated by training-set overlap. I found **zero** discussion of this in the SAP, the manuscript, or the methods audit. **Clauses 1 and 2 of the claims table (the gate's entire licence to make the categorical call) depend on it.** Intersecting Morgoth's training manifest with the 27k cohort and the 100 panel EEGs is the **single highest-value hour of work available in this project**, and it has not been done.

**(b) The van Putten benchmark, read across files, says a 1990s ratio beats the growth-curve apparatus.** SAP §8.7's adoption rule (P8b) is symmetric and pre-registered: if any van Putten arm beats ours by ΔAUROC > 0.02, **adopt it**. The benchmark as run cannot adjudicate this — it has **three arms, not four** (vP-raw, vP-age-normed, Morgoth) and **omits the authors' own features entirely**, contra §8.7:529. Comparing across files anyway (with the caveat that these are not matched n or matched CV):

| Target | Best van Putten | Ours | Reading |
|---|---|---|---|
| **Generalized** | **DTABR, age-normed: 0.720** | S: 0.683 | **vP wins by +0.037 → P8b triggered → SAP obliges adoption** |
| Focal | r_sBSI raw: 0.733 | 0.752 | +0.019 — below threshold, a **tie** |
| Abnormal | DTABR age-normed: 0.697 | 0.694 | **tie** |

On the flagship target, **age-normed (δ+θ)/(α+β) beats the entire GAMLSS/LMS normative apparatus**, and van Putten's own Brain Symmetry Index essentially ties the authors' asymmetry features on focal. A reviewer will ask what the growth-curve machinery buys over DTABR + BSI. **On these numbers the honest answer is ~0.02 AUROC, in the wrong direction on generalized.** This must be run properly (four arms, same recordings, same nested CV, patient-clustered CIs) before submission — and if it holds, the paper's contribution should be reframed as *the normative framework + lateralization + the human ceiling*, not a new detector.

**(c) But the benchmark also contains a real, defensible, narrower win — P8a.** Age-norming improves the **between-subject power/ratio** metrics (Q_SLOWING 0.636 → 0.667; DAR 0.652 → 0.676; DTABR 0.669 → 0.697; all ≈ +0.03) and **hurts the within-subject asymmetry** metric (r_sBSI 0.686 → **0.671**, −0.015). That is coherent and worth reporting exactly as it stands: **the normative framework helps where the metric is between-subject, and does nothing where the metric is already internally controlled.** It is a smaller claim than the one currently drafted, and it is *true*.

### The N1 anomaly — resolved, and the resolution is the story

`scripts/107b_diagnose_n1_anomaly.py` found that alpha-attenuation was **negative in abnormal N1** (focal −0.34, generalized −0.20) but ~0 in normal N1 — i.e. abnormal recordings had *more* alpha in N1 than normals. Backwards for slowing. Per `claims_table.md:60-63` it was **two artifacts, both fixed**: (a) 22–32% of abnormal *wake* segments were flat/suppressed and slipping past artifact rejection — now removed; (b) alpha in sleep is confounded (disrupted sleep retains wake-like alpha; sedatives *generate* alpha), so the alpha-attenuation axis is now **wake-only**. Both fixes are well-motivated and I would defend both.

**But the consequence nobody has connected: fix (a) is almost certainly what destroyed the detection headline.** The anomaly was resolved by removing the artifact that was doing much of the detecting. That is the most important thing the re-run has taught this project, and it is currently in nobody's write-up.

---

## 6. What is clean (and should be said so, in the paper)

- **The fleet worker and extractor.** Segmentation is exactly 15 s / 14 s step / 3000 / 2800 samples with no off-by-one; K = 6,171 at the 24 h cap matches the SAP's "~6,170". The `MAX_ANALYZE_HOURS = 24` cap is enforced in **three** independent places and grep finds **zero** `600`-second truncation constants anywhere in live code. Flag-don't-strip is correct and test-guarded. θ = 4–8 Hz is confirmed everywhere.
- **The van Putten module** (`features/vanputten.py`). `q_slowing` = P[2–8]/P[2–25]; `r_sbsi` is correctly **power-based, hemisphere-mean per frequency bin, 0.5–25 Hz** exactly as §8.7 demands; `pdbsi` is correctly labelled as the authors' own extension. Hand-checked in `tests/test_vanputten.py`. *(The module is right; `scripts/47` ignores it and recomputes BSI the wrong way — as a per-pair mean, the definition §8.7:510-511 explicitly corrects. Rebuild 47 on the module.)*
- **The `segment_master` schema** matches §5.1 column-for-column, and `segment_summary` / `recording_meta` match §5.2.
- **DESCRIBE's governance**, band clause aside, is genuinely well-disciplined: no severity adjective, no ACNS frequency word, no peak-SD (uses the median), focal-vs-generalized taken *only* from the gate, an abstain path, and every clause tagged with its claims-table row. `phrase.py` carries a correct RETIRED banner.
- **`z` itself is genuinely unsupervised** (`107:100-119`) — the kernel μ/σ are estimated on `clean_normal` rows only. The circularity problem is in `S`, not `z`, which means **the readers-miss claim is rescuable** by rebuilding it on `z`.
- **The code-freeze discipline.** `git tag run-v6` sits exactly on HEAD with zero drift. AWS keys are gitignored and were never committed.
- **`docs/claims_table.md` is better science than the manuscript.** It already encodes the re-run's numbers and already marks severity, band, frequency-words and focal-vs-gen-from-our-features as FORBIDDEN. **The fastest route to a defensible paper is to rewrite the manuscript from the claims table, not to patch the manuscript.**

---

## 7. Prioritized actions

**Before anything else**
1. **Explain the 0.848 → 0.638 collapse** by ablation (flat-segment rejection / band edge / relabel / expansion). This determines what the paper *is*. Do not submit, and do not rewrite, until it is attributed.
2. **Rule out Morgoth train/test overlap** against the 27k cohort and the 100 panel EEGs. One hour of work; it decides whether the gate's numbers are real.

**Then, to make the paper SAP-compliant**
3. Rebuild the readers-miss claim on **`z` alone**, or learn `w` without report labels, or retract it. Fix the `z`/`S` naming collision in the SAP and claims table first.
4. Either route the deviation field through `gamlss_fit.R`, or **stop calling it GAMLSS** in the manuscript, data dictionary, and SAP.
5. Add **k-fold cross-fitting** to `107` (copy the pattern already working in `103:216`).
6. **Finish the fleet run and repoint** `84/85/86/89/96/47/103/107/108/112` to `segment_master` via `io/canonical.py`. Fix `canonical.to_regions` to aggregate linear powers and re-derive ratios (per `recording.py`'s own docstring), and add a test asserting the two paths agree.
7. **Promote `eeg_id` end-to-end**; make `clean_pair` mandatory rather than an env var; apply `excluded_bdsp_ids` in `84/85/86/89/96/47/112`.
8. **Rebuild `scripts/47` on `features/vanputten.py`** with all four arms, identical recordings/stages, patient-clustered bootstrap CIs, no `max(a, 1−a)` auto-orientation, and an explicit **"adopted"** column adjudicating P8b.
9. Implement **BH-FDR**; re-frame `89` as exploratory.
10. Fix the **`posterior` label mapping** and recompute region macro-F1 — it is currently both wrong and unfairly pessimistic.
11. Fix the **abstain-threshold stage mismatch** (`110:62` vs `110:128`) — two lines, direct safety consequence.
12. Implement the **§3.2 burst-suppression exclusion**; record **channel fill** in the `.done` sidecar and gate on it; **calibrate the gate** (Platt/isotonic, held-out) before any operating-point claim; assert `fs == 200` in the worker.

**Housekeeping that a reviewer will notice**
13. Reconcile the **cohort N**: the SAP says ≈20,900 normal / ≈5,600 abnormal; the frozen v6 manifest is **10,276 / 13,622** — inverted, and matching no table in the repo. `docs/DATA_INVENTORY.md:54` is the source of the error and still advertises the banned legacy tables as "Canonical tables (use these)."
14. The **1,918 `replacement` rows** in v6 have `same_date_ambiguous` = null and are therefore admitted by **zero** clean-label analyses; effective N is **21,553**, not 27,524 — while `report_manifest_v6.meta.json` certifies `"replacements_analysis_ready": true`. Fix the rows or fix the freeze record.
15. **Panel EEGs have `age` = NULL** (all 1,861). The norms are age-conditioned by construction, so `z` cannot be computed for any panel EEG — this blocks the human-ceiling comparison at its foundation until age is backfilled from the EDF headers.
16. `scripts/60_build_unified_labels.py` **cannot be executed**: all three of its inputs are missing from the repo (`data/reports_raw/...csv`, `scripts/61_build_gen_labeling_set.py`, `models/gen_classifier.joblib`). The `GEN_SLOW_TEXT` regex defining `has_gen_slow` for 11,245 recordings **exists nowhere**. The label layer is currently unauditable and unreproducible.
17. Add **negation handling** to the report parser — `"no focal slowing"` currently sets `has_focal_slow=1` (81 such reports identified). This is the SAP's own stated counterexample (§3.5 PITFALL 2).
18. Three scripts (`86`, `95`, `95b`) hardcode a **dead scratchpad path from another machine** (`/private/tmp/claude-501/-Users-mwestover-...`) and cannot run.

---

## 8. A closing note on framing

The instinct that produced the SAP — name the pitfalls, freeze the manifest, forbid the claims you cannot support — is exactly right, and it is why this audit could be performed at all. Most projects cannot be audited this precisely because they never wrote down what they intended to do. The gap here is not between the SAP and good practice; it is between the SAP and the code, and it is almost entirely a *sequencing* gap: the canonical pipeline was built to spec, and then the analysis layer was never migrated onto it.

The scientific position is also better than the numbers first suggest. Three of the paper's results are strong, defensible, and largely re-run-proof: **the human ceiling** (slowing is the least reliable judgement experts make), **lateralization** (0.89, and 0.865 from a single unsupervised feature), and **the severity null**. What is fragile is the *detection* story — and the reason it is fragile may itself be the most interesting finding the project has produced. If the ablation confirms that ~0.2 AUROC of the old detection signal was suppression artifact, then the paper's real contribution is not a better slowing detector. It is: **a normative framework that measures what it claims to measure, a lateralizer that works, an honest human ceiling that shows the reference standard is weak — and a demonstration that the field's existing detection numbers are inflated by artifact.**

That is a better paper. It is also the one the data currently support.
