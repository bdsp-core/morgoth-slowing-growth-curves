# van Putten benchmark (SAP §8.7, Table 6) — FULL fleet coverage

All arms recomputed on the complete run: **27,003** recordings for the segment_master metrics (DAR/DTABR/SEF95/median_freq) and **27,003** for the whole-head metrics + the Morgoth gate (Q_*/p_slowing).

> The previously committed `vanputten_comparison.md` used only **3,130** recordings for the whole-head/gate arms and **14,450** for the rest — an incomplete `segment_summary` DOWNLOAD on the analysis box, not a fleet gap (S3 holds all 27,478; segment_master and segment_summary partition counts match exactly). This table supersedes it.

Labels are the CORRECTED SAP labels (`label_rederive_sap.py`: physiologic generalized slowing is NOT a positive — 5,528 recordings were previously mislabelled pathologic). AUROC [95% CI from a PATIENT-CLUSTERED bootstrap — patients resampled with replacement, all of their recordings carried along, per SAP §3.3]; auto-oriented so >0.5.

| method                         | abnormal            | generalized         | focal               |   n_scored |
|:-------------------------------|:--------------------|:--------------------|:--------------------|-----------:|
| Q_SLOWING (raw) [vP2013 k=.76] | 0.654 [0.646–0.661] | 0.702 [0.693–0.711] | 0.63 [0.622–0.638]  |      21984 |
| DAR (raw)                      | 0.667 [0.66–0.675]  | 0.731 [0.723–0.739] | 0.63 [0.622–0.638]  |      21984 |
| DTABR (raw)                    | 0.684 [0.676–0.691] | 0.743 [0.735–0.752] | 0.651 [0.643–0.659] |      21984 |
| SEF95 (raw)                    | 0.637 [0.629–0.645] | 0.665 [0.656–0.674] | 0.621 [0.613–0.629] |      21984 |
| median_freq (raw)              | 0.653 [0.646–0.66]  | 0.714 [0.706–0.723] | 0.622 [0.614–0.631] |      21984 |
| r_sBSI (raw)                   | 0.698 [0.691–0.706] | 0.692 [0.683–0.7]   | 0.726 [0.718–0.734] |      21984 |
| Q_APG (raw)                    | 0.649 [0.642–0.657] | 0.694 [0.684–0.704] | 0.622 [0.613–0.63]  |      21984 |
| Q_ASYM (raw)                   | 0.684 [0.677–0.692] | 0.69 [0.682–0.699]  | 0.697 [0.69–0.704]  |      21984 |
| Q_SLOWING (age-normed)         | 0.692 [0.684–0.699] | 0.751 [0.741–0.759] | 0.67 [0.663–0.679]  |      21981 |
| DAR (age-normed)               | 0.697 [0.689–0.704] | 0.772 [0.764–0.78]  | 0.663 [0.655–0.671] |      21981 |
| DTABR (age-normed)             | 0.719 [0.711–0.726] | 0.789 [0.781–0.797] | 0.691 [0.682–0.699] |      21981 |
| SEF95 (age-normed)             | 0.675 [0.669–0.682] | 0.711 [0.702–0.721] | 0.664 [0.656–0.673] |      21981 |
| r_sBSI (age-normed)            | 0.686 [0.679–0.694] | 0.675 [0.665–0.685] | 0.715 [0.707–0.724] |      21981 |
| Q_ASYM (age-normed)            | 0.679 [0.673–0.686] | 0.684 [0.675–0.692] | 0.693 [0.686–0.701] |      21981 |
| ** Morgoth p_slowing (gate) ** | 0.881 [0.876–0.886] | 0.918 [0.913–0.923] | 0.875 [0.87–0.881]  |      21984 |
