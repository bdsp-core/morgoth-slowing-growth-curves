# OccasionNoise — the human ceiling for slowing

100 EEGs, 18 experts, 15–18 raters per EEG. Balanced by design (20 focal-epileptiform / 20 generalized-epileptiform / 20 focal-non-epileptiform / 20 generalized-non-epileptiform / 16 normal / 4 normal-variant), so AUROC and κ transfer but prevalence-dependent metrics (PPV) do not.

## Between-rater agreement (Part I)

| axis | prevalence | Fleiss κ | pairwise Cohen κ median [IQR] |
|---|---|---|---|
| focal epileptiform | 0.178 | 0.585 | 0.643 [0.558–0.704] |
| FOCAL SLOWING | 0.181 | 0.373 | 0.394 [0.285–0.461] |
| generalized epileptiform | 0.166 | 0.739 | 0.805 [0.731–0.859] |
| GENERALIZED SLOWING | 0.228 | 0.450 | 0.451 [0.346–0.534] |

## Within-rater: the SAME expert re-reading the SAME EEG (Part I vs Part II)

| axis | raw agreement | Cohen κ |
|---|---|---|
| focal epileptiform | 0.913 | 0.716 |
| FOCAL SLOWING | 0.873 | 0.563 |
| generalized epileptiform | 0.955 | 0.832 |
| GENERALIZED SLOWING | 0.879 | 0.642 |

(n = 1335 repeat reads by 15 experts)

## Expert vs consensus (leave-one-out majority of the other raters)

| axis | sensitivity | specificity | balanced accuracy | κ |
|---|---|---|---|---|
| FOCAL SLOWING | 0.703 | 0.899 | **0.801** (range 0.578–1.000) | 0.526 |
| GENERALIZED SLOWING | 0.735 | 0.884 | **0.809** (range 0.686–0.943) | 0.576 |

## Signed clinical report vs the expert panel

Fraction of experts marking each axis, by the category assigned from the signed report:

| signed-report category | experts marking focal slowing | experts marking gen. slowing |
|---|---|---|
| Focal epileptiform | 0.246 | 0.067 |
| Focal non-epileptiform | 0.508 | 0.185 |
| Generalized epileptiform | 0.050 | 0.192 |
| Generalized non-epileptiform | 0.082 | 0.644 |
| Normal | 0.015 | 0.048 |
| Normal variant | 0.059 | 0.045 |

On EEGs the **signed report** called focal non-epileptiform, only 50.8% of experts marked focal slowing. This bounds every 'agreement with the report' number in the paper.

## Morgoth (the gate) against the same expert majority

| axis | AUROC vs majority | Morgoth's own threshold | expert-vs-consensus |
|---|---|---|---|
| FOCAL SLOWING | **0.923** | bal-acc 0.714 (sens 0.429, spec 1.000) | bal-acc 0.801 |
| GENERALIZED SLOWING | **0.895** | bal-acc 0.667 (sens 0.333, spec 1.000) | bal-acc 0.809 |

Morgoth **ranks** better than the average expert but its **thresholded operating point** is far below them: near-perfect specificity, badly deficient sensitivity. Ranking quality and operating-point calibration are different claims and must be reported separately.
