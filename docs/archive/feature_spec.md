> ⚠ **SUPERSEDED — historical only.** This doc asserts facts now overridden by `docs/analysis_plan.md` (the SAP) and `docs/claims_table.md` (e.g. theta = 4–8 Hz; severity adjectives / ACNS frequency words / band-from-our-features are FORBIDDEN output; artifact segments are flagged not stripped; zero reuse of prior derived tables). Do not implement from this file. Retained for provenance.

# Feature & Scoring Specification

This is the analytical framework for quantifying abnormal EEG slowing, transcribed and organized
from Dr. Jing's notes (`EEG Abnormality Quantification`). It is the source of truth for what
`src/morgoth_slowing/` implements. Notation: `t` = segment, `r` = channel/region, `b` = band,
`p` = homologous pair.

## 1. Reference model around features (not just a mean spectrum)

For each **state** (eyes-open wake, eyes-closed wake, drowsy wake, N1, N2, N3, REM), each
**region/electrode**, and each **band**, estimate norms as a function of **age (continuous) × sex**.
Use **log power**:

```
x_{t,r,b} = log ∫_b PSD_{t,r}(f) df
```

Store at least:

| Feature | Definition |
|---|---|
| Absolute delta | `Δ_abs = log P[0.5–4]` |
| Absolute theta | `Θ_abs = log P[4–7]` |
| Absolute low-freq | `LF_abs = log P[0.5–7]` |
| Relative delta | `Δ_rel = log( P[0.5–4] / P[0.5–30] )` |
| Relative theta | `Θ_rel = log( P[4–7] / P[0.5–30] )` |
| Delta/alpha ratio | `DAR = log( P[0.5–4] / P[8–13] )` |
| Theta/alpha ratio | `TAR = log( P[4–7] / P[8–13] )` |

Plus (recommended): median frequency, spectral edge frequency (SEF), alpha peak frequency,
low-frequency spectral AUC.

**Absolute vs relative matters.** Absolute delta can be high from amplitude, reference/montage,
breach, artifact, or true slowing. Relative power and ratios are cleaner indicators of a spectral
shift toward slower frequencies — report both, let a composite combine them.

**Estimate robustly:** medians/MADs, GAMs, GAMLSS, quantile regression, or empirical
percentile→z if non-Gaussian. **Age continuous**, not coarse-binned.

**Unit of analysis = subject, not segment.** Build segment-level norms, but validate patient-level
scores with leave-one-subject-out (LOSO) or subject-level bootstrap.

## 2. Segment-level abnormal slowing

Segment z-score:

```
z_{t,r,b} = ( x_{t,r,b} − μ_{age,state,r,b} ) / σ_{age,state,r,b}
```

Segment indicator: `I_{t,r}^Δ = 1[ z_{t,r}^Δ > τ ]`, with `τ` initially 2.0–2.5, ultimately
calibrated on held-out normal EEGs.

