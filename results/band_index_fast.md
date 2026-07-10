# Band index — which feature recovers the report band word? (no 7–8 Hz fix yet)

2053 report-band-labelled recordings (clean-paired, W/N1): theta 1022, delta 1031. Band power uses the current theta = 4–7 Hz.

| band feature | AUROC vs report word [95% CI] |
|---|---|
| z_θ − z_δ (old, deprecated) | **0.625** [0.600, 0.650] |
| rel_θ − rel_δ | **0.639** [0.616, 0.662] |
| ΔP_θ / (|ΔP_δ|+|ΔP_θ|) — excess-power share | **0.479** [0.453, 0.505] |
| θ excess power ΔP_θ alone | **0.479** [0.454, 0.503] |
| z_θ alone | **0.440** [0.416, 0.465] |
| z_δ alone (expect < 0.5: delta→delta-word) | **0.395** [0.370, 0.419] |

Expert–expert ceiling for band (MoE, exact δ-vs-θ match): 0.576 focal / 0.434 generalized (`results/moe_band_vs_ours.md`). The 7–8 Hz edge fix is tested separately (scripts/109).
