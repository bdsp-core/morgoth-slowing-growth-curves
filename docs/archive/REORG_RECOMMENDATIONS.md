# Repository reorganization recommendations — pre-clean-room-run cleanup

**Author:** Claude Code (automated review, commissioned by MBW)
**Date:** 2026-07-11
**Status:** ⚠️ **RECOMMENDATION ONLY — nothing in the repo was moved, deleted, or edited to produce this document.** Every `git mv` / `git rm` below is a *proposal* for a human to review and run (or not). Import-safety of the proposed moves was verified statically (see Appendix B); the destructive commands are grouped so you can accept them tier by tier.

**Reviewer's job:** decide which tiers/commands to act on. Tiers 1–5 are pure organization (the ask). Tier 6 lists plan-vs-code *gaps* that are not "cleanup" but block the plan's own §12 freeze gate — surfaced here so they aren't a surprise, not for this cleanup pass.

**Yardstick:** [docs/analysis_plan.md](docs/analysis_plan.md) v1.0 (the SAP) + its five companion docs. Canonical facts used to judge "stale": theta = **4–8 Hz**; coverage = **up to first 24 h** (never "first 600 s"); norms **stage-conditioned** & **sex-pooled**; recording key = **`eeg_id`** (not patient-level `bdsp_id`); **zero reuse** of prior derived tables; artifact segments **flagged, not stripped**; severity adjectives / ACNS frequency words / band-from-our-features are **FORBIDDEN** output.

---

## 0. Executive summary

The **governance layer is in excellent shape and current**: `analysis_plan.md` + `DATA_INVENTORY.md`, `data_dictionary.md`, `run_manifest_schema.md`, `claims_table.md`, `description_architecture.md` are mutually consistent and the canonical extractor (`src/morgoth_slowing/features/extract.py`) already encodes the corrected constants (theta 4–8, `FLAT_STD_UV=0.5`). Do not touch these.

**The problem is volume of *legacy* material sitting alongside the current work.** The repo still contains the entire pre-clean-room project — the old `bdsp_id`-keyed, first-600 s, reuse-based pipeline — as live-looking files. Concrete signal: **96 of 125 scripts still key on `bdsp_id`; only 3 mention `eeg_id`.** For a run whose premise is "one clean key, zero reuse," this is the "outdated code/docs in the way."

Rough scale of the cleanup:

| Area | Total tracked | Current / keep | Legacy / archive candidates |
|---|---|---|---|
| `scripts/` | 125 | ~40 (1 fleet + 7 pre-fleet + ~30 analysis) | ~80 |
| `docs/` | 46 | 6 governance + ~12 reference | ~13 superseded + ~9 historical |
| `src/` modules | 30 | ~18 (5 fleet-path + analysis) | 5 dead stubs + 5 legacy loaders |
| root `.md` | 5 | 1 (README, needs rewrite) | 3 superseded plans |

**One structural caveat found during verification (see Tier 3):** the current pipeline reaches back into legacy scripts by hard file path (`importlib`). The fleet worker `30` imports the *pilot* `26`; the label builder `20` imports `18`. So archiving is **not** a pure bulk move — a handful of legacy scripts are load-bearing until their reused logic is lifted into `src/`.

---

## 1. TIER 1 — Docs that actively contradict the plan (highest risk)

These read as authoritative live specs but assert superseded facts. An engineer or agent implementing from them would build the *wrong* thing. **Recommend:** move to `docs/archive/` OR prepend a `> ⚠ SUPERSEDED by analysis_plan.md — historical only` banner. Do not leave them looking current.

