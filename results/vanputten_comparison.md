# Comparison vs prior quantitative-slowing methods (van Putten lineage)

AUROC vs the clinical report label. Raw metrics use no age/sex/stage normalization (as clinically applied); our versions are age/sex-normed deviations of the same quantities.

| method                        |   abnormal |   focal |   generalized |
|:------------------------------|-----------:|--------:|--------------:|
| van Putten DAR                |      0.598 |   0.614 |         0.59  |
| van Putten DTABR              |      0.616 |   0.635 |         0.607 |
| van Putten BSI                |      0.631 |   0.775 |         0.561 |
| ours: DAR deviation (age/sex) |      0.62  |   0.659 |         0.602 |
| ours: |temporal asym| dev     |      0.53  |   0.646 |         0.526 |
| ours: BSI deviation (age/sex) |    nan     | nan     |       nan     |
| Morgoth p_abnormal            |      0.836 |   0.957 |         0.778 |
| Morgoth p_focal               |      0.725 |   0.93  |         0.627 |


_DAR/DTABR are global-slowing severity metrics (abnormal/generalized); BSI is an asymmetry metric (focal). References: van Putten 2004/2007 (BSI); Finnigan & van Putten 2013 (DAR, (δ+θ)/(α+β)). BSI is unsigned (detects asymmetry, not side) — our signed asymmetry adds lateralization on top._
