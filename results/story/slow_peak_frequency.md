# Slow-band frequency vs the frequency the report states (C146-c)

Measured on **40** recordings that state a slowing frequency in a slowing clause (cohort-wide, 5,785 such recordings exist).

| estimator | Spearman rho | p | median \|error\| |
|---|---|---|---|
| **slow-band median frequency (1-8 Hz)** | 0.177 | 0.27 | 1.13 Hz |
| slow-band 1/f-detrended peak | -0.025 | 0.88 | 2.82 Hz |
| full-band peak (1-45 Hz), the stored `peak_freq` | -0.077 | 0.64 | 2.00 Hz |

Reported frequency: median 3.00 Hz (IQR 2.00-5.00); measured slow-band median 2.02 Hz (IQR 1.72-2.31).

A raw PSD argmax inside the slow band is NOT usable and is excluded: EEG power falls off as roughly 1/f^a, so the largest value in any low band is its lowest bin. Measured that way every recording returns 1.0 Hz exactly and the correlation with the reported frequency is nil (rho = -0.10). Both estimators above are constructed not to be dominated by that aperiodic background.

The full-band peak is reported to show that the stored `peak_freq` cannot substitute: over 1-45 Hz the argmax lands on the posterior dominant rhythm whenever the record has one.
