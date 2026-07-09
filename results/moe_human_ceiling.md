# MoE — the between-rater human ceiling for slowing

Pooled over rounds r1–r3 (disjoint events; per ChenXi Sun the rounds are simply different EEGs, 
scored the same way). **BDSP events only** (`icare_*` cardiac-arrest events excluded: different 
population from our norms). Raters with ≥200 votes; pairs with ≥100 co-rated 
events. Raters anonymized; one rater is an author of this paper.

| category | raters | events | prevalence | Fleiss κ | pairwise Cohen κ median [95% CI] |
|---|---|---|---|---|---|
| focalslowing-delta | 21 | 1761 | 0.161 | 0.343 | **0.372** [0.343, 0.401] |
| focalslowing-theta | 21 | 1761 | 0.051 | 0.124 | **0.115** [0.071, 0.131] |
| focalslowing-alpha | 21 | 1761 | 0.005 | 0.053 | **-0.002** [-0.003, -0.001] |
| focalslowing-beta | 15 | 962 | 0.013 | -0.004 | **-0.002** [-0.006, 0.040] |
| genslowing-delta | 21 | 1761 | 0.389 | 0.280 | **0.270** [0.257, 0.293] |
| genslowing-theta | 21 | 1761 | 0.379 | 0.216 | **0.199** [0.179, 0.217] |
| genslowing-alpha | 21 | 1761 | 0.200 | 0.146 | **0.116** [0.095, 0.137] |
| genslowing-beta | 15 | 962 | 0.230 | 0.094 | **0.121** [0.091, 0.141] |
| ANY focalslowing | 21 | 1761 | 0.178 | 0.352 | **0.382** [0.351, 0.416] |
| ANY genslowing | 21 | 1761 | 0.637 | 0.356 | **0.255** [0.235, 0.276] |

## Band agreement, conditional on both raters calling slowing

Among events that **both** raters marked as slowing (any band), how often do they choose the 
same band? This is the direct analogue of our reported band agreement (0.74).

| kind | rater pairs | co-called events (median/pair) | exact band-set match | δ-vs-θ agreement |
|---|---|---|---|---|
| focalslowing | 153 | 65 | **0.541** | 0.576 |
| genslowing | 191 | 316 | **0.266** | 0.434 |
