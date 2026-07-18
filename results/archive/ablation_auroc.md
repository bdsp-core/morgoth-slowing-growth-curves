# AUROC ablation — attributing the headline detection move (audit §1)

Primary cell: stage **W**, whole_head, **TAR**; positives = pathologic generalized slowing, negatives = clean_normal; `clean_pair` only.

Manuscript (old legacy data + old labels): **0.848**.

| labels                           | artifact_segments   | source      |   AUROC (W, whole_head, TAR) |   n_pos |   n_neg |
|:---------------------------------|:--------------------|:------------|-----------------------------:|--------:|--------:|
| contaminated (has_gen_slow)      | dropped (new)       | pooled      |                        0.655 |    6573 |    6698 |
| contaminated (has_gen_slow)      | dropped (new)       | cohort-only |                        0.633 |    5271 |    6105 |
| contaminated (has_gen_slow)      | KEPT (old-like)     | pooled      |                        0.596 |    6665 |    6761 |
| contaminated (has_gen_slow)      | KEPT (old-like)     | cohort-only |                        0.57  |    5335 |    6151 |
| CORRECTED (named-as-abnormality) | dropped (new)       | pooled      |                        0.766 |    3182 |    6698 |
| CORRECTED (named-as-abnormality) | dropped (new)       | cohort-only |                        0.756 |    2208 |    6105 |
| CORRECTED (named-as-abnormality) | KEPT (old-like)     | pooled      |                        0.649 |    3264 |    6761 |
| CORRECTED (named-as-abnormality) | KEPT (old-like)     | cohort-only |                        0.62  |    2262 |    6151 |

**Not ablatable here:** the θ band edge (4–7 → 4–8 Hz) is baked into the PSD features at fleet time; toggling it requires re-running the fleet. It remains an un-attributed term.
