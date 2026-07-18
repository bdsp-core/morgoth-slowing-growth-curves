# Table 1 — Cohort characteristics (SAP §10)

Analysis set: recordings passing inclusion (SAP §3.2), panels excluded (§3.6 is a separate aim). Label rows are computed on `clean_pair` only (SAP §3.3, PITFALL 1 — report-broadcast guard); **1,664 EEGs dropped by the clean_pair filter**. CIs elsewhere are patient-clustered on `patient_id` (SAP §3.3).

| Characteristic | Overall | Routine (cohort) | Overnight (expansion) | Clean-normal | Abnormal |
|---|---|---|---|---|---|
| Recordings, n | 25,536 | 19,617 | 5,919 | 10,189 | 12,676 |
| Patients, n (unique) | 21,757 | 17,366 | 5,101 | 9,347 | 10,781 |
| Age, y — median [IQR] | 48.2 [22.0–66.8] | 45.0 [20.2–65.7] | 55.6 [31.5–69.4] | 36.8 [18.6–59.2] | 53.9 [24.3–69.7] |
|   Age band 0–18 | 5,153 (20.2%) | 4,344 (22.1%) | 809 (13.7%) | 2,447 (24.0%) | 2,434 (19.2%) |
|   Age band 18–45 | 6,804 (26.6%) | 5,460 (27.8%) | 1,344 (22.7%) | 3,469 (34.0%) | 2,726 (21.5%) |
|   Age band 45–60 | 4,642 (18.2%) | 3,426 (17.5%) | 1,216 (20.5%) | 1,817 (17.8%) | 2,283 (18.0%) |
|   Age band 60–75 | 5,622 (22.0%) | 3,995 (20.4%) | 1,627 (27.5%) | 1,661 (16.3%) | 3,214 (25.4%) |
|   Age band 75+ | 3,310 (13.0%) | 2,392 (12.2%) | 918 (15.5%) | 795 (7.8%) | 2,018 (15.9%) |
| Sex — female | 12,553 (49.2%) | 9,539 (48.6%) | 3,014 (50.9%) | 4,946 (48.5%) | 6,238 (49.2%) |
| Recording length, min — median [IQR] | 66.0 [48.1–91.7] | 62.1 [46.7–78.7] | 693.0 [59.0–1288.6] | 66.5 [48.1–85.4] | 64.2 [47.9–90.8] |
|   > 1 h (cEEG) | 14,816 (58.0%) | 10,421 (53.1%) | 4,395 (74.3%) | 6,069 (59.6%) | 7,020 (55.4%) |
| Usable segments — median [IQR] | 130 [94–216] | 120 [93–175] | 1031 [97–3721] | 136 [95–192] | 122 [92–208] |
|   Artifact-flagged segments | 46.7% | 48.6% | 40.3% | 47.3% | 46.9% |
|   Stage W (segment-weighted) | 30.5% | 44.9% | 25.9% | 44.4% | 28.2% |
|   Stage N1 (segment-weighted) | 13.7% | 17.6% | 12.5% | 13.3% | 13.7% |
|   Stage N2 (segment-weighted) | 28.7% | 20.6% | 31.3% | 24.4% | 29.7% |
|   Stage N3 (segment-weighted) | 20.1% | 7.9% | 24.1% | 8.4% | 21.9% |
|   Stage REM (segment-weighted) | 7.0% | 9.0% | 6.3% | 9.5% | 6.6% |
| Report paired (clean_pair) | 23,872 (93.5%) | 18,879 (96.2%) | 4,993 (84.4%) | 10,189 (100.0%) | 12,676 (100.0%) |
| clean_normal | 10,189 (42.7%) | 9,269 (49.1%) | 920 (18.4%) | 10,189 (100.0%) | 0 (0.0%) |
| is_abnormal | 12,676 (53.1%) | 9,089 (48.1%) | 3,587 (71.8%) | 0 (0.0%) | 12,676 (100.0%) |
|   Focal slowing | 8,304 (34.8%) | 5,846 (31.0%) | 2,458 (49.2%) | 0 (0.0%) | 8,016 (63.2%) |
|   Generalized slowing — pathologic | 6,841 (28.7%) | 5,108 (27.1%) | 1,733 (34.7%) | 0 (0.0%) | 6,841 (54.0%) |
|   Generalized slowing — physiologic | 3,382 (14.2%) | 3,130 (16.6%) | 252 (5.0%) | 3,009 (29.5%) | 0 (0.0%) |
|     Focal side left | 3,129 (24.7%) | 2,312 (25.4%) | 817 (22.8%) | — | 3,129 (24.7%) |
|     Focal side right | 2,099 (16.6%) | 1,483 (16.3%) | 616 (17.2%) | — | 2,099 (16.6%) |
|     Focal side bilateral | 2,365 (18.7%) | 1,585 (17.4%) | 780 (21.7%) | — | 2,365 (18.7%) |
|     Gen topography anterior | 600 (4.7%) | 398 (4.4%) | 202 (5.6%) | — | 600 (4.7%) |
|     Gen topography posterior | 724 (5.7%) | 534 (5.9%) | 190 (5.3%) | — | 724 (5.7%) |
|     Gen topography unspec | 3,129 (24.7%) | 2,470 (27.2%) | 659 (18.4%) | — | 3,129 (24.7%) |
|     Band delta | 2,088 (16.5%) | 1,368 (15.1%) | 720 (20.1%) | — | 2,088 (16.5%) |
|     Band theta | 1,709 (13.5%) | 1,264 (13.9%) | 445 (12.4%) | — | 1,709 (13.5%) |
|     Band mixed | 6,447 (50.9%) | 4,553 (50.1%) | 1,894 (52.8%) | — | 6,447 (50.9%) |

_Generated from the new run's canonical tables (recording_meta + recording_labels); n=25,536 included recordings, 21,757 unique patients._
