# Gated describe — the anterior/posterior gradient for generalized slowing

AP = S(anterior chain) − S(posterior chain), S = the wake-fit amount direction applied to each channel's age/stage-normed z. Normal 5th/95th centile: [-1.49, +1.64].

## Does AP recover the report's anterior/posterior call?

On pathologic-generalized recordings with a stated topography (anterior n=500, posterior n=408):
- **AP vs report anterior-vs-posterior: AUROC 0.604 [0.568, 0.642]**
- median AP: report-anterior **+0.19**, report-posterior **-0.37**

## Call distribution by group

| group | anterior | diffuse | posterior |
|---|---|---|---|
| clean-normal | 5.0% | 90.0% | 5.0% |
| pathologic-generalized | 3.7% | 93.1% | 3.2% |

Clean-normals should be ~90% diffuse by construction (5%/5% tails). The generalized group should show more anterior/posterior predominance if AP carries topographic signal.

## Consistency (enforced structurally)

- **generalized** branch emits: AP gradient (anterior/posterior/diffuse), band, prevalence, persistence, stage-accentuation.
- **focal** branch emits: side, region, band, prevalence, persistence, stage-accentuation.
- Neither emits a non-slowing feature; all descriptors are functionals of the slowing axes.
