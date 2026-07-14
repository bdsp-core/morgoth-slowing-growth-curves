# P2 — can sex be pooled in the norms? (re-verified on v6)

P2 had only ever been checked on the pre-run data. Here the normative reference is built two ways for each (stage × feature) cell — **pooled** across sexes, and **separately for female and male clean-normals** — and detection AUROC (slowing-positive vs clean-normal, corrected labels, `clean_pair` only) is compared. If sex genuinely carried information, splitting the reference by sex would sharpen detection.

| stage   | feature   |     n |   AUROC pooled |   AUROC by-sex |   dAUROC |
|:--------|:----------|------:|---------------:|---------------:|---------:|
| W       | TAR       | 20885 |         0.7328 |         0.7334 |   0.0006 |
| W       | DAR       | 20885 |         0.6779 |         0.6822 |   0.0043 |
| W       | log_delta | 20885 |         0.6783 |         0.6779 |  -0.0004 |
| W       | log_theta | 20885 |         0.6379 |         0.6387 |   0.0008 |
| W       | rel_delta | 20885 |         0.6681 |         0.6691 |   0.001  |
| N1      | TAR       | 18980 |         0.7081 |         0.7084 |   0.0003 |
| N1      | DAR       | 18980 |         0.6916 |         0.6921 |   0.0005 |
| N1      | log_delta | 18980 |         0.746  |         0.746  |   0      |
| N1      | log_theta | 18980 |         0.7102 |         0.7114 |   0.0012 |
| N1      | rel_delta | 18980 |         0.6964 |         0.6973 |   0.0009 |
| N2      | TAR       | 17201 |         0.646  |         0.6462 |   0.0002 |
| N2      | DAR       | 17201 |         0.6503 |         0.6507 |   0.0004 |
| N2      | log_delta | 17201 |         0.6816 |         0.6826 |   0.0009 |
| N2      | log_theta | 17201 |         0.6447 |         0.646  |   0.0013 |
| N2      | rel_delta | 17201 |         0.5823 |         0.5824 |   0      |

**max |ΔAUROC| = 0.0043**, median 0.0006. The pre-registered bar is 0.01.

**P2 → CONFIRMED.** Conditioning the norms on sex does not measurably improve detection, so sexes are pooled — which doubles the effective normative sample at every age.
