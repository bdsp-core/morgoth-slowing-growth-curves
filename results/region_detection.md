# Per-region slowing detection (one-vs-normal)

For each region: AUROC separating recordings with slowing in that region from normal controls, using that region's age-adjusted slowing deviation (independent of other regions).

| region    |   n_pos |   auroc |    lo |    hi |
|:----------|--------:|--------:|------:|------:|
| temporal  |    2445 |   0.716 | 0.701 | 0.729 |
| frontal   |     691 |   0.674 | 0.651 | 0.696 |
| central   |     256 |   0.659 | 0.628 | 0.691 |
| parietal  |      66 |   0.742 | 0.682 | 0.806 |
| occipital |      67 |   0.753 | 0.692 | 0.804 |


_This is the clinically natural 'can we see region-X slowing at all?' question; unlike the multi-class lobe confusion it is not swamped by temporal predominance._
