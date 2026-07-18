# SB / Sandor_100 — external validation: our models vs SCORE-AI vs Morgoth vs experts

Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → our report-trained detectors) run UNCHANGED on 98/100 external EMU EEGs. Ground truth = expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under our ROC curve.

| axis | model | AUROC [95% CI] | % experts under ROC | AP |
|---|---|---|---|---|
| focal (22+) | ours | 0.736 [0.621, 0.833] | 0% | 0.445 |
| focal (22+) | Morgoth | 0.609 [0.453, 0.749] | 7% | 0.357 |
| focal (22+) | SCORE-AI | 0.605 [0.479, 0.717] | 0% | 0.269 |
| generalized (24+) | ours | 0.893 [0.784, 0.978] | 50% | 0.846 |
| generalized (24+) | Morgoth | 0.951 [0.892, 0.991] | 71% | 0.889 |
| generalized (24+) | SCORE-AI | 0.930 [0.874, 0.971] | 57% | 0.784 |