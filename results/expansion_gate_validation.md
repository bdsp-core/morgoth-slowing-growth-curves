# Expansion gate validation (n=9 recordings with gate probs)

Label mix: {'focal_slow': 7, 'general_slow': 1, 'normal': 1}

**Preliminary** — strengthens as the balanced set grows.

## Mean gate probability by report label

| label        |   normal_head_prob |   p_focal |   p_generalized |
|:-------------|-------------------:|----------:|----------------:|
| focal_slow   |              0.981 |     0.309 |           0.397 |
| general_slow |              0.992 |     0.06  |           0.328 |
| normal       |              0.668 |     0.118 |           0.271 |

## Expected orderings (contrast AUC where both classes present)

- P(abnormal): abnormal > normal: AUC=1.00 ✅
- p_focal: focal > non-focal: AUC=0.93 ✅
- p_generalized: gen > non-gen: AUC=0.38 ⚠️

(AUC ≥ 0.6 = expected direction with useful separation; ~ = weak/underpowered; ⚠️ = wrong direction — revisit if it persists with more data.)


Note: many report-labeled recordings carry BOTH focal and generalized flags, so the focal-vs-gen contrast is inherently soft; P(abnormal) is the cleanest check.
