# SAI-100 (SCORE-AI validation set) — external validation: LENS vs SCORE-AI vs Morgoth vs experts

Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → the report-trained LENS detectors) run UNCHANGED on 100/100 external EMU EEGs. Ground truth = expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under the LENS ROC curve.

| axis | model | AUROC [95% CI] | % experts under ROC | AP |
|---|---|---|---|---|
| focal (26+) | LENS | 0.930 [0.862, 0.979] | 64% | 0.875 |
| focal (26+) | Morgoth | 0.976 [0.928, 1.000] | 93% | 0.965 |
| focal (26+) | SCORE-AI | 0.878 [0.784, 0.953] | 29% | 0.793 |
| generalized (24+) | LENS | 0.908 [0.806, 0.979] | 50% | 0.845 |
| generalized (24+) | Morgoth | 0.951 [0.897, 0.991] | 71% | 0.888 |
| generalized (24+) | SCORE-AI | 0.931 [0.878, 0.973] | 57% | 0.784 |

## Paired AUROC differences (LENS minus comparator)

Same 4,000 recording-level resamples for both models in each row, so the interval is on the DIFFERENCE. A comparative claim is only supported where the interval excludes 0.

| axis | comparison | ΔAUROC [95% CI] | p | supported? |
|---|---|---|---|---|
| focal | LENS − SCORE-AI | +0.052 [-0.049, +0.156] | 0.304 | no (interval includes 0) |
| focal | LENS − Morgoth | -0.046 [-0.116, +0.017] | 0.15 | no (interval includes 0) |
| generalized | LENS − SCORE-AI | -0.022 [-0.124, +0.061] | 0.685 | no (interval includes 0) |
| generalized | LENS − Morgoth | -0.042 [-0.157, +0.040] | 0.399 | no (interval includes 0) |
