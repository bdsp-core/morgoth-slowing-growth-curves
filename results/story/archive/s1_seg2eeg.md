# Section 1b — recovering EEG-level slowing from 30 s-context segment detections, by stage

For each axis, using only ONE stage's segments, we pool them into p_eeg' and score it against Morgoth's EEG-level head (Spearman rho, 'recover') and the report label (AUROC, 'predict'). Table shows the BEST rule per (axis, stage) on each target; the selection threshold X is read from the best `*_gt_X` rule.


## FOCAL slowing

| stage | n EEG | best-recover rule (rho vs head) | best-predict rule (AUROC vs report) |
|---|---|---|---|
| W | 23,903 | top5_mean (ρ=0.77) | top5_mean (AUROC=0.786) |
| N1 | 21,977 | top5_mean (ρ=0.81) | p90 (AUROC=0.797) |
| N2 | 19,955 | top5_mean (ρ=0.81) | p90 (AUROC=0.779) |
| N3 | 11,354 | top5_mean (ρ=0.78) | mean_gt_0.15 (AUROC=0.742) |
| REM | 19,644 | top5_mean (ρ=0.76) | p90 (AUROC=0.781) |
| ALL | 23,905 | top5_mean (ρ=0.85) | top5_mean (AUROC=0.813) |

## GENERALIZED slowing

| stage | n EEG | best-recover rule (rho vs head) | best-predict rule (AUROC vs report) |
|---|---|---|---|
| W | 23,903 | max (ρ=0.81) | mean_gt_0.35 (AUROC=0.749) |
| N1 | 21,977 | mean_gt_0.25 (ρ=0.83) | mean_gt_0.25 (AUROC=0.773) |
| N2 | 19,955 | top5_mean (ρ=0.85) | mean_gt_0.25 (AUROC=0.761) |
| N3 | 11,354 | top5_mean (ρ=0.82) | mean_gt_0.25 (AUROC=0.716) |
| REM | 19,644 | mean_gt_0.25 (ρ=0.81) | mean_gt_0.25 (AUROC=0.764) |
| ALL | 23,905 | frac_gt_0.65 (ρ=0.90) | p90 (AUROC=0.785) |