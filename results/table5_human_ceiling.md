# Table 5 — Inter-rater reliability and the human ceiling (SAP §10), RE-RUN on v6

Independent panel: **100 EEGs x 18 electroencephalographers**. These EEGs were featurized by the v6 fleet and scored with the v6 gate; nothing here touches report-derived labels, so this analysis was structurally immune to the report-label bug that invalidated the detection claims (SAP §3.4/§3.5).

## The ceiling (a property of the raters, not of our pipeline)

| axis | Fleiss kappa | prevalence by expert majority |
|---|---|---|
| focal slowing | **0.373** | 12/100 |
| generalized slowing | **0.450** | 18/100 |

Slowing is the *least* reliable judgement these experts make. Both values reproduce the previously published figures exactly.

## Our v6 gate against the panel

| score                 |   AUROC vs expert majority |   Spearman rho vs PROPORTION of experts |       p |
|:----------------------|---------------------------:|----------------------------------------:|--------:|
| Morgoth p_generalized |                      0.86  |                                   0.609 | 1.7e-11 |
| Morgoth p_focal       |                      0.904 |                                   0.635 | 1.4e-12 |

The Spearman column is the **conspicuity** result: our score tracks *how many experts saw the slowing*, which is the evidence the 'readers under-report slowing' argument actually rests on. It is non-circular (scored against expert votes, never report labels).

## P7 — do we MEET the ceiling?

**No.** Ranking and calibration are different claims. Our gate out-RANKS the experts (AUROC above), but at an operating point chosen leave-one-out it achieves balanced accuracy **0.748 (focal)** and **0.757 (generalized)** against a between-rater ceiling of **0.795** and **0.809**. P7 is therefore **FALSIFIED** (see `results/table4_predictions.md`).
