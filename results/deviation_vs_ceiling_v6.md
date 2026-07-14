# Does the normative DEVIATION score meet the human ceiling? (v6)

The abstract claimed the deviation score *"after leave-one-out recalibration exceeded the average expert on balanced accuracy (0.835 vs 0.809)"*. That figure came from the **legacy** run, and it was a claim about **generalized** slowing. Table 5 / P7 re-tested the **gate** on v6 and falsified it — but the gate and the deviation score are different objects, so P7 did not settle this claim.

Both sides are scored the same way. Each **expert** is graded against the majority of the *other* 17 (nobody is graded against a consensus they helped define). The **machine** uses the sparse score `S` with coefficients frozen on the in-cohort data (these 100 EEGs informed nothing) and a threshold chosen leave-one-EEG-out.

| axis | positives/n | deviation S — balanced acc | expert ceiling | S sens @ expert spec | expert sens | verdict |
|---|---|---|---|---|---|---|
| focal | 12/100 | **0.794** | 0.795 | 0.750 | nan | **BELOW** |
| generalized | 18/100 | **0.853** | 0.809 | 0.556 | 0.735 | **MEETS/EXCEEDS** |

## Verdict — the claim is axis-specific, and it survives where it was made

**Generalized slowing: the claim HOLDS on v6.** Balanced accuracy **0.853** against an expert ceiling of 0.809 — the legacy figure was 0.835 vs 0.809, so the result is reproduced and slightly stronger. The abstract's honest caveat also reproduces almost exactly: at the experts' own specificity, S reaches sensitivity 0.556 versus the experts' 0.735 — it beats them on the balanced operating point, not at theirs.

**Focal slowing: the claim does NOT hold.** Balanced accuracy 0.794 against a ceiling of 0.795. The abstract never claimed focal, and it must not start.

This is consistent with P7 (the **gate**) being falsified: ranking and thresholding are different claims. The score **out-ranks** the experts on both axes (AUROC 0.910 generalized, 0.879 focal) and tracks **how many** experts saw the slowing (Spearman rho ~0.62), but only for generalized slowing does it also beat them at a chosen threshold.
