# Slow-band dominant frequency vs the frequency the report states (C146-c)

Measured on **397** recordings that state a slowing frequency in a slowing clause (cohort-wide, 5,785 such recordings exist).

| comparison | Spearman rho | p | Pearson r |
|---|---|---|---|
| **slow-band peak (1-8 Hz)** vs reported | **-0.097** | 0.052 | -0.115 |
| full-band peak (1-45 Hz) vs reported | -0.109 | 0.03 | — |

Median absolute error of the slow-band peak against the reported frequency: **3.00 Hz**.

Measured slow-band peak: median 1.00 Hz (IQR 1.00-1.00); reported: median 4.00 Hz (IQR 3.00-5.50).

The full-band peak is shown to make the point that the stored `peak_freq` cannot substitute: over 1-45 Hz the argmax lands on the posterior dominant rhythm whenever the record has one, so it tracks the alpha frequency rather than the slowing.
