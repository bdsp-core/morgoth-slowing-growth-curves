# LR-on-deviations vs Morgoth
n=12379, 97 age/sex-adjusted feature@region deviations.

## vs Morgoth **p_abnormal**
- Discrimination vs clinical label: **our-LR AUC 0.962** | Morgoth AUC 0.921
- Agreement of probabilities: **Pearson r=0.693**, Spearman ρ=0.690
- Distillation (our features → Morgoth prob): **R²=0.456**

## vs Morgoth **p_slowing**
- Discrimination vs clinical label: **our-LR AUC 0.962** | Morgoth AUC 0.936
- Agreement of probabilities: **Pearson r=0.635**, Spearman ρ=0.694
- Distillation (our features → Morgoth prob): **R²=0.458**
