# Detection is robust to the borrowed-report bug

`EEGs_And_Reports.csv` broadcasts one report across up to 170 EEGs of the same patient (scripts/88).
17.2% of routine recordings therefore carry text describing a *different* study of that patient, and
`labels_unified` absorbs that text through the `text_abnormal` / `foc_text` terms of
`scripts/60_build_unified_labels.py:123`.

Re-running the primary detection analysis on cleanly-paired recordings only (`CLEAN_PAIR=1`):

| stage | feature | AUROC (all) | AUROC (clean pairs) |
|---|---|---|---|
| W   | TAR       | 0.848 [0.83,0.86] | 0.847 [0.84,0.86] |
| N1  | log_delta | 0.875 [0.86,0.89] | 0.872 [0.86,0.88] |
| N2  | DAR       | 0.791 [0.78,0.80] | 0.787 [0.77,0.80] |
| N3  | DAR       | 0.758 [0.73,0.78] | 0.749 [0.72,0.77] |
| REM | TAR/log_delta | 0.825 [0.81,0.84] | 0.830 [0.82,0.84] |

positives 3,883 -> 3,052; held-out routine-normal negatives 1,451 -> 1,433.

**Every shift is inside the bootstrap CI.** The reason is structural: a borrowed report belongs to the *same
patient*, and abnormal-vs-normal status is highly stable across a patient's studies, so the binary label
usually survives the swap. Severity does not survive it, because severity genuinely varies study to study —
which is precisely the asymmetry observed (severity rho ~= 0.05, unchanged by clean-pair filtering).

Note that abnormals are preferentially affected (21% of positives dropped vs 9% of recordings): patients with
abnormal EEGs are restudied more often, so they have more sibling reports to borrow from.
