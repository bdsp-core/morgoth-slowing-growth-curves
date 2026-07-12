# van Putten benchmark (SAP §8.7, Table 6) — fleet-computed faithful metrics

n = 14450 (abnormal contrast); Q_SLOWING/Q_APG/r_sBSI/Q_ASYM available on 3130 recordings (segment_summary coverage, partial fleet run).

AUROC (point est.; auto-oriented so >0.5). Three arms per SAP: raw as-published, age-conditioned deviation, Morgoth gate.

| method                        |   abnormal |   generalized |   focal |
|:------------------------------|-----------:|--------------:|--------:|
| Q_SLOWING (raw) [vP2013 κ.76] |      0.646 |         0.705 |   0.624 |
| DAR (raw)                     |      0.666 |         0.766 |   0.629 |
| DTABR (raw)                   |      0.683 |         0.768 |   0.652 |
| SEF95 (raw)                   |      0.637 |         0.674 |   0.623 |
| r_sBSI (raw)                  |      0.704 |         0.625 |   0.734 |
| Q_APG (raw)                   |      0.636 |         0.715 |   0.607 |
| Q_ASYM (raw)                  |      0.687 |         0.631 |   0.707 |
| Q_SLOWING (age-normed)        |      0.679 |         0.727 |   0.661 |
| DAR (age-normed)              |      0.694 |         0.782 |   0.661 |
| DTABR (age-normed)            |      0.716 |         0.787 |   0.689 |
| r_sBSI (age-normed)           |      0.689 |         0.605 |   0.72  |
| Morgoth p_slowing (gate)      |      0.885 |         0.882 |   0.886 |