# van Putten benchmark — segment_summary arms at FULL fleet coverage

Recomputed on **27,003** recordings (the committed table used only **3,130** — an incomplete `segment_summary` download, not a fleet gap; S3 has all 27,478).

Labels are the CORRECTED SAP labels (`label_rederive_sap.py`; physiologic generalized slowing is NOT a positive). AUROC [95% bootstrap CI].

| method                         | abnormal            | generalized         | focal               |   n_scored |
|:-------------------------------|:--------------------|:--------------------|:--------------------|-----------:|
| Q_SLOWING (raw) [vP2013]       | 0.654 [0.647–0.661] | 0.702 [0.694–0.71]  | 0.63 [0.623–0.637]  |      21984 |
| Q_APG (raw)                    | 0.649 [0.642–0.656] | 0.694 [0.686–0.702] | 0.622 [0.613–0.63]  |      21984 |
| r_sBSI (raw)                   | 0.698 [0.692–0.706] | 0.692 [0.684–0.701] | 0.726 [0.718–0.733] |      21984 |
| Q_ASYM (raw)                   | 0.684 [0.677–0.691] | 0.69 [0.682–0.698]  | 0.697 [0.689–0.704] |      21984 |
| Q_SLOWING (age-normed)         | 0.692 [0.684–0.699] | 0.751 [0.743–0.759] | 0.671 [0.663–0.679] |      21973 |
| r_sBSI (age-normed)            | 0.686 [0.68–0.693]  | 0.675 [0.665–0.684] | 0.715 [0.708–0.723] |      21973 |
| ** Morgoth p_slowing (gate) ** | 0.881 [0.876–0.885] | 0.918 [0.913–0.923] | 0.875 [0.87–0.881]  |      21984 |
