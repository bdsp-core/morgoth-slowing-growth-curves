# Per-region slowing detection (one-vs-normal)

For each region: AUROC separating recordings with slowing in that region from normal controls, using that region's age-adjusted slowing deviation (independent of other regions).

| region    |   n_pos |   auroc |    lo |    hi |
|:----------|--------:|--------:|------:|------:|
| temporal  |    2415 |   0.705 | 0.693 | 0.718 |
| frontal   |     509 |   0.668 | 0.643 | 0.692 |
| central   |     244 |   0.696 | 0.663 | 0.733 |
| parietal  |     120 |   0.742 | 0.7   | 0.785 |
| occipital |     122 |   0.747 | 0.694 | 0.792 |


_This is the clinically natural 'can we see region-X slowing at all?' question; unlike the multi-class lobe confusion it is not swamped by temporal predominance._
