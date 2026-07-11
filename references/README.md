# References — van Putten qEEG slowing/background metrics

Primary sources for the S7 benchmark (`docs/analysis_plan.md` §8.7). The metric definitions here are
taken **from these papers directly**, not from secondary summaries. The PDFs live in this folder locally
but are **gitignored** (copyrighted); only this README + `references.bib` are committed.

| file | citation | what we take from it |
|---|---|---|
| `The_revised_brain_symmetry_index.pdf` | van Putten, *Clin Neurophysiol* 118 (2007) 2362 | r-sBSI (power-based), r-tBSI (diffuse) |
| `Quantification_of_the_adult_EEG_backgrou.pdf` | Lodder & van Putten, *Clin Neurophysiol* 124 (2013) 228 | **Q_SLOWING, Q_APG, Q_ASYM, Q_REAC, Q_ALPHA** |
| `file.pdf` | Lodder, Askamp & van Putten, *PLoS ONE* (2014) "Computer-Assisted Interpretation of the EEG Background Pattern: A Clinical Evaluation" | validation-design precedent (IRR + automated-vs-consensus) |
| `circuitVis.pdf` | Anderson, Chong, Preston & Silva (Utah/Barrow), "Discovering and Visualizing Patterns in EEG Data" | **EEG visualization** paper — not a slowing metric; relevance TBD (flagged to MBW) |

## Exact metric definitions (as published)

### van Putten 2007 — revised BSI
- **r-sBSI** (revised spatial BSI, interhemispheric asymmetry), per epoch t:
  `r-sBSI = (1/K) Σ_n |R*_n − L*_n| / (R*_n + L*_n)`, where `R*_n = (1/M) Σ_ch a_n(ch)²` is the **mean
  squared** Fourier coefficient (i.e. **power**) over right-hemisphere channels at frequency n (L* likewise
  for left). Uses **squared** coefficients (power), giving ~2× the sensitivity of the 2004 amplitude BSI.
  Frequency range **0.5–25 Hz**; epoch T = 10 s. Baseline ≈0.07 (8 ch/hemisphere).
  → This is the correct definition of what our plan called `pBSI`. **Not** a per-homologous-pair mean.
- **r-tBSI** (revised temporal BSI, *diffuse* change vs a temporal reference t0):
  `r-tBSI = sqrt(|(ΔR − γ)(ΔL − γ)|)`, `ΔR = (1/K) Σ_n |R*_n(t) − R*_n(t0)|/(R*_n(t)+R*_n(t0))` (ΔL likewise),
  γ = offset (~0.07–0.14). Detects diffuse change **relative to a within-recording baseline** — designed for
  monitoring. For our cross-sectional, normative approach the "reference" is the age/stage-matched normal
  population, so r-tBSI is not adopted as-is; the normative deviation is its analogue. Noted, not computed.
- **pdBSI** (signed/directed): **our own extension**, NOT in van Putten — drop the absolute value in r-sBSI
  so the sign gives lateralization. Labelled as ours in the plan.

### Lodder & van Putten 2013 — five quantified background properties (validated vs reports, Fleiss κ)
Sampling 250 Hz, 19 ch 10–20, ICA eye-blink removal. **Q_SLOWING/Q_APG/Q_ASYM are the ones we adopt.**
- **Q_SLOWING = P_low / P_wide**, `P_low = power[2–8 Hz]`, `P_wide = power[2–25 Hz]` (mean spectrum over
  scalp). Abnormal (too much slowing) if **Q_SLOWING > 0.6** (i.e. <40% of power above 8 Hz).
  Report agreement **κ = 0.76** (their best; sens 0.78 / spec 0.98). **← the van Putten "slowing" metric.**
- **Q_APG = P_ant / (P_ant + P_pos)** on **alpha** power, eyes-closed, **Laplacian** montage. Normal <0.4,
  moderate 0.4–0.6, abnormal >0.6 (posterior→anterior shift). κ = 0.19. → adopt for generalized A–P.
- **Q_ASYM(c) = normalized spectral difference** per homologous pair c ∈ {Fp1,Fp2},{F7,F8},{F3,F4},
  {T3,T4},{C3,C4},{T5,T6},{P3,P4},{O1,O2}; asymmetry if any pair > 0.5. κ = 0.12. → adopt for focal/lateral.
- **Q_REAC = 1 − P_EO/P_EC** (occipital alpha, eyes-open vs eyes-closed). Substantial >0.5 / moderate /
  low <0.1. κ = 0.34. **State-dependent (needs EO/EC annotation)** — flagged: adopt only if we have reliable
  eyes-open/closed states.
- **Q_ALPHA = alpha (PDR) peak frequency** vs age norm (their Table 2: >51 yr 9.1±1.8 Hz, 16–50 9.9±1.8;
  deviant if |Δ|>1.8 Hz). κ = 0.60. **PDR grading was scoped OUT by MBW** (separate from slowing) — flagged
  for decision, not adopted by default.

## Relevance summary
Lodder & van Putten (2013) + the 2014 clinical evaluation are the **closest prior work to ours**: quantify
the background properties clinicians report, validate against reports/consensus by κ, and show automation
can match experts. Our advance over them: age/sex/**stage**-normed (they use fixed thresholds, wake-only,
single-site n=384), lifespan-continuous, per-segment whole-recording, at scale, with a foundation-model
gate. Their metrics — especially **Q_SLOWING** — are exactly what the S7 benchmark (and the P8b
adopt-if-better rule) must run head-to-head against ours.
