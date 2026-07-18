# Per-region slowing detection (one-vs-normal)

For each region: AUROC separating recordings with slowing in that region from normal controls, using that region's age-adjusted slowing deviation (independent of other regions).

| region    |   n_pos |   auroc |      lo |      hi |
|:----------|--------:|--------:|--------:|--------:|
| temporal  |    1844 |   0.662 |   0.647 |   0.676 |
| frontal   |     409 |   0.669 |   0.641 |   0.696 |
| central   |     239 |   0.692 |   0.658 |   0.729 |
| parietal  |       4 | nan     | nan     | nan     |
| occipital |       6 | nan     | nan     | nan     |


_This is the clinically natural 'can we see region-X slowing at all?' question; unlike the Each region is scored independently of the others; there is no forced-choice classification. 