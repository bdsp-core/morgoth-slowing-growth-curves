# Flip-augmented lateralizer (L/R mirror = negate signed asymmetry)

Focal-lateralized n=555 (74% left — a 2.8:1 prior).

|                                |   auroc |   bacc |   recall_left |   recall_right |
|:-------------------------------|--------:|-------:|--------------:|---------------:|
| baseline (intercept, no-aug)   |   0.867 |  0.706 |         0.895 |          0.517 |
| flip-augmented (antisymmetric) |   0.867 |  0.84  |         0.797 |          0.884 |


- Flip-consistency |p(left|x)+p(left|-x)-1| = 0.0000 (≈0 ⇒ predictions driven by genuine asymmetry, not a left prior — this is also the sign-convention audit).


**Takeaway:** augmentation equalizes left/right recall (removes the majority-class bias) while holding AUROC; the antisymmetric (no-intercept) model is the analytic equivalent. Adopt for training + as test-time augmentation.
