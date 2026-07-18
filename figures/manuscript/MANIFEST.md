# Manuscript figures — assembled set

Gathered by `scripts/assemble_manuscript_figures.py` from the producing directories; each is a copy of the current canonical figure. Regenerate the sources via the `results` reproduce tier, then re-run this.

| manuscript figure | source | producing script |
|---|---|---|
| `Figure1a_growth_curves.png` | `figures/growth_v2/keystone_growth_grid.png` | `scripts/76_keystone_growth_grid.py` |
| `Figure1b_deviation_field.png` | `figures/story/s2_segment_deviation.png` | `scripts/44_segment_deviation_summary.py` |
| `Figure1c_topoplot_rel_delta.png` | `figures/growth_v2/topo_rel_delta_by_age_stage.png` | `scripts/77_topoplots_by_age.py` |
| `Figure1c_topoplot_TAR.png` | `figures/growth_v2/topo_TAR_by_age_stage.png` | `scripts/77_topoplots_by_age.py` |
| `Figure1d_curvebank_rel_delta.png` | `figures/stage_curves/rel_delta__whole_head.png` | `scripts/111_curve_bank_v6.py` |
| `Figure1d_curvebank_TAR.png` | `figures/stage_curves/TAR__whole_head.png` | `scripts/111_curve_bank_v6.py` |
| `Figure1d_curvebank_DAR.png` | `figures/stage_curves/DAR__whole_head.png` | `scripts/111_curve_bank_v6.py` |
| `Figure2a_detection_generalized.png` | `figures/story/s0d_single_occasion_generalized.png` | `scripts/54_single_model_train_eval.py` |
| `Figure2a_detection_focal.png` | `figures/story/s0e_occasion_focal.png` | `scripts/55_recording_model.py` |
| `Figure2b_localized_focal.png` | `figures/story/s0_occasion_ours_v4_focal.png` | `scripts/49_occasion_allstage_localized.py` |
| `Figure3_vanputten_benchmark.png` | `results/figs/vanputten_comparison.png` | `scripts/recompute_vanputten_fullcov.py` |
| `Figure4_D1_type_amount.png` | `figures/story/s4_d1.png` | `scripts/57_description_panels.py` |
| `Figure4_D2_laterality_region.png` | `figures/story/s4_d2.png` | `scripts/57_description_panels.py` |
| `Figure4_D3_anteroposterior.png` | `figures/story/s4_d3.png` | `scripts/57_description_panels.py` |
| `Figure4_D4_persistence.png` | `figures/story/s4_d4.png` | `scripts/57_description_panels.py` |
| `Figure4_D5_by_sleep_stage.png` | `figures/story/s4_d5.png` | `scripts/57_description_panels.py` |
| `Figure4_D6_generated_words.png` | `figures/story/s4_d6.png` | `scripts/58_description_words.py` |
| `Figure5_sleep_underreporting.png` | `figures/growth_v2/v4a_wake_sleep.png` | `scripts/95_v4a_wake_sleep.py` |
| `Figure4_example_eeg_reports.png` | `figures/story/s4_examples_eeg_panel.png` | `scripts/63_example_eeg_traces.py` |
| `FigureS_example_reports_text.png` | `figures/story/s4_examples_panel.png` | `scripts/62_example_reports_panel.py` |
| `Figure3_sandor_external.png` | `figures/story/sandor100_slowing.png` | `scripts/sandor100_external_validation.py` |
| `FigureS1_severity_null.png` | *(missing: figures/growth_v2/severity_recalibrated.png)* | `scripts/109_severity_null_v6.py` |
