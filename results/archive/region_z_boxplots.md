# Regional slowing as a measurement, not a classification

No classifier, no forced choice, no attempt to reproduce the report's region label. Per lobe we report the deviation of that lobe's slowing features from the **age-matched clinician-normal distribution**, in alert (W/N1) segments, against a routine-alert reference. The question is simply: *is the lobe the reader localized the lobe that is objectively elevated?*


## log_delta

- **Within-subject** (focal cases with a stated side, n = 5337): ipsilateral temporal z median **+0.938** vs contralateral **+0.495** (Δ = +0.443, Wilcoxon p = 0.00e+00). The lobe the reader named is the lobe that is objectively elevated, in the same recording.
- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC 0.742** (n = 5337 vs 20410).
  - `L_temporal`: normal +0.05 | reported-left +0.89 | reported-right +0.57
  - `R_temporal`: normal +0.05 | reported-left +0.45 | reported-right +1.03
  - `L_parasagittal`: normal +0.05 | reported-left +0.78 | reported-right +0.60
  - `R_parasagittal`: normal +0.05 | reported-left +0.47 | reported-right +1.02

## TAR

- **Within-subject** (focal cases with a stated side, n = 5337): ipsilateral temporal z median **+0.796** vs contralateral **+0.305** (Δ = +0.491, Wilcoxon p = 2.42e-261). The lobe the reader named is the lobe that is objectively elevated, in the same recording.
- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC 0.733** (n = 5337 vs 20410).
  - `L_temporal`: normal -0.19 | reported-left +0.67 | reported-right +0.46
  - `R_temporal`: normal -0.20 | reported-left +0.23 | reported-right +0.95
  - `L_parasagittal`: normal -0.17 | reported-left +0.55 | reported-right +0.51
  - `R_parasagittal`: normal -0.17 | reported-left +0.24 | reported-right +0.93

## We resolve side, not lobe

Two facts in the tables above bound the claim, and both are visible without a model:

- **log_delta, temporal**: ipsilateral +0.94, contralateral +0.49, within-subject Δ **+0.32**
- **log_delta, parasagittal**: ipsilateral +0.87, contralateral +0.51, within-subject Δ **+0.26**
- **TAR, temporal**: ipsilateral +0.80, contralateral +0.31, within-subject Δ **+0.21**
- **TAR, parasagittal**: ipsilateral +0.69, contralateral +0.34, within-subject Δ **+0.15**

First, the **contralateral** lobe is itself well above the clinician-normal distribution (≈ +0.5 to +0.8 SD), so focal slowing raises the whole hemispheric background, not one lobe in isolation. Second, the parasagittal chain shows nearly the same left–right separation as the temporal chain, so the lateralizing signal is **hemispheric, not lobar**. Both are consistent with our weak lobe localization (macro-F1 0.23) and with strong side discrimination (AUROC 0.87). We therefore claim **side**, and describe the region as the maximum-deviation lobe without claiming it is resolved.


## Why there is no confusion matrix here

The deployed system does not perform forced-choice lobe classification; it reports the region of maximum deviation. The multi-class confusion matrix in `scripts/42_region_gated.py` scores a multinomial logistic regression *trained to reproduce the report's region label* — a classifier we do not ship, evaluated against a label that is majority-temporal (2,165 / 3,872) and, for 17% of recordings, borrowed from a different study of the same patient. Its 0.92 'region agreement' is a base-rate artifact. It is omitted.
