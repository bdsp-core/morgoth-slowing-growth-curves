# Gated lateralization — LEFT vs RIGHT among focal recordings with a stated side

n = 1301 (left 785, right 516). Bilateral & generalized excluded.


## Single signed-asymmetry features (AUROC for left-vs-right)

- asym_temporal_delta: AUROC 0.882
- asym_parasagittal_delta: AUROC 0.856
- asym_temporal_theta: AUROC 0.828

## Supervised LR on all signed asymmetries (5-fold OOF)

- **AUROC (left vs right) = 0.932**

- accuracy 0.873, balanced accuracy 0.872

- confusion (rows=true L/R, cols=pred L/R):

```
        pred L  pred R
true L     688      97
true R      68     448
```


_Contrast: the ungated 3-way side eval (all abnormals incl. bilateral generalized) gave left/right F1 0.35/0.24 — an artifact of the bilateral majority. Gating to focal + binary L/R is the correct, clinically-posed task._
