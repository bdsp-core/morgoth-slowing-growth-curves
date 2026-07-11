# Pilot segment_master summary (plumbing proof — analysis reads the canonical table)

Source: `data/derived/segment_master` (eeg_id-keyed) — **15 EEGs**, 19,938 rows. Usable whole-head segments: 1,641. *Pilot n is small; this proves the flow, not a result.*


## Mean feature by sleep stage (whole_head, usable segments)

| stage   |   n_seg |   rel_delta |   rel_theta |   rel_alpha |   DAR |   TAR |   Q_SLOWING |   SEF95 |
|:--------|--------:|------------:|------------:|------------:|------:|------:|------------:|--------:|
| W       |     868 |       0.34  |       0.15  |       0.113 | 1.271 | 0.312 |       0.58  |  26.368 |
| N1      |     380 |       0.337 |       0.182 |       0.113 | 1.194 | 0.543 |       0.595 |  27.107 |
| N2      |     261 |       0.457 |       0.161 |       0.102 | 1.569 | 0.502 |       0.679 |  17.888 |
| N3      |      31 |       0.505 |       0.138 |       0.06  | 2.125 | 0.846 |       0.756 |  17.957 |
| REM     |     101 |       0.306 |       0.155 |       0.133 | 0.871 | 0.141 |       0.506 |  25.101 |


_Van Putten metrics (`Q_SLOWING`, `SEF95`) and our features (`rel_delta`, `DAR`, `TAR`) all present per segment; stage is the Morgoth per-segment call. This is exactly the input the GAMLSS norms consume (feature ~ age × stage × region)._
