# Gated region localization (split by slowing type)


## (A) FOCAL-only lobe localization (n=1273) — acc 0.462, macro-F1 0.203

| region    |   precision |   recall |    f1 |    n |
|:----------|------------:|---------:|------:|-----:|
| temporal  |       0.872 |    0.501 | 0.636 | 1038 |
| frontal   |       0.171 |    0.342 | 0.228 |  149 |
| central   |       0.068 |    0.25  | 0.107 |   56 |
| parietal  |       0.026 |    0.13  | 0.043 |   23 |
| occipital |       0     |    0     | 0     |    7 |


## (B) GENERALIZED: anterior (FIRDA-like) vs posterior (OIRDA-like) predominance

- n=645 (anterior/frontal 542, posterior 103)

- anterior-minus-posterior delta gradient: AUROC **0.573**

- supervised LR on channel deviations: AUROC **0.658**


_For generalized slowing, side is undefined but A-P predominance is a real, reportable axis (frontal-predominant vs posterior-predominant intermittent rhythmic delta)._
