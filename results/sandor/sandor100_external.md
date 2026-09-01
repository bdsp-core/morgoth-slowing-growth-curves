# SAI-100 (SCORE-AI validation set) — external validation: LENS vs SCORE-AI vs Morgoth vs experts

Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → the report-trained LENS detectors) run UNCHANGED on 98/100 external EMU EEGs. Ground truth = expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under the LENS ROC curve.

| axis | model | AUROC [95% CI] | % experts under ROC | AP |
|---|---|---|---|---|
| focal (25+) | LENS | 0.938 [0.870, 0.985] | 79% | 0.887 |
| focal (25+) | Morgoth | 0.974 [0.923, 1.000] | 93% | 0.963 |
| focal (25+) | SCORE-AI | 0.878 [0.783, 0.955] | 29% | 0.786 |
| generalized (24+) | LENS | 0.908 [0.803, 0.980] | 50% | 0.846 |
| generalized (24+) | Morgoth | 0.951 [0.892, 0.991] | 71% | 0.889 |
| generalized (24+) | SCORE-AI | 0.930 [0.874, 0.971] | 57% | 0.784 |

## Paired AUROC differences (LENS minus comparator)

Same 4,000 recording-level resamples for both models in each row, so the interval is on the DIFFERENCE. A comparative claim is only supported where the interval excludes 0.

| axis | comparison | ΔAUROC [95% CI] | p | supported? |
|---|---|---|---|---|
| focal | LENS − SCORE-AI | +0.061 [-0.036, +0.160] | 0.228 | no (interval includes 0) |
| focal | LENS − Morgoth | -0.037 [-0.107, +0.024] | 0.241 | no (interval includes 0) |
| generalized | LENS − SCORE-AI | -0.020 [-0.122, +0.062] | 0.726 | no (interval includes 0) |
| generalized | LENS − Morgoth | -0.042 [-0.151, +0.041] | 0.402 | no (interval includes 0) |
