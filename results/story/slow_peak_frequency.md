# Slow-band frequency vs the frequency the report states (C146-c)

Measured on **30** recordings that state a slowing frequency in a slowing clause (cohort-wide, 5,785 such recordings exist).

| estimator | Spearman rho | p | median \|error\| |
|---|---|---|---|
| **slow-band median frequency (1-8 Hz)** | 0.083 | 0.66 | 1.25 Hz |
| slow-band 1/f-detrended peak | -0.105 | 0.58 | 2.18 Hz |
| full-band peak (1-45 Hz), the stored `peak_freq` | -0.219 | 0.25 | 2.00 Hz |

Reported frequency: median 3.00 Hz (IQR 2.12-4.88); measured slow-band median 1.93 Hz (IQR 1.63-2.44).

A raw PSD argmax inside the slow band is NOT usable and is excluded: EEG power falls off as roughly 1/f^a, so the largest value in any low band is its lowest bin. Measured that way every recording returns 1.0 Hz exactly and the correlation with the reported frequency is nil (rho = -0.10). Both estimators above are constructed not to be dominated by that aperiodic background.

The full-band peak is reported to show that the stored `peak_freq` cannot substitute: over 1-45 Hz the argmax lands on the posterior dominant rhythm whenever the record has one.
