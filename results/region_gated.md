# Gated region localization (split by slowing type)


## (A) FOCAL-only lobe localization (n=2779) — acc 0.364, macro-F1 0.216

| region    |   precision |   recall |    f1 |    n |
|:----------|------------:|---------:|------:|-----:|
| temporal  |       0.877 |    0.389 | 0.539 | 2157 |
| frontal   |       0.151 |    0.275 | 0.195 |  280 |
| central   |       0.09  |    0.264 | 0.134 |  148 |
| parietal  |       0.074 |    0.276 | 0.117 |  105 |
| occipital |       0.056 |    0.303 | 0.094 |   89 |


## (B) GENERALIZED: anterior (FIRDA-like) vs posterior (OIRDA-like) predominance

- n=192 (anterior/frontal 172, posterior 20)

- anterior-minus-posterior delta gradient: AUROC **0.612**

- supervised LR on channel deviations: AUROC **0.852**


_For generalized slowing, side is undefined but A-P predominance is a real, reportable axis (frontal-predominant vs posterior-predominant intermittent rhythmic delta)._
