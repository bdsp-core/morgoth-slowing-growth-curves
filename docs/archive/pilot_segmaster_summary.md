# Pilot segment_master summary (plumbing proof — new per-channel schema)

Source: `segment_master` (per eeg_id×segment×channel) + `segment_summary` — **111 EEGs**, 1,069,056 channel-rows. Regions DERIVED via `canonical.to_regions`. *Pilot n is small; this proves the flow, not a result.*


## Mean feature by sleep stage (whole_head region, usable segments)

| stage   |   n_seg |   rel_delta |   rel_theta |   rel_alpha |   log_DAR |   log_TAR |   Q_SLOWING |   p_slowing |
|:--------|--------:|------------:|------------:|------------:|----------:|----------:|------------:|------------:|
| W       |    8198 |       0.324 |       0.121 |       0.135 |     1.416 |     0.277 |       0.576 |       0.367 |
| N1      |    4415 |       0.39  |       0.165 |       0.084 |     1.882 |     0.888 |       0.681 |       0.671 |
| N2      |   13310 |       0.407 |       0.1   |       0.054 |     2.346 |     0.706 |       0.704 |       0.778 |
| N3      |   14259 |       0.448 |       0.07  |       0.028 |     3.026 |     1.002 |       0.803 |       0.941 |
| REM     |    2249 |       0.394 |       0.156 |       0.092 |     1.78  |     0.727 |       0.693 |       0.413 |


_`rel_*`/`log_DAR`/`log_TAR` are region-averaged from the 18 channels; `Q_SLOWING`/`p_slowing` come from `segment_summary`. This is exactly the input GAMLSS norms consume (feature ~ age × stage × region), now with channel-level detail retained upstream._


## Ledger (recording_meta): 120 intended EEGs | included 89 | excluded 31. Exclusion reasons: {'unusable:short_or_artifact': np.int64(22), 'noedf:ambiguous:0of3': np.int64(2), 'noedf:ambiguous:0of6': np.int64(2), 'noedf:noedf': np.int64(1), 'noedf:ambiguous:0of7': np.int64(1), 'noedf:ambiguous:0of2': np.int64(1)}
