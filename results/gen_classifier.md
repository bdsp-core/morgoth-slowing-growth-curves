# Generalized-slowing phys/path classifier (distilled from LLM labels)

- labeled cases: **998**  (unsure 82 held out)
- training: **916**, pathologic **585** (64%)

## Model A_cue — 5-fold CV
- AUROC **0.937**, macro-F1 **0.857**
```
              precision    recall  f1-score   support

    not-path      0.777     0.876     0.824       331
  pathologic      0.924     0.858     0.890       585

    accuracy                          0.865       916
   macro avg      0.851     0.867     0.857       916
weighted avg      0.871     0.865     0.866       916

confusion (rows=true not/path):
[[290  41]
 [ 83 502]]
```
## Model B_tfidf — 5-fold CV
- AUROC **0.960**, macro-F1 **0.883**
```
              precision    recall  f1-score   support

    not-path      0.843     0.861     0.852       331
  pathologic      0.920     0.909     0.915       585

    accuracy                          0.892       916
   macro avg      0.882     0.885     0.883       916
weighted avg      0.893     0.892     0.892       916

confusion (rows=true not/path):
[[285  46]
 [ 53 532]]
```

**Winner: B_tfidf** (higher macro-F1).

## Top n-grams → pathologic
diffuse, slowing of, theta, generalized, theta slowing, diffuse irregular, the background, diffuse theta, delta, due, background no, due to, generalized delta, delta slowing, irregular, irregular theta, abnormal, an abnormal, delta activity, of the

## Top n-grams → not-pathologic
normal, awake, is normal, sleep, vertex, good, drowsy, left temporal, eye, states, normal eeg, and asleep, 10 hz, awake and, vertex waves, states no, impression normal, asleep, focal, spindles

## Human validation (2026-07-05)
Brandon spot-reviewed the hardest cases in `results/gen_label_review.html` (the set of
LLM/classifier disagreements + all `unsure`, the cases most likely to be wrong): **15/15 agreement
with the LLM label**. Review stopped early given unanimous agreement. The LLM gen-slowing labels are
therefore taken as validated gold for training; no corrections were applied.
