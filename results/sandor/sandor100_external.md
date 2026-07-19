# SAI-100 (SCORE-AI validation set) — external validation: LENS vs SCORE-AI vs Morgoth vs experts

Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → the report-trained LENS detectors) run UNCHANGED on 98/100 external EMU EEGs. Ground truth = expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under the LENS ROC curve.

| axis | model | AUROC [95% CI] | % experts under ROC | AP |
|---|---|---|---|---|
| focal (25+) | LENS | 0.933 [0.864, 0.984] | 71% | 0.894 |
| focal (25+) | Morgoth | 0.974 [0.923, 1.000] | 93% | 0.963 |
| focal (25+) | SCORE-AI | 0.878 [0.783, 0.955] | 29% | 0.786 |
| generalized (24+) | LENS | 0.893 [0.784, 0.978] | 50% | 0.846 |
| generalized (24+) | Morgoth | 0.951 [0.892, 0.991] | 71% | 0.889 |
| generalized (24+) | SCORE-AI | 0.930 [0.874, 0.971] | 57% | 0.784 |