# Region localization — supervised classifier vs baselines

Abnormal recordings with a report region, n=3412. Features: age-band-adjusted per-channel slowing deviations (18 ch x 4 metrics). 5-fold OOF multinomial LR (balanced).


## Headline comparison

| approach | accuracy | macro-F1 |
|---|---|---|
| temporal-default (majority) | 0.708 | 0.166 |
| argmax-deviation lobe (scripts/37) | 0.162 | 0.115 |
| **supervised LR (this)** | **0.356** | **0.237** |

_Accuracy favors the majority-default (temporal ~69%); **macro-F1 is the honest metric** (equal weight per region) — the default scores ~0.16 there because it never predicts the other four regions._


## Supervised per-region metrics

| region    |   precision |   recall |    f1 |    n |
|:----------|------------:|---------:|------:|-----:|
| frontal   |       0.224 |    0.295 | 0.255 |  509 |
| temporal  |       0.813 |    0.379 | 0.517 | 2416 |
| central   |       0.137 |    0.298 | 0.188 |  245 |
| parietal  |       0.071 |    0.292 | 0.115 |  120 |
| occipital |       0.067 |    0.328 | 0.112 |  122 |
