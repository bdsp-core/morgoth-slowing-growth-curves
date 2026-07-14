# Can an algorithm agree with each expert better than the experts agree with each other? (v6)

**kappa_ee** is the mean pairwise Cohen kappa between the 18 experts — the expert–expert ceiling. **kappa_ae** is the mean Cohen kappa between the algorithm's binary call and each expert taken individually. The algorithm's threshold is chosen **leave-one-EEG-out**, so no recording contributes to the threshold that classifies it. The CI is a bootstrap over EEGs on the *difference*.

Why this can hold even though **P7 is falsified**: kappa is chance-corrected and penalises prevalence mismatch, whereas balanced accuracy is not and does not. They are different questions — 'does the algorithm agree with a typical reader as well as two readers agree with each other' is not 'does the algorithm beat the readers at a chosen operating point'. Reporting only whichever one flatters us would be the error.

| axis        | score             |   kappa_ae |   kappa_ee (ceiling) |   difference | 95% CI           | beats the ceiling?   |
|:------------|:------------------|-----------:|---------------------:|-------------:|:-----------------|:---------------------|
| focal       | Morgoth gate      |      0.349 |                0.386 |       -0.037 | [-0.149, +0.072] | no                   |
| focal       | deviation score S |      0.477 |                0.386 |        0.091 | [-0.022, +0.155] | no                   |
| generalized | Morgoth gate      |      0.333 |                0.446 |       -0.113 | [-0.253, +0.026] | no                   |
| generalized | deviation score S |      0.472 |                0.446 |        0.026 | [-0.040, +0.100] | no                   |

**The claim does NOT survive on v6.** No score beats the expert–expert ceiling on kappa with a CI excluding zero. The legacy figures (Morgoth kappa_ae = 0.471 vs kappa_ee = 0.403 on focal) were computed on the contaminated legacy run and must be **withdrawn** from the manuscript.

Neither score reaches sqrt(kappa_ee) (0.62–0.67), the value classical test theory predicts for an algorithm sitting at the latent truth — so neither is at the truth. Because expert errors are correlated (shared training, shared blind spots), sqrt(kappa_ee) is a conservative target.
