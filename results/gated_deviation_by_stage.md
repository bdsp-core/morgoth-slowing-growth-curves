# Figure 4 / Table 2 — how much slowing, in the recordings Morgoth says have slowing

The previous version of this figure reported the normative deviation as a **standalone detector** (AUROC vs the report label, per stage). That is not how the deviation is meant to be used, and we never intend to report slowing except where Morgoth has already decided there is slowing. The deviation is the **quantifier**, not the detector.

This figure groups recordings by **Morgoth's call** and shows, within each sleep stage, the distribution of normative deviation from normal. Because every recording is scored against **its own stage's** age-matched normal curve, the quantity stays interpretable in N2/N3 — where raw delta is uninformative because deep sleep is *supposed* to be slow.

Gate operating points, chosen by Youden J against the corrected report labels on the `clean_pair` set (labels pick the threshold only; they do not define the groups plotted): **p_focal ≥ 0.103**, **p_generalized ≥ 0.241**.

## Median deviation z

| gate_call            |     W |    N1 |    N2 |    N3 |   REM |
|:---------------------|------:|------:|------:|------:|------:|
| Morgoth: no slowing  | -0.19 | -0.19 | -0.13 | -0.1  | -0.17 |
| Morgoth: focal       |  0.68 |  0.64 |  0.41 |  0.23 |  0.55 |
| Morgoth: generalized |  0.77 |  1.06 |  0.63 |  0.34 |  0.77 |

## n recordings per cell

| gate_call            |     W |    N1 |   N2 |   N3 |   REM |
|:---------------------|------:|------:|-----:|-----:|------:|
| Morgoth: no slowing  | 12835 | 11531 | 9550 | 3314 | 10747 |
| Morgoth: focal       |  3682 |  3456 | 3258 | 2276 |  3031 |
| Morgoth: generalized |  9086 |  8302 | 8612 | 6145 |  6737 |

## The honest limit

**The gating here is per-RECORDING, not per-segment.** Morgoth's SLOWING head is a 3-class *per-window* head — `{0: Others, 1: Focal Slowing, 2: Generalized Slowing}` (`morgoth2/results_figures.py:2790`) — so per-segment focal and generalized probabilities *do* exist. Our fleet worker did not keep them: `scripts/31_segment_master_worker.py:162` collapses the window head to `p_slowing = 1 − class_0_prob` and discards `class_1_prob` / `class_2_prob`. The focal/generalized split we persisted comes from the separate **EEG-level** heads, which emit one probability per recording.

Recovering per-segment focal/generalized requires re-running Morgoth's SLOWING window head across the fleet and persisting all three class probabilities. Nothing on disk substitutes for it.
