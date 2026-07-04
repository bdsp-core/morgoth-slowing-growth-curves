# Gated lateralization — LEFT vs RIGHT among focal recordings with a stated side

n = 555 (left 408, right 147). Bilateral & generalized excluded.


## Single signed-asymmetry features (AUROC for left-vs-right)

- asym_temporal_delta: AUROC 0.856
- asym_parasagittal_delta: AUROC 0.801
- asym_temporal_theta: AUROC 0.822

## Supervised LR on all signed asymmetries (5-fold OOF)

- **AUROC (left vs right) = 0.866**

- accuracy 0.813, balanced accuracy 0.807

- confusion (rows=true L/R, cols=pred L/R):

```
        pred L  pred R
true L     334      74
true R      30     117
```


_Contrast: the ungated 3-way side eval (all abnormals incl. bilateral generalized) gave left/right F1 0.35/0.24 — an artifact of the bilateral majority. Gating to focal + binary L/R is the correct, clinically-posed task._
