# Does the detector exploit age? (review comment 14)

Abnormal recordings are ~17 y older than clean-normals, and chronological age is a feature in both heads, so the classifier could in principle recover the age-label association instead of reading the deviation field. Five arms, reported even-handedly.

| axis | arm | test set | AUROC [95% CI] | n | positives |
|---|---|---|---|---|---|
| focal | age-only | report-test | 0.591 [0.568, 0.613] | 2,989 | 989 |
| focal | age-only | ON-100 | 0.661 [0.492, 0.820] | 95 | 14 |
| focal | deviation-only | report-test | 0.738 [0.719, 0.757] | 2,989 | 989 |
| focal | deviation-only | ON-100 | 0.912 [0.836, 0.971] | 95 | 14 |
| focal | deviation+age | report-test | 0.737 [0.719, 0.757] | 2,989 | 989 |
| focal | deviation+age | ON-100 | 0.920 [0.851, 0.973] | 95 | 14 |
| generalized | age-only | report-test | 0.610 [0.585, 0.636] | 2,989 | 625 |
| generalized | age-only | ON-100 | 0.712 [0.551, 0.866] | 95 | 17 |
| generalized | deviation-only | report-test | 0.710 [0.687, 0.732] | 2,989 | 625 |
| generalized | deviation-only | ON-100 | 0.925 [0.870, 0.970] | 95 | 17 |
| generalized | deviation+age | report-test | 0.717 [0.694, 0.739] | 2,989 | 625 |
| generalized | deviation+age | ON-100 | 0.937 [0.886, 0.977] | 95 | 17 |

## Age-stratified (deviation+age, report-test)

Within a decade band age barely varies, so a shortcut has little to exploit; if performance held up only across bands it would be doing demographics, not EEG.

| axis | age band | AUROC [95% CI] | n | positives |
|---|---|---|---|---|
| focal | 0-10 | 0.603 [0.537, 0.667] | 423 | 110 |
| focal | 10-20 | 0.674 [0.599, 0.750] | 279 | 69 |
| focal | 20-30 | 0.724 [0.652, 0.790] | 308 | 78 |
| focal | 30-40 | 0.757 [0.682, 0.822] | 276 | 67 |
| focal | 40-50 | 0.687 [0.614, 0.755] | 294 | 88 |
| focal | 50-60 | 0.742 [0.688, 0.792] | 388 | 153 |
| focal | 60-70 | 0.756 [0.707, 0.805] | 427 | 173 |
| focal | 70-80 | 0.815 [0.769, 0.857] | 339 | 149 |
| focal | 80-90 | 0.746 [0.675, 0.815] | 211 | 84 |
| generalized | 0-10 | 0.608 [0.534, 0.681] | 423 | 73 |
| generalized | 10-20 | 0.760 [0.671, 0.839] | 279 | 37 |
| generalized | 20-30 | 0.718 [0.627, 0.805] | 308 | 40 |
| generalized | 30-40 | 0.757 [0.662, 0.843] | 276 | 33 |
| generalized | 40-50 | 0.726 [0.647, 0.799] | 294 | 60 |
| generalized | 50-60 | 0.698 [0.628, 0.760] | 388 | 88 |
| generalized | 60-70 | 0.696 [0.634, 0.756] | 427 | 100 |
| generalized | 70-80 | 0.676 [0.621, 0.734] | 339 | 108 |
| generalized | 80-90 | 0.647 [0.560, 0.722] | 211 | 67 |

## Age-matched (inverse-propensity reweighted)

| axis | test set | AUROC raw | AUROC age-matched | n |
|---|---|---|---|---|
| focal | report-test | 0.737 | 0.708 | 2,989 |
| focal | ON-100 | 0.920 | 0.898 | 95 |
| generalized | report-test | 0.717 | 0.684 | 2,989 |
| generalized | ON-100 | 0.937 | 0.944 | 95 |

## Verdict

- **focal, report-test** — age alone 0.591; deviation alone 0.738; deviation+age 0.737. Dropping age costs -0.001; the deviation field adds +0.147 over age alone.
- **focal, ON-100** — age alone 0.661; deviation alone 0.912; deviation+age 0.920. Dropping age costs +0.008; the deviation field adds +0.251 over age alone.
- **generalized, report-test** — age alone 0.610; deviation alone 0.710; deviation+age 0.717. Dropping age costs +0.007; the deviation field adds +0.100 over age alone.
- **generalized, ON-100** — age alone 0.712; deviation alone 0.925; deviation+age 0.937. Dropping age costs +0.012; the deviation field adds +0.213 over age alone.
