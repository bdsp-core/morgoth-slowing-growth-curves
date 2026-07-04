# Comparison vs prior quantitative-slowing methods (van Putten lineage)

AUROC vs the clinical report label. Raw metrics use no age/sex/stage normalization (as clinically applied); our versions are age/sex-normed deviations of the same quantities.

| method                        |   abnormal |   focal |   generalized |
|:------------------------------|-----------:|--------:|--------------:|
| van Putten DAR                |      0.65  |   0.594 |         0.672 |
| van Putten DTABR              |      0.659 |   0.611 |         0.678 |
| van Putten BSI                |      0.688 |   0.803 |         0.644 |
| ours: DAR deviation (age/sex) |      0.668 |   0.634 |         0.681 |
| ours: |temporal asym| dev     |      0.548 |   0.681 |         0.504 |
| ours: BSI deviation (age/sex) |      0.682 |   0.799 |         0.637 |
| Morgoth p_abnormal            |      0.929 |   0.963 |         0.916 |
| Morgoth p_focal               |      0.784 |   0.986 |         0.706 |


_DAR/DTABR are global-slowing severity metrics (abnormal/generalized); BSI is an asymmetry metric (focal). References: van Putten 2004/2007 (BSI); Finnigan & van Putten 2013 (DAR, (δ+θ)/(α+β)). BSI is unsigned (detects asymmetry, not side) — our signed asymmetry adds lateralization on top._
