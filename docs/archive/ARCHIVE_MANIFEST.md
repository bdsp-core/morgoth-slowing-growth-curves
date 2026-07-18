# Archive manifest — 2026-07-18 repo cleanup

When the analysis was consolidated into the clean 3-section story (normative deviation model → detection →
description) and the manuscript revised to match, the superseded scaffolding was moved to `archive/`
subdirectories (via `git mv`, so history and recoverability are preserved). **Nothing was deleted.** This
file records what moved and the rule used, so anything can be restored with `git mv … ..`.

## Rule

**Keep** exactly what the revised manuscript (`docs/manuscript_draft.md`), the story dashboard
(`scripts/build_story_dashboard.py`), the reproduce runner (`scripts/reproduce_story.sh`), and the upstream
fleet data-build reference. **Archive** everything superseded by those — earlier design iterations, an
alternate dashboard, withdrawn analyses, and era/setup docs.

## What moved

- **`scripts/archive/`** — superseded pipeline scripts. Includes: the occasion/MoE detector iterations
  (`40`, `45`, `46`, `47_occasion_wake_persegment`, `48`, `51`, `52`) superseded by the single report-trained
  model (`53`–`55`) and localized focal (`49`); the withdrawn/cut analyses (`84` vigilance-matched detection,
  `85` dose-response table, `86`/`89` severity recalibration, `103`/`104` sparse score, `105`/`113`/`114`
  two-stage, `38` intermittency, `102` region-z boxplots, `112` gated-by-stage, `96` nested-CV, `106`
  appendix figures, `108` deviation-vs-ceiling, `ablation_auroc`); the older deviation-field builders
  (`107_deviation_field*`, `107b`) replaced by `43` + `115`; the human-ceiling variants (`90`, `91`, `93`,
  `94`) superseded by `recompute_human_ceiling_v6`; legacy adapters/shims
  (`adapter_*`, `shims/`) superseded by `fleet_analysis_adapter`; the superseded van Putten scripts
  (`47_vanputten_comparison`, `producer_vanputten_sap`) superseded by `recompute_vanputten_fullcov`; the
  alternate SAP dashboard (`build_dashboard_sap`) and run-monitors (`build_burndown`, `fleet_progress`);
  plus the pre-existing legacy `01`–`72` set. **(~139 files total, including the pre-existing legacy set.)**
- **`results/archive/` + `results/story/archive/`** — result tables not cited by the revised manuscript or
  embedded by the dashboard (superseded story iterations `s0_*`, `s0_occasion_ours_v{1,2,3}`, `s1_*`; and
  top-level analyses for cut sections: `sparse_*`, `two_stage_*`, `lateralization_*`, `region_*`,
  `severity_prevalence*`, `deviation_field`, `nested_cv_detection`, `ablation_auroc`, `table3/4`, etc.), plus
  stale HTML dashboards/labeling UIs (`analysis_dashboard.html`, `gate_run_dashboard.html`, …).
- **`figures/story/archive/` + `figures/growth_v2/archive/`** — figures not referenced by the manuscript or
  dashboard (MoE panels, occasion v1–v3 iterations, `s1_seg2eeg`, `s1a_eeg_roc_prc`; and the growth_v2 cut
  figures `dose_response`, `sparse_score*`, `two_stage_*`, `vigilance_matched_detection`,
  `severity_recalibrated`, `morgoth_intermittency`, `region_z_boxplots`, `gated_deviation_by_stage`,
  `harmonized_two_stage*`, `occasion_roc_experts`).
- **`docs/archive/`** — stale reproduce docs (`REPRODUCE_ANALYSIS.md`, `RUN_READINESS.md`, replaced by
  `docs/REPRODUCE.md` + `scripts/reproduce_story.sh`) and era/setup docs (`aws_*`, `bdsp_io_update_notice`,
  `morgoth_h5_loader_patch`, `legacy_growth_curves_matformat`, `pilot_segmaster_summary`,
  `psg_n3_calibration_feasibility`, `source_data_cleanup_plan`), plus the pre-revision manuscript
  (`manuscript_draft_pre_v6revision_2026-07-18.md`) and the pre-existing planning/status docs.

## What was kept live

Scripts: the reproduce runner + dashboard builder, the story figure/model/table producers
(`44`, `49`, `53`–`58`, `76`, `77`, `95`/`95b`, `109`, `110_kappa`, `111_curve_bank`, `recompute_*`,
`table1_sap`), and the upstream data-build (`20`, `31`–`36`, `43`, `60`, `87`, `99`, `107_rebuild`, `115`,
`120`–`130`, `label_rederive_sap`, `fleet_analysis_adapter`, `fix_ages_fractional`, `gamlss_*.R`,
`p2_sex_pooling_v6`, `p6_sleep_underreporting`, `97_moe_band_vs_ours`).
Docs: the manuscript, analysis/validation plans, data dictionary/inventory, description architecture,
methods audit, literature review, and the new `REPRODUCE.md`.
