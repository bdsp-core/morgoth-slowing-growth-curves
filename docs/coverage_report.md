# Coverage report — report-labelled bins (cohort + backfill, 4-region)

Source: `data/manifest/report_manifest_v2.parquet` (merged cohort + pool backfill) filtered to `clean_pair & ~same_date_ambiguous`. Counts are EEGs (report labels). **Adequacy is judged on the MARGINALS** (region / side / band / topography / age — all ≥200); the few 3-way cells below 200 are **genuinely-rare findings** (whole-pool max <200), pooled in assessment — not sampling gaps.


**Clean usable set: 12,387 EEGs** (of 15,033; excluded 2,124 borrowed + 554 same-date-ambiguous).

- abnormal 7,056 | focal 4,802 | generalized 8,270 | clean-normal 4,813


## 0. Marginal adequacy — the criterion (all ≥200 = adequate)

- FOCAL region: temporal **1878** · posterior **841** · frontal **659** · central **463**

- FOCAL side: left **1907** · right **1502** · bilateral **1212**

- FOCAL band: mixed **2359** · delta **1164** · theta **926**

- GEN topography: unspec **6475** · posterior **1021** · anterior **774**

- GEN band: mixed **3698** · delta **1368** · theta **1268**


_All marginal minima ≥ 200: True (smallest = 463)._


## 1. Age × class

| age_bin   |   abnormal |   normal |   focal |   generalized |
|:----------|-----------:|---------:|--------:|--------------:|
| 0-1       |        308 |      261 |     169 |           188 |
| 1-5       |        318 |      426 |     166 |           443 |
| 6-12      |        472 |      303 |     301 |           501 |
| 13-17     |        292 |      357 |     183 |           338 |
| 18-44     |       1338 |     1627 |     927 |          1919 |
| 45-59     |       1226 |      922 |     895 |          1470 |
| 60-74     |       1818 |      943 |    1285 |          2060 |
| 75+       |       1273 |      490 |     874 |          1338 |


## 2. FOCAL slowing — side × band

| focal_side   |   delta |   mixed |   theta |   All |
|:-------------|--------:|--------:|--------:|------:|
| bilateral    |     295 |     557 |     280 |  1132 |
| left         |     442 |    1019 |     348 |  1809 |
| right        |     407 |     760 |     275 |  1442 |
| All          |    1144 |    2336 |     903 |  4383 |


## 3. FOCAL slowing — region × band

| focal_region   |   delta |   mixed |   theta |   All |
|:---------------|--------:|--------:|--------:|------:|
| central        |     107 |     279 |      63 |   449 |
| frontal        |     264 |     283 |      92 |   639 |
| posterior      |     249 |     307 |     246 |   802 |
| temporal       |     368 |    1054 |     355 |  1777 |
| All            |     988 |    1923 |     756 |  3667 |


## 4. FOCAL slowing — region × side

| focal_region   |   bilateral |   left |   right |   All |
|:---------------|------------:|-------:|--------:|------:|
| central        |         102 |    183 |     169 |   454 |
| frontal        |         132 |    259 |     261 |   652 |
| posterior      |         227 |    304 |     288 |   819 |
| temporal       |         322 |    949 |     591 |  1862 |
| All            |         783 |   1695 |    1309 |  3787 |


## 5. FOCAL slowing — age × side

| age_bin   |   bilateral |   left |   right |   All |
|:----------|------------:|-------:|--------:|------:|
| 0-1       |          49 |     25 |      23 |    97 |
| 1-5       |          52 |     60 |      45 |   157 |
| 6-12      |         135 |     94 |      66 |   295 |
| 13-17     |          55 |     60 |      53 |   168 |
| 18-44     |         199 |    382 |     323 |   904 |
| 45-59     |         194 |    363 |     323 |   880 |
| 60-74     |         312 |    535 |     416 |  1263 |
| 75+       |         216 |    386 |     253 |   855 |
| All       |        1212 |   1905 |    1502 |  4619 |


## 6. GENERALIZED slowing — topography × band

| gen_topography   |   delta |   mixed |   theta |   All |
|:-----------------|--------:|--------:|--------:|------:|
| anterior         |     250 |     393 |      94 |   737 |
| posterior        |     213 |     428 |     250 |   891 |
| unspec           |     905 |    2877 |     924 |  4706 |
| All              |    1368 |    3698 |    1268 |  6334 |


## 7. GENERALIZED slowing — age × topography

| age_bin   |   anterior |   posterior |   unspec |   All |
|:----------|-----------:|------------:|---------:|------:|
| 0-1       |          7 |          17 |      164 |   188 |
| 1-5       |         21 |          84 |      338 |   443 |
| 6-12      |         33 |         102 |      366 |   501 |
| 13-17     |         22 |          55 |      261 |   338 |
| 18-44     |        163 |         215 |     1541 |  1919 |
| 45-59     |        151 |         164 |     1155 |  1470 |
| 60-74     |        217 |         227 |     1616 |  2060 |
| 75+       |        160 |         156 |     1022 |  1338 |
| All       |        774 |        1020 |     6463 |  8257 |


## 8. Genuinely-rare 3-way cells (< 200) — pooled in assessment, not sampling gaps

| crosstab          | cell             |   n |
|:------------------|:-----------------|----:|
| focal region×band | central × theta  |  63 |
| focal region×band | frontal × theta  |  92 |
| gen topo×band     | anterior × theta |  94 |
| focal region×band | central × delta  | 107 |
