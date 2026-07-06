# Gated lateralization — LEFT vs RIGHT among focal recordings with a stated side

n = 2926 (left 1711, right 1215). Bilateral & generalized excluded.


## Single signed-asymmetry features (AUROC for left-vs-right)

- asym_temporal_delta: AUROC 0.820
- asym_parasagittal_delta: AUROC 0.801
- asym_temporal_theta: AUROC 0.750

## Supervised LR on all signed asymmetries (5-fold OOF)

- **AUROC (left vs right) = 0.887**

- accuracy 0.806, balanced accuracy 0.804

- confusion (rows=true L/R, cols=pred L/R):

```
        pred L  pred R
true L    1392     319
true R     250     965
```


_Contrast: the ungated 3-way side eval (all abnormals incl. bilateral generalized) gave left/right F1 0.35/0.24 — an artifact of the bilateral majority. Gating to focal + binary L/R is the correct, clinically-posed task._
