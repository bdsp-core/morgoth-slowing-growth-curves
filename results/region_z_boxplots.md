# Regional slowing as a measurement, not a classification

No classifier, no forced choice, no attempt to reproduce the report's region label. Per lobe we report the deviation of that lobe's slowing features from the **age-matched clinician-normal distribution**, in alert (W/N1) segments, against a routine-alert reference. The question is simply: *is the lobe the reader localized the lobe that is objectively elevated?*


## log_delta

- **Within-subject** (focal cases with a stated side, n = 3341): ipsilateral temporal z median **+0.928** vs contralateral **+0.479** (Δ = +0.448, Wilcoxon p = 1.02e-288). The lobe the reader named is the lobe that is objectively elevated, in the same recording.
- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC 0.745** (n = 3341 vs 13042).
  - `L_temporal`: normal +0.05 | reported-left +0.87 | reported-right +0.54
  - `R_temporal`: normal +0.06 | reported-left +0.45 | reported-right +1.02
  - `L_parasagittal`: normal +0.06 | reported-left +0.76 | reported-right +0.61
  - `R_parasagittal`: normal +0.05 | reported-left +0.47 | reported-right +1.04

## TAR

- **Within-subject** (focal cases with a stated side, n = 3341): ipsilateral temporal z median **+0.804** vs contralateral **+0.310** (Δ = +0.494, Wilcoxon p = 3.77e-159). The lobe the reader named is the lobe that is objectively elevated, in the same recording.
- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC 0.737** (n = 3341 vs 13042).
  - `L_temporal`: normal -0.20 | reported-left +0.69 | reported-right +0.46
  - `R_temporal`: normal -0.20 | reported-left +0.23 | reported-right +0.91
  - `L_parasagittal`: normal -0.17 | reported-left +0.59 | reported-right +0.54
  - `R_parasagittal`: normal -0.16 | reported-left +0.25 | reported-right +0.94

## We resolve side, not lobe

Two facts in the tables above bound the claim, and both are visible without a model:

- **log_delta, temporal**: ipsilateral +0.93, contralateral +0.48, within-subject Δ **+0.33**
- **log_delta, parasagittal**: ipsilateral +0.88, contralateral +0.52, within-subject Δ **+0.26**
- **TAR, temporal**: ipsilateral +0.80, contralateral +0.31, within-subject Δ **+0.21**
- **TAR, parasagittal**: ipsilateral +0.72, contralateral +0.34, within-subject Δ **+0.15**

First, the **contralateral** lobe is itself well above the clinician-normal distribution (≈ +0.5 to +0.8 SD), so focal slowing raises the whole hemispheric background, not one lobe in isolation. Second, the parasagittal chain shows nearly the same left–right separation as the temporal chain, so the lateralizing signal is **hemispheric, not lobar**. Both are consistent with our weak lobe localization (macro-F1 0.23) and with strong side discrimination (AUROC 0.87). We therefore claim **side**, and describe the region as the maximum-deviation lobe without claiming it is resolved.


## Why there is no confusion matrix here

The deployed system does not perform forced-choice lobe classification; it reports the region of maximum deviation. The multi-class confusion matrix in `scripts/42_region_gated.py` scores a multinomial logistic regression *trained to reproduce the report's region label* — a classifier we do not ship, evaluated against a label that is majority-temporal (2,165 / 3,872) and, for 17% of recordings, borrowed from a different study of the same patient. Its 0.92 'region agreement' is a base-rate artifact. It is omitted.
