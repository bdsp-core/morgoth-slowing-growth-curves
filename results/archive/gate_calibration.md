# Morgoth gate calibration (SAP §4.7)

Cross-fitted by patient (5-fold GroupKFold) on 21,984 recordings (11,735 slowing-positive / 10,249 clean-normal), corrected SAP labels.

| map | AUROC | Brier | ECE |
|---|---|---|---|
| raw p_slowing | 0.881 | 0.1581 | 0.1114 |
| Platt | 0.877 | 0.1471 | 0.0645 |
| isotonic | 0.880 | 0.1366 | 0.0036 |

**AUROC is identical across maps by construction** — calibration is monotonic, so it cannot change ranking. The Table 6 benchmark is therefore unaffected. What improves is the *meaning* of the probability: Brier 0.1581 → 0.1366 and the reliability curve. Operating-point claims (§7.1) and P7 must use the calibrated column (`p_isotonic`), stored alongside the raw one in `data/derived/gate_calibrated.parquet`.
