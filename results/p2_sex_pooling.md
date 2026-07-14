# P2 — can sex be pooled in the norms? (re-verified on v6)

P2 had only ever been checked on the pre-run data. Here the normative reference is built two ways for each (stage × feature) cell — **pooled** across sexes, and **separately for female and male clean-normals** — and detection AUROC (slowing-positive vs clean-normal, corrected labels, `clean_pair` only) is compared. If sex genuinely carried information, splitting the reference by sex would sharpen detection.

| stage   | feature   |     n |   AUROC pooled |   AUROC by-sex |   dAUROC |
|:--------|:----------|------:|---------------:|---------------:|---------:|
| W       | TAR       | 20886 |         0.7326 |         0.7332 |   0.0006 |
| W       | DAR       | 20886 |         0.6779 |         0.6822 |   0.0043 |
| W       | log_delta | 20886 |         0.6784 |         0.678  |  -0.0004 |
| W       | log_theta | 20886 |         0.6379 |         0.6386 |   0.0008 |
| W       | rel_delta | 20886 |         0.6681 |         0.6691 |   0.001  |
| N1      | TAR       | 18980 |         0.708  |         0.7083 |   0.0004 |
| N1      | DAR       | 18980 |         0.6916 |         0.6921 |   0.0005 |
| N1      | log_delta | 18980 |         0.7461 |         0.7461 |  -0      |
| N1      | log_theta | 18980 |         0.7104 |         0.7116 |   0.0012 |
| N1      | rel_delta | 18980 |         0.6965 |         0.6974 |   0.0009 |
| N2      | TAR       | 17202 |         0.6454 |         0.6456 |   0.0002 |
| N2      | DAR       | 17202 |         0.6498 |         0.6502 |   0.0004 |
| N2      | log_delta | 17202 |         0.6812 |         0.6821 |   0.0009 |
| N2      | log_theta | 17202 |         0.6446 |         0.6458 |   0.0013 |
| N2      | rel_delta | 17202 |         0.582  |         0.5821 |   0      |

**max |ΔAUROC| = 0.0043**, median 0.0006. The pre-registered bar is 0.01.

**P2 → CONFIRMED.** Conditioning the norms on sex does not measurably improve detection, so sexes are pooled — which doubles the effective normative sample at every age.
