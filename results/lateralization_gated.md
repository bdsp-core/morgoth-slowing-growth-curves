# Gated lateralization — LEFT vs RIGHT among focal recordings with a stated side

n = 2049 (left 1229, right 820). Bilateral & generalized excluded.


## Single signed-asymmetry features (AUROC for left-vs-right)

- asym_temporal_delta: AUROC 0.844
- asym_parasagittal_delta: AUROC 0.825
- asym_temporal_theta: AUROC 0.774

## Supervised LR on all signed asymmetries (5-fold OOF)

- **AUROC (left vs right) = 0.904**

- accuracy 0.832, balanced accuracy 0.830

- confusion (rows=true L/R, cols=pred L/R):

```
        pred L  pred R
true L    1033     196
true R     148     672
```


_Contrast: the ungated 3-way side eval (all abnormals incl. bilateral generalized) gave left/right F1 0.35/0.24 — an artifact of the bilateral majority. Gating to focal + binary L/R is the correct, clinically-posed task._
