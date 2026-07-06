# LR-on-deviations vs Morgoth
n=12379, 97 age/sex-adjusted feature@region deviations.

## vs Morgoth **p_abnormal**
- Discrimination vs clinical label: **our-LR AUC 0.909** | Morgoth AUC 0.923
- Agreement of probabilities: **Pearson r=0.720**, Spearman ρ=0.723
- Distillation (our features → Morgoth prob): **R²=0.459**

## vs Morgoth **p_slowing**
- Discrimination vs clinical label: **our-LR AUC 0.909** | Morgoth AUC 0.910
- Agreement of probabilities: **Pearson r=0.659**, Spearman ρ=0.722
- Distillation (our features → Morgoth prob): **R²=0.458**