Combined theta/delta exceedance score (deviations below threshold don't cancel abnormal ones):

```
S_{t,r}^slow = sqrt( max(z^Δ − τ, 0)² + max(z^Θ − τ, 0)² )
```

Full-spectral version: `S_{t,r}^slow = (1/(7−0.5)) ∫_{0.5}^{7} max(z_{t,r}(f) − τ, 0) df`.

**Exceedance curve** (the "histogram of deviations" idea, made cumulative):
`E_{r,b}(τ) = Pr(z_{t,r,b} > τ)` for τ = 1..5. Distinguishes "many mildly abnormal" from "rare
severely abnormal" segments even at equal mean z.

## 3. Prevalence, severity, burden, persistence (per state/region/band)

```
Prevalence   Prev_{r,b} = Σ_t w_t·1[z>τ] / Σ_t w_t
Severity     Sev_{r,b}  = median( z_{t,r,b} | z_{t,r,b} > τ )     (or 90th/95th pct for peak)
Burden       Burden_{r,b} = Σ_t w_t·max(z_{t,r,b} − τ, 0) / Σ_t w_t
Persistence  LongestRun, MedianEpisodeDuration, NumberOfEpisodes
```

**Burden is the best single number** (combines prevalence + degree). Persistence separates "30
scattered abnormal segments" from "one 7.5-min continuous epoch".

ACNS-style prevalence words (borrowed from rhythmic/periodic terminology as a standardized scale):
**rare <1%, occasional 1–9%, frequent 10–49%, abundant 50–89%, continuous ≥90%**.

## 4. Patient-level "SD above normal"

Do **not** call a record abnormal merely because many segments have z>2 (expected by chance across
many segments). Instead build a **null distribution**: score every normal reference subject as if a
patient, against a model **excluding that subject** (LOSO), giving `Burden^norm_{r,b}`. Then:

```
Z^patient_{r,b} = ( Burden^patient − mean(Burden^norm) ) / sd(Burden^norm)
```

Better, empirical percentile→z (robust to non-Gaussian burden):

```
Z_eq^patient = Φ⁻¹( F_norm( Burden^patient ) )
```

→ *"The awake right temporal delta burden is 4.1 SD above the age/state-matched normal
distribution."*

## 5. Asymmetry (left–right log ratios)

Never compare raw L vs R. Use homologous log ratios per pair `p`, per band:

```
A_{t,p,b} = log( P_Left,p,b / P_Right,p,b )
z_{t,p,b}^asym = ( A_{t,p,b} − μ_{age,state,p,b}^asym ) / σ_{age,state,p,b}^asym
```

Sign gives direction (e.g. `z^asym > 0` ⇒ right > left if defined right/left). Compute the same
time summaries (Prev/Burden/LongestRun) on the asymmetry series. Sanity check against ACNS visual
"marked asymmetry" (>50% amplitude or >1 Hz difference).

## 6. Topographic classification

Aggregate channels → regions (L/R frontal, temporal, central, parietal, occipital, + midline).
Compute `Burden_{region,band,state}` and:

```
DominanceRatio = Burden_maxregion / ( median(Burden_other regions) + ε )
```

Classify:
- **Generalized** — both hemispheres abnormal, multiple regions, asymmetry *not* abnormal.
- **Lateralized (hemispheric)** — one hemisphere abnormal + abnormal hemisphere asymmetry burden.
- **Focal** — one region / one dominant side of a pair, burden substantially above neighbors (high
  dominance ratio).
- **Multifocal** — ≥2 noncontiguous abnormal regions, no single dominant field (low dominance ratio).

Calibrate thresholds against expert-labeled EEGs, not theory.

## 7. Absolute vs relative vs total power — interpretation table

| Abs δ/θ | Rel δ/θ | Broadband/total | Interpretation |
|---|---|---|---|
| High | High | normal/high | Strong evidence for true low-frequency excess |
| High | not high | High | Globally high amplitude / technical / breach / nonspecific |
| not high | High | low/normal | Spectral shift from reduced faster activity (may still be slowing) |
| High δ only | — | — | Delta-predominant slowing |
| High θ only | — | — | Mild slowing / drowsiness / meds / age variant |
| δ & θ high | both high | — | Mixed theta/delta slowing |

Report absolute δ, relative δ, θ, LF burden, and broadband **separately**, then let a composite
slowing score combine them.

## 8. Verbal mapping

Template: `[State]: [prevalence] [severity] [location/laterality] [band/type] slowing, +
quantitative parenthetical.` Generate the phrase **from the quantitative table, not separately.**

Provisional severity (patient-level z): **2.0–3.0 mild, 3.0–4.5 moderate, >4.5 marked** (final
cutoffs from expert labels + target specificity).

Band phrase: delta-dominant → "delta slowing"; theta-dominant → "theta slowing"; both → "mixed
theta/delta slowing"; broad 0.5–7 excess → "low-frequency slowing"; narrow rhythmic delta peak →
"rhythmic delta activity" *if morphology supports it*.

**Caveat (must be preserved):** spectrum detects delta *excess* but cannot alone distinguish
polymorphic slowing vs rhythmic delta vs periodic pattern vs artifact vs normal variant —
morphology review may be required.

## 9. Practical guardrails

1. **Wakefulness is not one state** — separate norms for alert eyes-open, eyes-closed, and
   drowsy/transitional wake, or drowsiness gets overcalled as slowing.
2. **Exclude/annotate** eye movement, muscle, movement, electrode artifact, epileptiform bursts,
   seizures, HV response, photic driving, arousals.
3. **Identical preprocessing** for reference and patient (montage, reference, filters, notch, fs,
   artifact rejection, interpolation, band edges).
4. **State-specific norms** — delta in N3 ≠ delta in alert wake.
5. **Report the denominator** — "frequent" over 10 usable segments ≠ over 200.

## 10. Compact core (minimum viable)

```
SegmentZ_{t,r,b}   = ( logP_{t,r,b} − μ_{age,state,r,b} ) / σ_{age,state,r,b}
Burden_{state,r,b} = (1/T) Σ_t Δt · max(SegmentZ_{t,r,b} − 2, 0)
PatientZ_{state,r,b}   = Φ⁻¹( F_{normal,state,r,b}( Burden ) )
AsymmetryZ_{state,p,b} = Φ⁻¹( F^asym_{normal,state,p,b}( Burden^asym ) )
phrase = state + prevalence + severity + location/laterality + band
```
