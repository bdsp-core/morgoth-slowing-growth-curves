# SB / Sandor_100 — external validation: our models vs SCORE-AI vs Morgoth vs experts

Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → our report-trained detectors) run UNCHANGED on 59/100 external EMU EEGs. Ground truth = expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under our ROC curve.

| axis | model | AUROC [95% CI] | % experts under ROC | AP |
|---|---|---|---|---|
| focal (13+) | ours | 0.779 [0.639, 0.900] | 7% | 0.466 |
| focal (13+) | Morgoth | 0.657 [0.480, 0.824] | 7% | 0.320 |
| focal (13+) | SCORE-AI | 0.619 [0.463, 0.769] | 0% | 0.271 |
| generalized (14+) | ours | 0.871 [0.698, 1.000] | 71% | 0.893 |
| generalized (14+) | Morgoth | 0.983 [0.950, 1.000] | 86% | 0.941 |
| generalized (14+) | SCORE-AI | 0.927 [0.854, 0.984] | 57% | 0.799 |