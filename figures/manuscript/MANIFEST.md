# Manuscript figures — composited submission set

Built by `scripts/assemble_manuscript_figures.py`: multi-panel figures are composited into one file with (A)/(B) labels (as submitted); singles are passed through. Regenerate panel sources via the `results` reproduce tier, then re-run.

Printed size is what the figure measures once it is scaled to fit Clinical Neurophysiology's 190 x 240 mm box; type scale is what every point size in it is multiplied by on the page. A figure that is too tall prints narrower than the column and shrinks its own labels, so both are reported here.

| submission figure | panels | producing script(s) | printed mm | type scale | printed DPI |
|---|---|---|---|---|---|
| `Figure1_normative_model.png` | 2 (keystone_growth_grid.png, topo_rel_delta_by_age_stage.png) | `scripts/76, 77` | 156 x 240 | 1.16 | 300 |
| `Figure2_detection.png` | 2 (s0d_single_occasion_generalized.png, s0e_occasion_focal.png) | `scripts/54, 55, 66` | 190 x 190 | 1.41 | 300 |
| `Figure3_sandor_external.png` | 1 (sandor100_slowing.png) | `scripts/sandor100_external_validation` | 190 x 91 | 1.34 | 300 |
| `Figure4_example_focal.png` | 1 (s4_examples_eeg_focal.png) | `scripts/62, 63` | 167 x 240 | 1.18 | 300 |
| `Figure5_example_generalized.png` | 1 (s4_examples_eeg_generalized.png) | `scripts/62, 63` | 167 x 240 | 1.18 | 300 |
| `Figure6_description_contrast.png` | 2 (s4_d2.png, s4_d5.png) | `scripts/57` | 190 x 157 | 1.41 | 300 |
| `Figure7_sleep_underreporting.png` | 1 (v4a_wake_sleep.png) | `scripts/fig6_sleep_naming (95b stat)` | 190 x 98 | 1.34 | 300 |
| `FigureS1_architecture.png` | 1 (architecture.png) | `scripts/architecture_diagram` | 190 x 186 | 1.34 | 300 |
| `FigureS6_deviation_field.png` | 1 (s2_segment_deviation.png) | `scripts/44` | 190 x 65 | 1.34 | 300 |
| `FigureS5_curvebank.png` | 3 (rel_delta__whole_head.png, TAR__whole_head.png, DAR__whole_head.png) | `scripts/111` | 190 x 226 | 1.44 | 301 |
| `FigureS8_description_panels.png` | 4 (s4_d1.png, s4_d3.png, s4_d4.png, s4_d6.png) | `scripts/57, 58` | 159 x 240 | 1.21 | 300 |
| `FigureS7_localized_focal.png` | 1 (s0_occasion_ours_v4_focal.png) | `scripts/49` | 190 x 91 | 1.34 | 300 |
| `FigureS9_severity_null.png` | 1 (severity_recalibrated.png) | `scripts/109` | 190 x 92 | 1.34 | 300 |
| `FigureS3_vanputten.png` | 1 (vanputten_panel_s7.png) | `scripts/vanputten_panel_s7` | 190 x 102 | 1.34 | 300 |
| `FigureS4_topoplot_TAR.png` | 1 (topo_TAR_by_age_stage.png) | `scripts/77` | 190 x 110 | 1.34 | 300 |
| `FigureS2_centile_calibration.png` | 1 (s9_centile_calibration.png) | `scripts/78` | 190 x 217 | 1.34 | 300 |
