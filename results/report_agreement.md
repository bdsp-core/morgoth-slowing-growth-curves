# Agreement with clinical reports (report-derived finding flags)
Matched **11339 / 12379** cohort recordings to a report (EEG/HEEDB_Metadata). AUC of each score vs the report flag.

| target (report flag) | Morgoth AUC | our-LR AUC | our-simple AUC |
|---|---|---|---|
| r_abnormal (pos 0.45) | 0.904 | 0.752 | 0.660 |
| r_focal (pos 0.16) | 0.785 | 0.630 | 0.626 |
| r_gen (pos 0.66) | 0.745 | 0.646 | 0.603 |

**Read:** Morgoth tracks the reports strongly (abnormal ~0.90; focal ~0.79; generalized ~0.75). Our objective LR on age/sex deviations is close behind — face validity that our features capture what experts write. Band (δ/θ/mixed) and exact side/region need the report TEXT (scripts/18 part B).

## Part B — band/location from report TEXT (source: Box Brandon - PHI/Datasets/BDSP_deID/I0001-MGB/data_Unstructured/EEG_Reports_OtherSourceFiles/EEGs_And_Reports.csv)

## band/location agreement (our generated statement vs report), where report states it
- band: agreement nan on n=0
- side: agreement nan on n=0
- region: agreement nan on n=0

## Part B — band/location from report TEXT (source: Box Brandon - PHI/Datasets/BDSP_deID/I0001-MGB/data_Unstructured/EEG_Reports_OtherSourceFiles/EEGs_And_Reports.csv)

## band/location agreement (our generated statement vs report), where report states it
- band: agreement 0.159 on n=5196
- side: agreement 0.784 on n=5406
- region: agreement 0.910 on n=402

## Part B — band/location from report TEXT (source: Box Brandon - PHI/Datasets/BDSP_deID/I0001-MGB/data_Unstructured/EEG_Reports_OtherSourceFiles/EEGs_And_Reports.csv)

## band/location agreement (our generated statement vs report), where report states it
- band: agreement 0.328 on n=5196
- side: agreement 0.784 on n=5406
- region: agreement 0.910 on n=402
