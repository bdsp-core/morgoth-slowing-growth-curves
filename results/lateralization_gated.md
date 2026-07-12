# Gated lateralization — LEFT vs RIGHT among focal recordings with a stated side

n = 2691 (left 1619, right 1072). Bilateral & generalized excluded.


## Single signed-asymmetry features (AUROC for left-vs-right)

- asym_temporal_delta: AUROC 0.869
- asym_parasagittal_delta: AUROC 0.843
- asym_temporal_theta: AUROC 0.770

## Supervised LR on all signed asymmetries (5-fold OOF)

- **AUROC (left vs right) = 0.892**

- accuracy 0.817, balanced accuracy 0.816

- confusion (rows=true L/R, cols=pred L/R):

```
        pred L  pred R
true L    1330     289
true R     204     868
```


_Contrast: the ungated 3-way side eval (all abnormals incl. bilateral generalized) gave left/right F1 0.35/0.24 — an artifact of the bilateral majority. Gating to focal + binary L/R is the correct, clinically-posed task._
