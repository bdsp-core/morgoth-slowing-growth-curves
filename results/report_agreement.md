# Agreement with clinical reports (report-derived finding flags)
Matched **11339 / 12379** cohort recordings to a report (EEG/HEEDB_Metadata). AUC of each score vs the report flag.

| target (report flag) | Morgoth AUC | our-LR AUC | our-simple AUC |
|---|---|---|---|
| r_abnormal (pos 0.45) | 0.904 | 0.752 | 0.660 |
| r_focal (pos 0.16) | 0.785 | 0.630 | 0.626 |
| r_gen (pos 0.66) | 0.745 | 0.646 | 0.603 |

**Read:** Morgoth tracks the reports strongly (abnormal ~0.90; focal ~0.79; generalized ~0.75). Our objective LR on age/sex deviations is close behind — face validity that our features capture what experts write. Band (δ/θ/mixed) and exact side/region need the report TEXT (scripts/18 part B).
