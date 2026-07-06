# Flip-augmented lateralizer (L/R mirror = negate signed asymmetry)

Focal-lateralized n=2926 (58% left — a 1.4:1 prior).

|                                |   auroc |   bacc |   recall_left |   recall_right |
|:-------------------------------|--------:|-------:|--------------:|---------------:|
| baseline (intercept, no-aug)   |   0.866 |  0.785 |         0.878 |          0.691 |
| flip-augmented (antisymmetric) |   0.866 |  0.789 |         0.794 |          0.784 |


- Flip-consistency |p(left|x)+p(left|-x)-1| = 0.0000 (≈0 ⇒ predictions driven by genuine asymmetry, not a left prior — this is also the sign-convention audit).


**Takeaway:** augmentation equalizes left/right recall (removes the majority-class bias) while holding AUROC; the antisymmetric (no-intercept) model is the analytic equivalent. Adopt for training + as test-time augmentation.
