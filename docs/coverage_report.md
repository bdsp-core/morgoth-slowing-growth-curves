# Coverage report — report-labelled bins (clean usable set)

Source: `data/manifest/report_manifest_v1.parquet` filtered to `clean_pair & ~same_date_ambiguous`. Counts are EEGs (report labels). Cells < 50 are **under-powered** (backfill targets).


**Clean usable set: 9,733 EEGs** (of 12,379; excluded 2,124 borrowed + 554 same-date-ambiguous).

- abnormal 4,676 | focal 3,049 | generalized 7,643 | clean-normal 4,673


## 1. Age × class

| age_bin   |   abnormal |   normal |   focal |   generalized |
|:----------|-----------:|---------:|--------:|--------------:|
| 0-1       |         72 |       74 |      24 |            97 |
| 1-5       |        174 |      426 |      71 |           394 |
| 6-12      |        239 |      303 |     111 |           458 |
| 13-17     |        147 |      270 |      80 |           296 |
| 18-44     |        839 |     1627 |     543 |          1804 |
| 45-59     |        855 |      922 |     617 |          1377 |
| 60-74     |       1368 |      943 |     947 |          1948 |
| 75+       |        971 |      490 |     654 |          1256 |


## 2. FOCAL slowing — side × band

| focal_side   |   delta |   mixed |   theta |   All |
|:-------------|--------:|--------:|--------:|------:|
| bilateral    |      74 |     462 |      29 |   565 |
| left         |     272 |     906 |     103 |  1281 |
| right        |     197 |     644 |      79 |   920 |
| All          |     543 |    2012 |     211 |  2766 |


## 3. FOCAL slowing — region × band

| focal_region   |   delta |   mixed |   theta |   All |
|:---------------|--------:|--------:|--------:|------:|
| central        |      27 |      70 |      10 |   107 |
| frontal        |      49 |     149 |      17 |   215 |
| occipital      |      10 |      42 |       3 |    55 |
| parietal       |      17 |      60 |      10 |    87 |
| temporal       |     338 |    1168 |     136 |  1642 |
| All            |     441 |    1489 |     176 |  2106 |


## 4. FOCAL slowing — region × side

| focal_region   |   bilateral |   left |   right |   All |
|:---------------|------------:|-------:|--------:|------:|
| central        |          22 |     53 |      37 |   112 |
| frontal        |          49 |     75 |     102 |   226 |
| occipital      |          20 |     15 |      24 |    59 |
| parietal       |           8 |     40 |      40 |    88 |
| temporal       |         283 |    919 |     528 |  1730 |
| All            |         382 |   1102 |     731 |  2215 |


## 5. FOCAL slowing — age × side

| age_bin   |   bilateral |   left |   right |   All |
|:----------|------------:|-------:|--------:|------:|
| 0-1       |           6 |      9 |       5 |    20 |
| 1-5       |          11 |     32 |      25 |    68 |
| 6-12      |          31 |     48 |      31 |   110 |
| 13-17     |          17 |     24 |      31 |    72 |
| 18-44     |          82 |    255 |     189 |   526 |
| 45-59     |         123 |    262 |     217 |   602 |
| 60-74     |         208 |    425 |     295 |   928 |
| 75+       |         145 |    314 |     177 |   636 |
| All       |         623 |   1369 |     970 |  2962 |


## 6. GENERALIZED slowing — topography × band

| gen_topography   |   delta |   mixed |   theta |   All |
|:-----------------|--------:|--------:|--------:|------:|
| anterior         |      79 |     392 |      28 |   499 |
| posterior        |      89 |     425 |      85 |   599 |
| unspec           |     893 |    2863 |     922 |  4678 |
| All              |    1061 |    3680 |    1035 |  5776 |


## 7. GENERALIZED slowing — age × topography

| age_bin   |   anterior |   posterior |   unspec |   All |
|:----------|-----------:|------------:|---------:|------:|
| 0-1       |          4 |           9 |       84 |    97 |
| 1-5       |         12 |          44 |      338 |   394 |
| 6-12      |         19 |          73 |      366 |   458 |
| 13-17     |         12 |          35 |      249 |   296 |
| 18-44     |        110 |         153 |     1541 |  1804 |
| 45-59     |         97 |         125 |     1155 |  1377 |
| 60-74     |        164 |         168 |     1616 |  1948 |
| 75+       |        116 |         118 |     1022 |  1256 |
| All       |        534 |         725 |     6371 |  7630 |


## 8. Under-powered cells (< 50 EEGs) — backfill targets

| crosstab          | cell              |   n |
|:------------------|:------------------|----:|
| focal region×band | occipital × theta |   3 |
| focal region×band | central × theta   |  10 |
| focal region×band | occipital × delta |  10 |
| focal region×band | parietal × theta  |  10 |
| focal region×band | frontal × theta   |  17 |
| focal region×band | parietal × delta  |  17 |
| focal region×band | central × delta   |  27 |
| gen topo×band     | anterior × theta  |  28 |
| focal side×band   | bilateral × theta |  29 |
| focal region×band | occipital × mixed |  42 |
| focal region×band | frontal × delta   |  49 |