| Doc | The wrong thing it says |
|---|---|
| [docs/feature_spec.md](docs/feature_spec.md) | theta = `P[4–7]`; a quantitative severity ladder ("2.0–3.0 mild, 3.0–4.5 moderate…"). Both now wrong (theta 4–8; severity FORBIDDEN). Self-describes as "source of truth for `src/`." |
| [docs/report_architecture.md](docs/report_architecture.md) | Report axes include severity adjectives + ACNS frequency words — both FORBIDDEN in `claims_table.md`. Superseded by `description_architecture.md`. |
| [docs/artifact_rejection_plan.md](docs/artifact_rejection_plan.md) | Segments failing checks are **removed** — the silent-stripping behavior PITFALL 4 exists to prevent (plan: *flag, don't strip*). |
| [docs/repro_data.md](docs/repro_data.md) | Reproduce analyses by **rebuilding from committed derived tables** (`reanalyze.sh`) — the reuse pattern the zero-reuse principle forbids. |
| [docs/figure5_pipeline_schematic_brief.md](docs/figure5_pipeline_schematic_brief.md) | Sample sentence embeds **four FORBIDDEN clauses** (frequency word, severity adjective, band, peak-SD). If Fig 1/5 is built from this brief, the paper ships forbidden language. Needs a claims-table-legal rewrite before use. |
| [docs/manuscript_draft.md](docs/manuscript_draft.md) | Self-flagged "major revision in progress" but internally inconsistent: N = both 12,379 and 27,012; description numbers rest on first-600 s data; §5 still says norms are **sex-specific**; withdrawn band-0.74 survives in the conclusion. Keep, but every number needs the clean-room refresh before it is trustable. |

**Also:** `extract.py:34` (canonical code) points readers to `docs/feature_extraction.md`, which is itself a superseded `_py`-migration doc → repoint that comment to `data_dictionary.md`.

Lower-severity staleness (banner, not urgent): `bdsp_io_update_notice.md` ("sex-specific"), `sleep_staging.md` / `aws_cloud_plan.md` (name `SLEEPPSG.pth` as an acceptable stager; SAP pins `ss_hm_1.pth`), `morgoth_gate_outputs.md` (per-recording cohort-only gate vs the SAP's per-segment all-cohort requirement), `methods_audit.md` (carries a stale "7–8 Hz gap deliberate" leftover contradicting its own θ 4–8 headline).

---

## 2. TIER 2 — Root-level clutter

| Item | Issue | Action |
|---|---|---|
| [PLAN.md](PLAN.md) | Pre-clean-room roadmap (Phase-0, θ 4–7, "BLOCKER: staging is Other") | archive |
| [EXECUTION_PLAN.md](EXECUTION_PLAN.md) | "v1 stage-agnostic" execution plan | archive |
| [AUTONOMOUS_STATUS.md](AUTONOMOUS_STATUS.md) | Cycle-1→22 autonomous-loop status log | archive |
| [README.md](README.md) | Front door is **stale**: "Start here → PLAN.md", old n=12,379 Table 1, stage-agnostic pipeline | **rewrite** to point at `analysis_plan.md` and reflect current design (highest-value single edit) |
| `rel_theta` | Tracked **0-byte stray file** at root, committed by accident (`92e5008`, a shell-redirect artifact) | `git rm` |
| Working tree | `20`, `109` modified; `121` untracked; two `results/*_progress.txt` scratch files | commit or discard — you cannot `git tag run-v<N>` a dirty tree (build-order step 2) |

---

## 3. TIER 3 — `scripts/`: the main event (~80 legacy vs ~40 that matter)

### 3.1 The keep-set (~40 scripts)

- **Fleet path (1):** `30_ingest_worker.py` (rest of the fleet lives in `src/`).
- **Pre-fleet builders (7):** `20`, `60`, `88`, `120`, `121`, `122`, `123`.
- **Current analysis (~30):** `gamlss_fit.R`; deviation/descriptors `102, 106, 107, 108`; sentence/gating `110, 111, 112, 113`; band `109` (fold in `109b`); detection `96`, van Putten `47`; sparse-score/Fig4 `103, 104, 105`; Table 1 `85`; human-ceiling/IRR/PhaseA/blinded `90, 91, 92, 93, 94, 97, 98`; V4a `95, 95b`; case review `115, 116`; repro harness `100, 101`.
- **Kept as the negative result of record:** `86, 89` (severity is null / FORBIDDEN — keep to reproduce the null, not as a live descriptor).

> **Reality check — "keep" ≠ "ready."** Every current-analysis script still reads legacy tables (`segment_features` first-600 s, `bdsp_id`-keyed `segment_stages`). `107` and `108` (Jul 10, core to §7) are prototypes on the *old* data. Each C-script needs **repointing to `segment_master` / `deviation_field` on the `eeg_id` key** — that is genuine migration work, not archiving.

### 3.2 ⚠ Coupling that blocks a naive bulk archive (verified — Appendix B)

Kept scripts reach into legacy scripts by hard file path via `importlib.spec_from_file_location`:

| Kept script | hard-imports | If you archive the target… |
|---|---|---|
| `30_ingest_worker.py` (**fleet**) | `26_slowing_ingest_pilot.py` | **fleet worker breaks** |
| `20_extract_report_labels.py` (**pre-fleet builder**) | `18_report_agreement.py` | **label builder breaks** |
| `101_verify_figures_regenerate.py` (repro) | subprocess-runs `76`, `84` (+ kept `86`, `95`) | figure-regen harness breaks for those figures |
| `102_region_z_boxplots.py` | *comment only* references `42` | safe — only a stale doc reference in a comment |

**Consequence:** `18` and `26` are **load-bearing legacy** — do **not** archive them until their reused functions are lifted into `src/morgoth_slowing/` (this is exactly the §12.1 "inventory & separate the fleet code" task; a fleet worker importing a script named *pilot* is the smell). `76` and `84` are archivable only together with a rewrite of the `101` repro harness. `42` is safe to archive (optionally clean the comment in `102`).

### 3.3 Number collisions & consolidation

- `06_discrimination.py` + `06_make_growth_curves.py` — genuine prefix collision (both legacy).
- `95` / `95b`, `107` / `107b`, `109` / `109b` — sibling pairs. `107b` is a throwaway diagnostic; `109b` should fold into `109`. Consolidate before the run.
- Numbering gaps (08, 25, 29, 31, 45, 57–59, 64, 66, 81, 114, 117–119) are *skipped numbers* — `git log --diff-filter=D` confirms no numbered script was ever deleted. Old docs reference a `scripts/qc_checks.py` that never existed.

### 3.4 The legacy set (archive candidates — full list in §7)

Old Phase-0→E pipeline (`01`–`11`); old eval/validation (`12, 14–19, 21, 22, 24, 32–35, 38, 46, 48–50`); old localization/lateralization (`36, 37, 39–44`); H5 prototypes (`27, 28`); old label injection (`52, 53, 56, 61–63`); the reuse/uniform/union builders that build the forbidden legacy tables (`51, 55, 65, 67–71, 75, 77–80, 82, 83`, + `76, 84` per the caveat above); settled sex one-offs (`72–74`, `sex_auc.R`, `sex_sensitivity.R`); superseded utils/dashboards (`13, 23, 54`, `make_table1.py`, `refresh_dashboard.py`, `build_burndown.py`, `build_analysis_dashboard.py`, `fleet_progress.py`, `build_cohort_metadata.py`, `combine_expansion.py`); shell (`cloud_pilot_setup.sh`, `overnight_rebuild.sh`, `overnight_rebuild2.sh`). **Excluded from archive (load-bearing): `18`, `26`.**

> A few archived scripts are cited *historically* in `DATA_INVENTORY.md` (`13, 51, 65`) and `methods_audit.md` (`74, 78, 82`) as the provenance of established findings — archive the code (don't `rm`) so the citations still resolve.

---

## 4. TIER 4 — `src/` dead code + config drift

### 4.1 Dead stubs — safe to delete (verified: imported by nothing, Appendix B)

`features/spectra.py`, `features/regions.py`, `norms/reference_model.py`, `norms/zscore.py`, `io/s3.py` — all `NotImplementedError` or orphan. The first three are **duplicate-module pairs** of live code (`spectra↔extract`, `regions↔recording`, `reference_model↔norms/growth`) — the exact "dead duplicate on the fleet path" the plan warns about via retired `bandpower.py`.

### 4.2 Legacy loaders — leave in place, document as legacy

`io/segments.py`, `io/raw.py` (`.mat`-clip consumers), `io/h5_convert.py`, `io/h5_int16.py`, `features/morphology.py`. **No kept script imports them** (Appendix B), but archived scripts do — moving them out of the package would break the archived code's imports. Cleanest is to leave them and note them legacy, or relocate to a `src/morgoth_slowing/legacy/` subpackage *after* the script archive.

### 4.3 Fleet-path modules the plan §12.1 list omits

The worker actually imports `features/extract.py`, `features/recording.py`, `features/artifact.py`, `io/staging.py`, `io/edf.py`. Plan §12.1 names only the first, third, and the stager/gate — **add `recording.py` and `io/edf.py`** to the inventoried fleet-module list. Minor stale doc-strings: `io/staging.py:5` still says "spanning the same 600 s."

### 4.4 config/ drift (neither file is read by the fleet path — montage/regions are hardcoded in `recording.py`)

- [config/channels_regions.yaml](config/channels_regions.yaml): lists **5 regions, omits `whole_head`** (plan §4.6 + `recording.py` say 6); `homologous_pairs` has 2 vs `recording.py`'s 8.
- [config/config.example.yaml](config/config.example.yaml): still says features are "PRECOMPUTED, we consume them directly" (opposite of clean-room re-featurize) and defines forbidden `severity_words`. → update or delete.

### 4.5 references/ gap

[references/README.md](references/README.md) is excellent for the Q_*/BSI family but **missing definitions + a `references.bib` entry for DAR/ADR/DTABR/SEF95** (plan §8.7 cites "Finnigan & van Putten 2013," absent). Since §8.7 says definitions come from `references/`, close this before building the S7 benchmark.

---

## 5. TIER 5 — Outputs, data & git hygiene

- **`.git` is 511 MB.** ~70 MB is **legacy derived parquets force-committed past `.gitignore`** (`data/derived/recording_features.parquet` 33 MB, `stage_recording_features.parquet` 25 MB, etc. — `data/*` and `*.parquet` are gitignored, so these were `git add -f`'d). They are the old `bdsp_id`-keyed tables the plan retains "for historical reference, never as input." **Decision needed** (see §8): keep tracked (accept bloat) vs `git rm --cached` + push to S3. A true history shrink (BFG/filter-repo) rewrites history on the shared `bdsp-core` remote — separate, coordinated decision.
- **`fleet/`**: multiple overlapping manifests (`manifest.jsonl`, `manifest_cohort*.jsonl`, four `make_manifest*.py`) + ad-hoc `scale_*` / `rebuild_fix` / `final_rebuild` scripts from prior partial runs. The clean-room run uses one `run_manifest_v<N>.csv`; multiple committed manifests re-introduce the "which data?" pitfall. → prune to one manifest builder + one launch path.
- **`results/` (56 md + csv/png/html) and `figures/` (78 PNG)**: legacy pipeline outputs; the fresh run regenerates Figures 1–9 / Tables 1–6. `results/archive_exploratory/` already exists — extend that discipline so "which figure is current?" stays unambiguous.
- **`notebooks/` (5, all 2026-07-02) and `metadata/cohort_metadata.csv`**: old `bdsp_id`-keyed Table-1/curve path, referenced by no current doc → legacy.
- **`requirements.txt`**: fully **unpinned** and missing the deep-learning deps (`torch`, `timm`) the gate + stager need; lists `pygam` though the norms use GAMLSS (R). Plan §8.6 wants a pinned environment (`timm==0.9.16`, the `np.trapz→trapezoid` shim). → pin + complete before freeze.

---

## 6. TIER 6 — Plan-vs-code GAPS (not cleanup; they block the §12 freeze gate)

Surfaced because §12 makes tests + review + tag a *hard gate* before the fleet runs. Not part of this reorg, but do not let them be a surprise:

1. **24 h cap not implemented.** Plan §4.2/4.3 mandate `MAX_ANALYZE_HOURS = 24`; no such constant exists. The worker's only length control *skips* recordings > 3 GB (`EXPANSION_MAX_GB`) rather than truncating to 24 h. (Verified: `grep` finds nothing.)
2. **van Putten metrics not implemented.** §4.5 lists Q_SLOWING/Q_APG/Q_ASYM/r-sBSI/DTABR as computed "in the same pass"; none exist in `src/`; `47` is a scaffold. (Verified.)
3. **Test coverage near-zero vs §12.3/12.4.** `tests/test_smoke.py` exercises 5 modules, 4 of them *off* the fleet path. Absent: band-power-vs-known-integral, `usable_mask` on flat/high-amp fixtures, segment-index + 24 h-cap, van Putten-vs-hand-value, the stage-grid-alignment regression, and the golden-recording end-to-end diff.

---

## 7. Full 125-item script categorization

**Bucket:** A = fleet-path · B = pre-fleet builder · C = current analysis (repoint to `segment_master`) · D = legacy/archive. **Dep** = hard `importlib` dependency direction.

| Script | Bucket | Purpose | Note |
|---|---|---|---|
| 01_pull_data.py | D | Phase-0 S3 inventory/sync | |
| 02_build_control_cohort.py | D | Phase-1 control selection | |
| 03_compute_features.py | D | old region features | |
| 04_fit_reference_models.py | D | old growth curves | |
| 05_score_patients.py | D | old burden/z scoring | |
| 06_discrimination.py | D | old feature discrimination | #06 collision |
| 06_make_growth_curves.py | D | old curve plots | #06 collision |
| 07_pull_sex_omop.py | D | pull sex from OMOP | |
| 09_map_stages.py | D | old stage-CSV→segment map | |
| 10_stage_curves.py | D | old stage growth curves | |
| 11_descriptive_scoring.py | D | old prevalence/persistence | |
| 12_validate_extractor.py | D | one-time extractor validation | |
| 13_recompute_features.py | D | old full recompute | cited in DATA_INVENTORY (hist) |
| 14_aggregate_gate.py | D | old gate aggregation | |
| 15_feature_selection.py | D | old feature selection | |
| 16_gated_report.py | D | old gated-report prototype | |
| 17_lr_vs_morgoth.py | D | LR-vs-Morgoth agreement | |
| **18_report_agreement.py** | D→**RETAIN** | old report agreement | **imported by 20 (keep) — do not archive yet** |
| 19_report_validation.py | D | old report validation | |
| **20_extract_report_labels.py** | **B** | report→labels + v2 laterality | plan §3.5/3.7; imports 18 |
| 21_regional_stage_curves.py | D | old region×stage curves | |
| 22_roc_prc.py | D | old ROC/PRC | |
| 23_expansion_cohort.py | D | old expansion selection | |
| 24_morphology_features.py | D | old P1 morphology | |
| **26_slowing_ingest_pilot.py** | D→**RETAIN** | ingest pilot | **imported by 30 fleet worker — do not archive yet** |
| 27_h5_cleanup_pilot.py | D | EDF→H5 pilot | |
| 28_h5_int16_prototype.py | D | int16 H5 prototype | |
| **30_ingest_worker.py** | **A** | fleet ingest worker | plan §12/§13; imports 26 |
| 32_gate_validation.py | D | gate validation (expansion) | |
| 33_age_auroc.py | D | age AUROC | |
| 34_age_auroc_by_stage.py | D | age×stage AUROC | |
| 35_region_eval.py | D | old location eval | imports 18 (both archived) |
| 36_stage_original_abnormals.py | D | one-off stage abnormals | |
| 37_region_predictor.py | D | old region/side localizer | |
| 38_stage_stratified_auroc.py | D | old stage AUROC | |
| 39_region_supervised.py | D | old supervised region | |
| 40_lateralization_gated.py | D | old lateralization | |
| 41_lateralization_by_band.py | D | old band lateralization | |
| 42_region_gated.py | D | old gated region | referenced only in 102 comment (safe) |
| 43_flip_augment_lateralizer.py | D | flip-augmented lateralizer | |
| 44_lateralizer_band_conditioned.py | D | band-conditioned lateralizer | |
| 46_region_detection.py | D | old per-region detection | imports 42 (both archived) |
| **47_vanputten_comparison.py** | **C** | van Putten S7 benchmark scaffold | plan §8.7; rebuild vs master |
| 48_bsi_growth.py | D | old BSI growth | |
| 49_extra_evals.py | D | misc old evals | |
| 50_severity_prevalence.py | D | old severity/prevalence | |
| 51_expansion_to_derived.py | D | rebuild old derived tables | cited DATA_INVENTORY (hist) |
| 52_canonical_labels.py | D | old canonical labels | |
| 53_inject_clean_labels.py | D | inject labels into old tables | |
| 54_stage_pathology.py | D | old per-stage phys/path | |
| 55_build_cohort_stage_table.py | D | merge abnormal stages | cited DATA_INVENTORY (hist) |
| 56_build_report_labeler.py | D | HTML labeling tool | |
| **60_build_unified_labels.py** | **B** | unified label table | plan §3.5/3.7 |
| 61_build_gen_labeling_set.py | D | gen phys/path labeling set | |
| 62_train_gen_classifier.py | D | distill gen labels→classifier | |
| 63_build_label_review.py | D | HTML gen-label review | |
| 65_merge_n3_expansion.py | D | merge N3 expansion | cited DATA_INVENTORY (hist) |
| 67_central_stage_growth.py | D | central stage growth | |
| 68_topoplots_by_age.py | D | age topoplots | |
| 69_cohort_mat_to_uniform.py | D | .mat→uniform | |
| 70_build_uniform_reference.py | D | old uniform reference | |
| 71_omop_fractional_age.py | D | fractional age→uniform | |
| 72_sex_sensitivity.py | D | sex sensitivity (settled P2) | |
| 73_sex_detection_auc.py | D | sex detection AUC | |
| 74_sex_ablation_discrim.py | D | sex ablation | cited methods_audit (hist) |
| 75_source_harmonization.py | D | cohort/expansion harmonization | |
| 76_keystone_growth_grid.py | D | old keystone Fig-2 grid | subprocess-run by 101 |
| 77_harmonize_normal.py | D | harmonize normal def | |
| 78_pipeline_control.py | D | pipeline-control diagnostic | cited methods_audit (hist) |
| 79_union_normal_detection.py | D | union-normal detection | |
| 80_recompute_cohort_extractpy.py | D | old union recompute | "_extractpy" alias smell |
| 82_build_uniform_v2.py | D | old uniform-v2 union | cited methods_audit (hist) |
| 83_union_discrimination.py | D | discrimination on union | |
| 84_vigilance_matched_detection.py | D | superseded by 96 | subprocess-run by 101 |
| **85_table1_and_dose_response.py** | **C** | Table 1 + dose-response | rebuild for Table 1 |
| **86_recalibrate_severity.py** | **C** | severity recalibration | keep as null-result of record |
| 87_build_abnormal_stages.py | C→D? | stage abnormals | obviated once fleet stages all — demote when confirmed |
| **88_report_pairing_audit.py** | **B** | nearest-in-time clean_pair | plan §3.3/3.7 |
| **89_severity_axis_sweep.py** | **C** | severity-axis sweep | keep as null-result of record |
| **90_moe_human_ceiling.py** | **C** | MoE between-rater ceiling | plan §8.3 |
| **91_occasion_human_ceiling.py** | **C** | OccasionNoise ceiling | plan §8.3 |
| **92_ea_irr_and_recalibration.py** | **C** | expert-vs-algo IRR | plan §8.3 |
| **93_phaseA_occasion_scoring.py** | **C** | Phase-A OccasionNoise scoring | phaseA_prereg |
| **94_phaseA_model_vs_experts.py** | **C** | Phase-A model vs experts (Fig 8) | |
| **95_v4a_wake_sleep.py** | **C** | V4a wake→sleep (P6) | |
| **95b_v4a_spindle_check.py** | **C** | V4a spindle-verified N2 | #95 sibling |
| **96_nested_cv_detection.py** | **C** | nested-CV detection (canonical S1) | supersedes 84 |
| **97_moe_band_vs_ours.py** | **C** | our band vs MoE panel | plan §8.3 |
| **98_build_review_set.py** | **C** | blinded head-to-head set | plan §8.3f |
| 99_exclude_multirecording_patients.py | C | multi-recording dedup sensitivity | cited methods_audit |
| **100_cache_figure_inputs.py** | **C** | cache figure inputs (repro) | imports 86, 95 (both keep) |
| **101_verify_figures_regenerate.py** | **C** | verify figures regen (repro) | subprocess-runs 76, 84, 86, 95 |
| **102_region_z_boxplots.py** | **C** | regional slowing as measurement | 42 in a comment only |
| **103_sparse_slowing_score.py** | **C** | sparse slowing score S | |
| **104_sparse_score_external.py** | **C** | sparse-score external test | imports 103 |
| **105_two_stage_figure.py** | **C** | Fig 4 gate-then-quantify | imports 103 |
| **106_focal_excess_prototype.py** | **C** | focality-as-excess prototype | imports 103 |
| **107_deviation_field.py** | **C** | deviation field + 6 descriptors | reads legacy tables — repoint |
| 107b_diagnose_n1_anomaly.py | C | N1-anomaly diagnostic | #107 sibling (throwaway) |
| **108_descriptor_validation.py** | **C** | validate 6 descriptors | reads legacy tables — repoint |
| **109_band_edges_test.py** | **C** | 7–8 Hz band-edge fix | plan §4.5; fold in 109b |
| 109b_band_index_fast.py | C | fast band-index | #109 sibling — fold into 109 |
| **110_generate_sentence.py** | **C** | claims-gated sentence generator | plan §7.2 |
| **111_stage_specific.py** | **C** | per-stage present/absent | claims/desc_arch |
| **112_operating_points.py** | **C** | per-branch operating points | desc_arch |
| **113_gated_describe.py** | **C** | gated per-branch describe | desc_arch |
| **115_case2_review_set.py** | **C** | generalized case-2 review set | desc_arch |
| **116_export_case2_clips.py** | **C** | export case-2 EEG clips | |
| **120_build_report_manifest.py** | **B** | build/freeze report manifest | plan §3.7 |
| **121_backfill_manifest.py** | **B** | backfill manifest cells | plan §3.7; imports 20 |
| **122_coverage_report.py** | **B** | coverage tables | plan §3.7 |
| **123_coverage_plots.py** | **B** | coverage plots | plan §3.7; imports 20 |
| gamlss_fit.R | C | GAMLSS/LMS norms engine | plan §6 |
| sex_auc.R | D | sex detection R test | |
| sex_sensitivity.R | D | sex-conditioning R test | |
| build_analysis_dashboard.py | D | old all-evals dashboard | |
| build_burndown.py | D | ingestion burndown HTML | monitoring |
| build_cohort_metadata.py | D | build old cohort_metadata.csv | |
| combine_expansion.py | D | combine pilot outputs | |
| fleet_progress.py | D | .done progress tracker | monitoring |
| make_table1.py | D | old Table 1 (→ 85) | |
| refresh_dashboard.py | D | live ingest dashboard | monitoring |
| cloud_pilot_setup.sh | D | one-shot GPU pilot setup | |
| overnight_rebuild.sh | D | overnight old-table rebuild | |
| overnight_rebuild2.sh | D | phase-2 overnight rebuild | |

---

## 8. Open decisions for the reviewer

1. **Archive vs delete.** Recommendation: **archive** legacy scripts/docs (`git mv` into `archive/`, history preserved) rather than `git rm`, because several are cited as finding-provenance. Pure dead stubs (§4.1) can be `git rm` (recoverable from history).
2. **Load-bearing legacy (`18`, `26`).** Lift their reused functions into `src/` and repoint `20` / `30`, *then* archive? Or leave both in `scripts/` as acknowledged shared deps for now? (Recommend the refactor — it is the §12.1 task and de-risks the freeze.)
3. **Committed derived parquets (~70 MB).** Leave tracked, or `git rm --cached` + move to S3? (A deep history shrink is a separate, coordinated call on the shared remote.)
4. **`87_build_abnormal_stages.py`.** Keep until the fleet stager is confirmed to cover abnormals, then demote to legacy?
5. **PHI reconciliation.** Plan §11 now permits committing de-identified BDSP report text (supersedes the earlier "never commit raw text" rule). Confirm the earlier-pushed report text is covered by §11 so that item can be formally closed rather than left hanging.

---

## 9. Proposed move-list (copy-paste blocks — review before running)

> Run from repo root. Each block is independent; accept the tiers you agree with. **Nothing here has been executed.** `git mv` preserves history. Verify a clean working tree first (Tier 2) so the moves are the only change in the commit.

**A. Create archive directories**
```bash
mkdir -p docs/archive scripts/archive results/archive figures/archive
```

**B. Root-level (Tier 2)**
```bash
git rm rel_theta
git mv PLAN.md EXECUTION_PLAN.md AUTONOMOUS_STATUS.md docs/archive/
# README.md: rewrite in place (do NOT archive) — see Tier 1/2
```

**C. Superseded / stale docs (Tier 1 + historical)**
```bash
git mv docs/feature_spec.md docs/report_architecture.md docs/artifact_rejection_plan.md \
       docs/repro_data.md docs/paper_outline.md docs/feature_extraction.md \
       docs/normative_deviation_plan.md docs/label_cleanup_plan.md docs/label_quality_plan.md \
       docs/localization_improvement_plan.md docs/staging_and_localization_plan.md \
       docs/coverage_expansion_plan.md docs/coverage_by_stage.md docs/archive/
# Historical/status logs (optional — keep dated record, move out of active set):
git mv docs/phase0_findings.md docs/reanalysis_status.md docs/status_2026-07-06.md \
       docs/n3_expansion_plan.md docs/table1.md docs/table1_live.md docs/archive/
# Then update docs/analysis_plan.md line 34 cross-ref if it points at any moved file,
# and repoint the extract.py:34 comment from feature_extraction.md -> data_dictionary.md.
```

**D. Dead `src/` stubs (Tier 4.1 — verified imported by nothing)**
```bash
git rm src/morgoth_slowing/features/spectra.py \
       src/morgoth_slowing/features/regions.py \
       src/morgoth_slowing/norms/reference_model.py \
       src/morgoth_slowing/norms/zscore.py \
       src/morgoth_slowing/io/s3.py
```

**E. Legacy scripts (Tier 3.4) — EXCLUDES load-bearing `18` and `26`**
```bash
git mv \
  scripts/01_pull_data.py scripts/02_build_control_cohort.py scripts/03_compute_features.py \
  scripts/04_fit_reference_models.py scripts/05_score_patients.py scripts/06_discrimination.py \
  scripts/06_make_growth_curves.py scripts/07_pull_sex_omop.py scripts/09_map_stages.py \
  scripts/10_stage_curves.py scripts/11_descriptive_scoring.py scripts/12_validate_extractor.py \
  scripts/13_recompute_features.py scripts/14_aggregate_gate.py scripts/15_feature_selection.py \
  scripts/16_gated_report.py scripts/17_lr_vs_morgoth.py scripts/19_report_validation.py \
  scripts/21_regional_stage_curves.py scripts/22_roc_prc.py scripts/23_expansion_cohort.py \
  scripts/24_morphology_features.py scripts/27_h5_cleanup_pilot.py scripts/28_h5_int16_prototype.py \
  scripts/32_gate_validation.py scripts/33_age_auroc.py scripts/34_age_auroc_by_stage.py \
  scripts/35_region_eval.py scripts/36_stage_original_abnormals.py scripts/37_region_predictor.py \
  scripts/38_stage_stratified_auroc.py scripts/39_region_supervised.py scripts/40_lateralization_gated.py \
  scripts/41_lateralization_by_band.py scripts/42_region_gated.py scripts/43_flip_augment_lateralizer.py \
  scripts/44_lateralizer_band_conditioned.py scripts/46_region_detection.py scripts/48_bsi_growth.py \
  scripts/49_extra_evals.py scripts/50_severity_prevalence.py scripts/51_expansion_to_derived.py \
  scripts/52_canonical_labels.py scripts/53_inject_clean_labels.py scripts/54_stage_pathology.py \
  scripts/55_build_cohort_stage_table.py scripts/56_build_report_labeler.py scripts/61_build_gen_labeling_set.py \
  scripts/62_train_gen_classifier.py scripts/63_build_label_review.py scripts/65_merge_n3_expansion.py \
  scripts/67_central_stage_growth.py scripts/68_topoplots_by_age.py scripts/69_cohort_mat_to_uniform.py \
  scripts/70_build_uniform_reference.py scripts/71_omop_fractional_age.py scripts/72_sex_sensitivity.py \
  scripts/73_sex_detection_auc.py scripts/74_sex_ablation_discrim.py scripts/75_source_harmonization.py \
  scripts/77_harmonize_normal.py scripts/78_pipeline_control.py scripts/79_union_normal_detection.py \
  scripts/80_recompute_cohort_extractpy.py scripts/82_build_uniform_v2.py scripts/83_union_discrimination.py \
  scripts/sex_auc.R scripts/sex_sensitivity.R scripts/build_analysis_dashboard.py \
  scripts/build_cohort_metadata.py scripts/combine_expansion.py scripts/make_table1.py \
  scripts/refresh_dashboard.py scripts/cloud_pilot_setup.sh scripts/overnight_rebuild.sh \
  scripts/overnight_rebuild2.sh \
  scripts/archive/
```

**F. Deferred until the `101` repro harness is rewritten (subprocess-invokes these)**
```bash
# git mv scripts/76_keystone_growth_grid.py scripts/84_vigilance_matched_detection.py scripts/archive/
```

**G. Blocked until refactor (Tier 3.2 — DO NOT run until 20/30 stop importing them by path)**
```bash
# git mv scripts/18_report_agreement.py scripts/26_slowing_ingest_pilot.py scripts/archive/
```

**H. Monitoring dashboards — archive only if not needed live during the new run**
```bash
# git mv scripts/build_burndown.py scripts/fleet_progress.py scripts/archive/
```

**I. Add `docs/archive/README.md`** — a short index: "Superseded pre-clean-room material, retained for provenance. Canonical is `docs/analysis_plan.md`. Nothing here is an input to the fresh run." List the moved files + the fact each supersedes.

---

## Appendix A — Governance set to KEEP untouched
`docs/analysis_plan.md`, `docs/DATA_INVENTORY.md`, `docs/data_dictionary.md`, `docs/run_manifest_schema.md`, `docs/claims_table.md`, `docs/description_architecture.md`, plus current references (`docs/legacy_growth_curves_matformat.md`, `docs/coverage_report.md`, `docs/literature_review.md`, `docs/omop-query-instructions.txt`, `docs/pull_eeg_reports.sql`, `docs/phaseA_preregistration.md`, infra `aws_*`/`source_data_cleanup_plan.md`/`morgoth_h5_loader_patch.md`/`psg_n3_calibration_feasibility.md`, roadmap `morphology_features.md`).

## Appendix B — Verification performed (this review, read-only)
- Confirmed `extract.py:35` `BANDS` theta = `(4.0, 8.0)` — canonical code is correct; stale θ 4–7 lives only in old docs.
- Confirmed **no** `MAX_ANALYZE_HOURS` / 24 h cap anywhere in `src/` or fleet-path scripts.
- Confirmed **no** van Putten metric (`Q_SLOWING`/`Q_APG`/`DTABR`/`sBSI`/`SEF95`) implemented in `src/`.
- Confirmed dead stubs (`spectra`, `regions`, `reference_model`, `zscore`, `io.s3`) have **0 importers** across `src/` + `scripts/`.
- Confirmed **no keep-bucket script** imports a legacy `src/` loader (`segments`/`raw`/`h5_convert`/`h5_int16`/`morphology`).
- Mapped cross-script `importlib` coupling: `30→26`, `20→18`, `104/105/106→103`, `100→86,95`, `121/123→20` (imports); `101→76,84,86,95` (subprocess); `102→42` (comment only).
- Confirmed `.DS_Store`, `__pycache__`, `.pyc` are correctly gitignored (not tracked); `rel_theta` and the `data/derived/*.parquet` set ARE tracked (force-added past `.gitignore`).
