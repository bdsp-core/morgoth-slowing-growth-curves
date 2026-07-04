# Region localization — supervised classifier vs baselines

Abnormal recordings with a report region, n=3525. Features: age-band-adjusted per-channel slowing deviations (18 ch x 4 metrics). 5-fold OOF multinomial LR (balanced).


## Headline comparison

| approach | accuracy | macro-F1 |
|---|---|---|
| temporal-default (majority) | 0.694 | 0.164 |
| argmax-deviation lobe (scripts/37) | 0.162 | 0.115 |
| **supervised LR (this)** | **0.376** | **0.234** |

_Accuracy favors the majority-default (temporal ~69%); **macro-F1 is the honest metric** (equal weight per region) — the default scores ~0.16 there because it never predicts the other four regions._


## Supervised per-region metrics

| region    |   precision |   recall |    f1 |    n |
|:----------|------------:|---------:|------:|-----:|
| frontal   |       0.31  |    0.337 | 0.323 |  691 |
| temporal  |       0.814 |    0.402 | 0.538 | 2445 |
| central   |       0.117 |    0.281 | 0.165 |  256 |
| parietal  |       0.032 |    0.212 | 0.056 |   66 |
| occipital |       0.049 |    0.373 | 0.086 |   67 |
