# van Putten benchmark (SAP §8.7, Table 6) — FULL fleet coverage

All arms recomputed on the SAP §3.3 **clean_pair** set (feature coverage 23,872 recordings for the segment_master metrics [DAR/DTABR/SEF95/median_freq] and 23,872 for the whole-head metrics + the Morgoth gate [Q_*/p_slowing]). Each AUROC is scored on its own contrast — clean-normal vs the relevant positive class — so the benchmark denominator is the **n_scored** column (**21,146** for the any-abnormal contrast: 10,189 clean-normal vs 10,957 slowing-positive), NOT the raw feature-coverage count.

> The previously committed `vanputten_comparison.md` used only **3,130** recordings for the whole-head/gate arms and **14,450** for the rest — an incomplete `segment_summary` DOWNLOAD on the analysis box, not a fleet gap (S3 holds all 27,478; segment_master and segment_summary partition counts match exactly). This table supersedes it.

Labels are the CORRECTED SAP labels (`label_rederive_sap.py`: physiologic generalized slowing is NOT a positive — 5,528 recordings were previously mislabelled pathologic). AUROC [95% CI from a PATIENT-CLUSTERED bootstrap — patients resampled with replacement, all of their recordings carried along, per SAP §3.3]; auto-oriented so >0.5.

| method                         | abnormal            | generalized         | focal               |   n_scored |
|:-------------------------------|:--------------------|:--------------------|:--------------------|-----------:|
| Q_SLOWING (raw) [vP2013 k=.76] | 0.646 [0.638–0.654] | 0.691 [0.682–0.7]   | 0.62 [0.612–0.629]  |      21146 |
| DAR (raw)                      | 0.657 [0.648–0.665] | 0.719 [0.711–0.728] | 0.619 [0.609–0.627] |      21146 |
| DTABR (raw)                    | 0.674 [0.667–0.681] | 0.732 [0.723–0.741] | 0.641 [0.632–0.649] |      21146 |
| SEF95 (raw)                    | 0.631 [0.624–0.639] | 0.657 [0.646–0.667] | 0.615 [0.605–0.624] |      21146 |
| median_freq (raw)              | 0.644 [0.637–0.652] | 0.703 [0.693–0.712] | 0.612 [0.603–0.621] |      21146 |
| r_sBSI (raw)                   | 0.696 [0.688–0.703] | 0.685 [0.675–0.694] | 0.723 [0.715–0.73]  |      21146 |
| Q_APG (raw)                    | 0.643 [0.635–0.651] | 0.687 [0.678–0.697] | 0.615 [0.606–0.623] |      21146 |
| Q_ASYM (raw)                   | 0.68 [0.672–0.689]  | 0.682 [0.673–0.692] | 0.692 [0.684–0.7]   |      21146 |
| Q_SLOWING (age-normed)         | 0.681 [0.673–0.689] | 0.736 [0.726–0.745] | 0.659 [0.65–0.667]  |      21145 |
| DAR (age-normed)               | 0.684 [0.677–0.692] | 0.756 [0.746–0.765] | 0.65 [0.642–0.658]  |      21145 |
| DTABR (age-normed)             | 0.707 [0.7–0.713]   | 0.773 [0.766–0.782] | 0.678 [0.67–0.686]  |      21145 |
| SEF95 (age-normed)             | 0.667 [0.659–0.674] | 0.699 [0.689–0.709] | 0.656 [0.648–0.665] |      21145 |
| r_sBSI (age-normed)            | 0.683 [0.676–0.692] | 0.667 [0.657–0.677] | 0.712 [0.704–0.719] |      21145 |
| Q_ASYM (age-normed)            | 0.675 [0.668–0.682] | 0.675 [0.667–0.685] | 0.688 [0.681–0.696] |      21145 |
| ** Morgoth p_slowing (gate) ** | 0.875 [0.87–0.88]   | 0.911 [0.906–0.917] | 0.87 [0.864–0.875]  |      21146 |
