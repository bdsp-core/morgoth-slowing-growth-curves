# Region / side identification vs clinical reports


## Region (n=407 with region stated by both) — accuracy **0.916**

| region    |   precision |   recall |    f1 |   n |
|:----------|------------:|---------:|------:|----:|
| frontal   |       0     |        0 | 0     |  23 |
| temporal  |       0.916 |        1 | 0.956 | 373 |
| central   |       0     |        0 | 0     |   2 |
| parietal  |       0     |        0 | 0     |   6 |
| occipital |       0     |        0 | 0     |   3 |


## Side (n=5406) — accuracy **0.785**

| side      |   precision |   recall |    f1 |    n |
|:----------|------------:|---------:|------:|-----:|
| left      |       0.405 |    0.307 | 0.349 |  668 |
| right     |       0.2   |    0.293 | 0.238 |  242 |
| bilateral |       0.873 |    0.882 | 0.877 | 4496 |


_Note: comparison is limited to recordings where both our statement and the report explicitly state a location; region is the sparser of the two. Expands with the ingestion._
