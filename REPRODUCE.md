# Reproduce every figure, table, and number

Everything is driven by one script, [`scripts/reproduce_story.sh`](scripts/reproduce_story.sh), in three
tiers (pick by how much you want to rebuild):

```bash
pip install -e .                                   # or: pip install -r requirements.txt
bash scripts/reproduce_story.sh results            # FAST  — figures/tables from the derived tables
bash scripts/reproduce_story.sh features           # ~1 h  — rebuild norms/deviation/descriptors + train, then results
bash scripts/reproduce_story.sh scratch            # ~24 h — from raw EDFs on the GPU fleet, then everything
```

## Data access (before the `results`/`features` tiers)

The derived tables are git-ignored (72 GB). Pull them from the credentialed prefix (needs bdsp.io
credentialed access + a DUA — see [`DATA_SOURCE.md`](DATA_SOURCE.md)):

```bash
export AWS_PROFILE=opendata          # read profile for s3://bdsp-opendata-credentialed
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/ data/derived/
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/panels/  data/derived/   # ON-100 panel inputs
```

The small **proximal artifacts** each figure/table also needs (report manifest, result CSVs/MD, norm
grids small enough to commit) are already in the repo under `data/`, `results/`, and `figures/`.

## The contract — paper item → script → input → output

Figures are assembled into the submission set by
[`scripts/assemble_manuscript_figures.py`](scripts/assemble_manuscript_figures.py)
(→ `figures/manuscript/Figure*.png` + `.pdf`). Panel producers and their inputs:

| Paper item | Producing script(s) | Key input (derived / proximal) | Output |
|---|---|---|---|
| **Figure 1** normative model | `76_keystone_growth_grid.py`, `77_topoplots_by_age.py` | `grid_norm.json`, `segment_deviation/` | `figures/growth_v2/{keystone_growth_grid,topo_rel_delta_by_age_stage}.png` |
| **Figure 2** detection (gen + focal) | `54_single_model_train_eval.py`, `55_recording_model.py` | `single_model_segfeats.parquet` | `figures/story/{s0d_single_occasion_generalized,s0e_occasion_focal}.png` |
| **Figure 3** SAI-100 external | `sandor100_external_validation.py` | SAI-100 set + `segment_master/eeg_id=SB_*` | `figures/story/sandor100_slowing.png` |
| **Figure 4** example EEG + reports | `62_example_reports_panel.py`, `63_example_eeg_traces.py` | `description_recording.parquet`, `data/manifest/report_manifest_v6.parquet`, source EDFs (S3) | `figures/story/s4_examples_eeg_panel.png` |
| **Figure 5** description contrast | `57_description_panels.py` | `description_recording.parquet`, `description_stage.parquet` | `figures/story/{s4_d2,s4_d5}.png` |
| **Figure 6** sleep under-reporting | `fig6_sleep_naming.py` (stat: `95b_v4a_spindle_check.py`) | `description_stage.parquet`, `results/p6_sleep_underreporting.md` | `figures/growth_v2/v4a_wake_sleep.png` |
| **Figure S1** architecture | `architecture_diagram.py` | — | `figures/story/architecture.png` |
| **Figure S2** deviation field | `44_segment_deviation_summary.py` | `segment_deviation/` | `figures/story/s2_segment_deviation.png` |
| **Figure S3** curve bank | `111_curve_bank_v6.py` | `grid_norm.json` | `figures/stage_curves/*__whole_head.png` |
| **Figure S4** description panels (D1–D6) | `57_description_panels.py`, `58_description_words.py` | `description_recording.parquet` | `figures/story/s4_d{1,3,4,6}.png` |
| **Figure S5** localized focal | `49_occasion_allstage_localized.py` | `occasion_features.parquet` | `figures/story/s0_occasion_ours_v4_focal.png` |
| **Figure S6** severity null | `109_severity_null_v6.py` | `occasion_features.parquet` | `figures/growth_v2/severity_recalibrated.png` |
| **Figure S7** van Putten benchmark | `vanputten_panel_s7.py` | `occasion_features.parquet`, gate tables | `figures/figs/vanputten_panel_s7.png` |
| **Figure S8** topoplot (TAR) | `77_topoplots_by_age.py` | `segment_deviation/` | `figures/growth_v2/topo_TAR_by_age_stage.png` |
| **Table 1** cohort | `table1_sap.py` | `labels_unified.parquet`, manifest | `results/table1.md` |
| **Table S1** van Putten full-coverage | `recompute_vanputten_fullcov.py` | `occasion_features.parquet` | `results/vanputten_fullcoverage.md` |
| **Table S2** human ceiling | `recompute_human_ceiling_v6.py` | ON-100 panel votes | `results/table5_human_ceiling.md` |
| **Table S3** band (δ/θ/mixed) calibration | `band_calibration.py` | `description_recording.parquet` (`band_dtr`) | `results/story/band_calibration.md` |

## Key quoted numbers → where they come from

| Number (paper) | Script | Source artifact |
|---|---|---|
| Detection AUROC (focal 0.92 / gen 0.95) | `54`, `55` | `single_model_segfeats.parquet` → `results/story/*` |
| ON-100 experts-under-curve; human ceiling κ | `recompute_human_ceiling_v6.py` | ON-100 panel votes (`panels/`) |
| Band δ-vs-θ AUROC 0.74 (vs 0.68 deviation); κ≈0.10 | `band_calibration.py` | `description_recording.parquet` |
| Component concordance (side 56% / region 46% / band 52%) | `58_description_words.py` | `description_recording.parquet` + report labels |
| Sleep under-reporting naming rates; spindle-verified AUROC | `95b_v4a_spindle_check.py` | `description_stage.parquet` + source EDFs |
| Severity null (ρ≈0.05; 168-combination sweep) | `109_severity_null_v6.py` | `occasion_features.parquet` |

Numbers that require the **raw EEG or model training** to regenerate (not just the committed CSVs) are
produced by the `features`/`scratch` tiers and are marked in `reproduce_story.sh`; every other number
regenerates from the derived tables in the `results` tier.

## How the runner works

The runner executes numbered stages (0 canonical tables · 1 norms + deviation field · 2 panel inputs
[Morgoth] · 3 descriptors + model features · 4 figures/tables/models · 5 dashboard + manuscript figure set);
the tier just sets the starting stage (`results`→4, `features`→0, `scratch`→fleet then 0). Each step is
**skipped when its output already exists** — `FORCE=1` rebuilds regardless, `SKIP_PANEL=1` skips the
Morgoth-dependent panel step. Steps needing R (`115`, `76`) are marked `[R]`. `scratch` is a sharded,
multi-host S3 job, not a laptop run; the runner prints the fleet command and, if `segment_master/` is present
locally, continues from `features`.

## Known reproducibility note

`results/story/s0c_morgoth_free.md` (the in-domain focal/generalized trajectory in dashboard block 2b) is a
hand-authored summary of the design search, not a script-generated artifact. Everything else is produced by
the stages above.
