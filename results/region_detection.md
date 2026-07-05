# Per-region slowing detection (one-vs-normal)

For each region: AUROC separating recordings with slowing in that region from normal controls, using that region's age-adjusted slowing deviation (independent of other regions).

| region    |   n_pos |   auroc |    lo |    hi |
|:----------|--------:|--------:|------:|------:|
| temporal  |    2288 |   0.711 | 0.699 | 0.723 |
| frontal   |     570 |   0.665 | 0.643 | 0.688 |
| central   |     313 |   0.663 | 0.637 | 0.691 |
| parietal  |     116 |   0.745 | 0.7   | 0.784 |
| occipital |     135 |   0.761 | 0.721 | 0.799 |


_This is the clinically natural 'can we see region-X slowing at all?' question; unlike the multi-class lobe confusion it is not swamped by temporal predominance._
