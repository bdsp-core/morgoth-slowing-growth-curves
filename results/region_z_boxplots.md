# Regional slowing as a measurement, not a classification

No classifier, no forced choice, no attempt to reproduce the report's region label. Per lobe we report the deviation of that lobe's slowing features from the **age-matched clinician-normal distribution**, in alert (W/N1) segments, against a routine-alert reference. The question is simply: *is the lobe the reader localized the lobe that is objectively elevated?*


## log_delta

- **Within-subject** (focal cases with a stated side, n = 2268): ipsilateral temporal z median **+0.944** vs contralateral **+0.548** (Δ = +0.396, Wilcoxon p = 2.49e-194). The lobe the reader named is the lobe that is objectively elevated, in the same recording.
- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC 0.746** (n = 2268 vs 9302).
  - `L_temporal`: normal -0.00 | reported-left +0.92 | reported-right +0.64
  - `R_temporal`: normal -0.01 | reported-left +0.50 | reported-right +1.00
  - `L_parasagittal`: normal +0.00 | reported-left +0.85 | reported-right +0.66
  - `R_parasagittal`: normal +0.01 | reported-left +0.53 | reported-right +1.03

## TAR

- **Within-subject** (focal cases with a stated side, n = 2268): ipsilateral temporal z median **+1.176** vs contralateral **+0.810** (Δ = +0.366, Wilcoxon p = 6.80e-143). The lobe the reader named is the lobe that is objectively elevated, in the same recording.
- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC 0.788** (n = 2268 vs 9302).
  - `L_temporal`: normal +0.03 | reported-left +1.15 | reported-right +0.92
  - `R_temporal`: normal +0.02 | reported-left +0.74 | reported-right +1.22
  - `L_parasagittal`: normal +0.04 | reported-left +1.04 | reported-right +0.90
  - `R_parasagittal`: normal +0.03 | reported-left +0.73 | reported-right +1.18

## We resolve side, not lobe

Two facts in the tables above bound the claim, and both are visible without a model:

- **log_delta, temporal**: ipsilateral +0.94, contralateral +0.55, within-subject Δ **+0.28**
- **log_delta, parasagittal**: ipsilateral +0.91, contralateral +0.59, within-subject Δ **+0.22**
- **TAR, temporal**: ipsilateral +1.18, contralateral +0.81, within-subject Δ **+0.22**
- **TAR, parasagittal**: ipsilateral +1.11, contralateral +0.79, within-subject Δ **+0.17**

First, the **contralateral** lobe is itself well above the clinician-normal distribution (≈ +0.5 to +0.8 SD), so focal slowing raises the whole hemispheric background, not one lobe in isolation. Second, the parasagittal chain shows nearly the same left–right separation as the temporal chain, so the lateralizing signal is **hemispheric, not lobar**. Both are consistent with our weak lobe localization (macro-F1 0.23) and with strong side discrimination (AUROC 0.87). We therefore claim **side**, and describe the region as the maximum-deviation lobe without claiming it is resolved.


## Why there is no confusion matrix here

The deployed system does not perform forced-choice lobe classification; it reports the region of maximum deviation. The multi-class confusion matrix in `scripts/42_region_gated.py` scores a multinomial logistic regression *trained to reproduce the report's region label* — a classifier we do not ship, evaluated against a label that is majority-temporal (2,165 / 3,872) and, for 17% of recordings, borrowed from a different study of the same patient. Its 0.92 'region agreement' is a base-rate artifact. It is omitted.
