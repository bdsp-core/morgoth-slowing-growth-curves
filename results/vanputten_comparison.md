# Comparison vs prior quantitative-slowing methods (van Putten lineage)

AUROC vs the clinical report label. Raw metrics use no age/sex/stage normalization (as clinically applied); our versions are age/sex-normed deviations of the same quantities.

| method                        |   abnormal |   focal |   generalized |
|:------------------------------|-----------:|--------:|--------------:|
| van Putten DAR                |      0.676 |   0.642 |         0.757 |
| van Putten DTABR              |      0.678 |   0.649 |         0.745 |
| van Putten BSI                |      0.74  |   0.773 |         0.663 |
| ours: DAR deviation (age/sex) |      0.713 |   0.678 |         0.795 |
| ours: |temporal asym| dev     |      0.58  |   0.631 |         0.542 |
| ours: BSI deviation (age/sex) |    nan     | nan     |       nan     |
| Morgoth p_abnormal            |      0.954 |   0.946 |         0.971 |
| Morgoth p_focal               |      0.818 |   0.889 |         0.652 |


_DAR/DTABR are global-slowing severity metrics (abnormal/generalized); BSI is an asymmetry metric (focal). References: van Putten 2004/2007 (BSI); Finnigan & van Putten 2013 (DAR, (δ+θ)/(α+β)). BSI is unsigned (detects asymmetry, not side) — our signed asymmetry adds lateralization on top._
