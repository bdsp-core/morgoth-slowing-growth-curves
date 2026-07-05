# Per-region slowing detection (one-vs-normal)

For each region: AUROC separating recordings with slowing in that region from normal controls, using that region's age-adjusted slowing deviation (independent of other regions).

| region    |   n_pos |   auroc |    lo |    hi |
|:----------|--------:|--------:|------:|------:|
| temporal  |    2327 |   0.715 | 0.699 | 0.727 |
| frontal   |     514 |   0.668 | 0.643 | 0.693 |
| central   |     337 |   0.657 | 0.627 | 0.684 |
| parietal  |     128 |   0.764 | 0.721 | 0.803 |
| occipital |     116 |   0.768 | 0.724 | 0.811 |


_This is the clinically natural 'can we see region-X slowing at all?' question; unlike the multi-class lobe confusion it is not swamped by temporal predominance._
