# LR-on-deviations vs Morgoth
n=12379, 97 age/sex-adjusted feature@region deviations.

## vs Morgoth **p_abnormal**
- Discrimination vs clinical label: **our-LR AUC 0.965** | Morgoth AUC 0.921
- Agreement of probabilities: **Pearson r=0.696**, Spearman ρ=0.691
- Distillation (our features → Morgoth prob): **R²=0.468**

## vs Morgoth **p_slowing**
- Discrimination vs clinical label: **our-LR AUC 0.965** | Morgoth AUC 0.936
- Agreement of probabilities: **Pearson r=0.634**, Spearman ρ=0.692
- Distillation (our features → Morgoth prob): **R²=0.467**

## Interpretation
- **Agreement with Morgoth's (expert-calibrated) probabilities is moderate-to-good: r≈0.63–0.70,
  distillation R²≈0.47.** Our simple objective deviation features (spectral band-power deviations +
  asymmetry + prevalence/persistence) are a solid proxy for the expert-aligned Morgoth score, but
  Morgoth carries ~half its probability variance beyond what these features explain (morphology,
  temporal/spatial pattern) — consistent with our features being deliberately basic.
- **Caveat on the 0.965 label-AUC:** this is *not* a fair "beats Morgoth" — the dataset label
  (normal/focal/general folders) is JJ's spectral-informed curation, so our spectral features align
  with it by construction, and the descriptive prevalence/burden features are partly circular with
  "slowing present." The robust cross-check is the **probability agreement (r/R²) vs Morgoth**, above.
- **Takeaway (face validity):** an objective LR on our deviations tracks the expert-calibrated detector
  reasonably; disagreements concentrate where morphology matters — a target for richer features.
