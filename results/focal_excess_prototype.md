# Prototype — one slowing-amount direction, applied regionally

`w` is learned ONCE, on whole-head z's, clean-normal vs any pathologic slowing (nested-ish 5-fold AUROC **0.837**, split on patient). It is the direction of 'how much slowing is here'. It is then applied region by region, unchanged.

**Retained (6 of 10):** `log_delta@N1` (+0.72), `TAR@W` (+0.68), `log_theta@N1` (+0.18), `TAR@N1` (+0.14), `log_delta@W` (-0.14), `rel_delta@N1` (+0.09)


## The decisive test: exclusively-focal vs generalized-only

n = 1155 exclusively-focal vs 1555 generalized-only.

| score | what it is | AUROC [95% CI] |
|---|---|---|
| S_amount(whole_head) | global slowing amount (should be ~chance or worse) | 0.183 [0.167, 0.200] |
| max lobar amount | absolute lobar deviation (what S(focal) used) | 0.215 [0.196, 0.232] |
| **max background excess** | z_lobe − z_whole_head, invariant to global level | 0.692 [0.673, 0.711] |
| **max asymmetry excess** | z_lobe − z_contralateral, invariant to global level | 0.632 [0.611, 0.653] |

The trained focal detector scored **0.477 (chance)** on this contrast (`results/sparse_slowing_score.md`).

## Localization needs no labels

- argmax of background excess picks the reported **side** correctly in **79.4%** of 2268 lateralized focal recordings (chance 50%).
- the signed temporal asymmetry (L − R) discriminates reported-left from reported-right at **AUROC 0.881** [0.867, 0.895] — a *measurement*, fit to nothing.
- where the argmax lands, overall: L_temporal 34%, L_parasagittal 23%, R_temporal 22%, R_parasagittal 21%
