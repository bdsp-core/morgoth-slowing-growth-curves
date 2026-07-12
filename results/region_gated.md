# Gated region localization (split by slowing type)


## (A) FOCAL-only lobe localization (n=2423) — acc 0.527, macro-F1 0.252

| region    |   precision |   recall |    f1 |    n |
|:----------|------------:|---------:|------:|-----:|
| temporal  |       0.859 |    0.574 | 0.688 | 1778 |
| frontal   |       0.252 |    0.398 | 0.309 |  399 |
| central   |       0.192 |    0.415 | 0.262 |  236 |
| parietal  |       0     |    0     | 0     |    4 |
| occipital |       0     |    0     | 0     |    6 |


## (B) GENERALIZED: anterior (FIRDA-like) vs posterior (OIRDA-like) predominance

- n=358 (anterior/frontal 184, posterior 174)

- anterior-minus-posterior delta gradient: AUROC **0.548**

- supervised LR on channel deviations: AUROC **0.607**


_For generalized slowing, side is undefined but A-P predominance is a real, reportable axis (frontal-predominant vs posterior-predominant intermittent rhythmic delta)._
