# Slow-band frequency vs the frequency the report states (C146-c)

Measured on **370** recordings that state a slowing frequency in a slowing clause (cohort-wide, 5,785 such recordings exist).

| estimator | Spearman rho | p | median \|error\| |
|---|---|---|---|
| **slow-band median frequency (1-8 Hz)** | 0.036 | 0.49 | 2.08 Hz |
| slow-band 1/f-detrended peak | -0.078 | 0.13 | 2.27 Hz |
| full-band peak (1-45 Hz), the stored `peak_freq` | -0.049 | 0.35 | 3.00 Hz |

Reported frequency: median 4.50 Hz (IQR 3.00-5.50); measured slow-band median 1.85 Hz (IQR 1.61-2.28).

A raw PSD argmax inside the slow band is NOT usable and is excluded: EEG power falls off as roughly 1/f^a, so the largest value in any low band is its lowest bin. Measured that way every recording returns 1.0 Hz exactly and the correlation with the reported frequency is nil (rho = -0.10). Both estimators above are constructed not to be dominated by that aperiodic background.

The full-band peak is reported to show that the stored `peak_freq` cannot substitute: over 1-45 Hz the argmax lands on the posterior dominant rhythm whenever the record has one.
