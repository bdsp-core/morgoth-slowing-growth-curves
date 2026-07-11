> ⚠ **SUPERSEDED — historical only.** This doc asserts facts now overridden by `docs/analysis_plan.md` (the SAP) and `docs/claims_table.md` (e.g. theta = 4–8 Hz; severity adjectives / ACNS frequency words / band-from-our-features are FORBIDDEN output; artifact segments are flagged not stripped; zero reuse of prior derived tables). Do not implement from this file. Retained for provenance.

# Figure 5 — Pipeline schematic: artist brief

**Purpose.** One figure that makes the paper's architecture instantly legible: a foundation model decides
*whether and what* to report; **lifespan, sleep-stage, vigilance-matched normative growth curves** decide
*how to describe it*. The growth chart is the intellectual centrepiece and must read as such.

**Format.** Full page width, landscape, ~180 mm × 90–110 mm. Vector (AI/SVG), CMYK-safe, legible at 100%.
Print-safe: no information carried by color alone; distinguish tracks by shape/position/label as well as hue.

---

## Overall layout — left-to-right flow, splitting into two tracks that re-merge

```
 [A] INPUT ──▶ [B] SIGNAL PREP ──▶ [C] FEATURES ──┬──▶ [D] SLEEP STAGING ──┐
                                                  │                        │
                                                  │                        ▼
                                                  │           [E] NORMATIVE GROWTH CURVES  ★centrepiece★
                                                  │                        │
                                                  │                        ▼
                                                  │           [F] DEVIATION SCORING (z)
                                                  │                        │
                                                  └──▶ [G] MORGOTH GATE    │
                                                          (3 tiers)        │
                                                              │            │
                                                              └────┬───────┘
                                                                   ▼
                                                        [H] DESCRIPTION SYNTHESIS
                                                                   ▼
                                                        [I] OUTPUT SENTENCE
```

Draw **two visually distinct tracks** that converge at [H]:
- **Detection track (G)** — cooler/neutral (e.g. slate). Label it **"WHETHER & WHAT"**.
- **Description track (D→E→F)** — warmer/accent. Label it **"HOW TO DESCRIBE"**.
Place a small vertical divider or tinted band behind each track so the reader sees the two roles at a glance.

---

## Panel contents

**[A] Input.** A short strip of multichannel EEG waveform (8–10 traces). Caption: *"Clinical EEG — routine
(alerted) or overnight."* Small icons: a clock (20 min) and a moon (all-night) to show both study types.

**[B] Signal prep.** Head diagram with the 10–20 electrodes, arrows forming the **double-banana bipolar
chains** (18 derivations). Beneath: three tiny badges — `0.5 Hz high-pass`, `50/60 Hz notch`,
`15-s segments`. One badge for **artifact rejection** with a segment shown greyed/struck out.

**[C] Features.** A small multitaper spectrum with δ/θ/α/β bands shaded. Callouts for the derived measures:
**relative delta**, **DAR (δ/α)**, **TAR (θ/α)**, **left–right homologous asymmetry**. Note "31 features ×
18 channels, per 15-s segment."

**[D] Sleep staging.** A compact hypnogram (W/N1/N2/N3/REM) with each 15-s segment tagged by stage. Use the
project's stage colors (W gold, N1 light blue, N2 blue, N3 navy, REM purple) — reuse them everywhere.

**[E] NORMATIVE GROWTH CURVES — make this the largest, most beautiful element.**
A miniature growth chart: **x = age on a log scale** (ticks: 0, 1mo, 6mo, 1, 5, 20, 60), **y = feature
value**, with nested percentile bands (p3–p97 / p10–p90 / p25–p75, darker toward the median) and a bold
median line. Show **one patient plotted as a single marker sitting high in the band**, with a dotted
drop-line to the axis and a small "+2.1 SD" flag. Behind it, fan out **five faint copies** (one per stage,
in stage colors) to convey "one chart per sleep stage."
Annotate with three short tags — the paper's three normative claims:
- `lifespan-continuous (GAMLSS/LMS)`
- `sleep-stage-specific`
- `vigilance-matched reference`
Sub-caption: *"n = 20,892 clinician-normal recordings."*

**[F] Deviation scoring.** An arrow from [E] labelled **"z = deviation from age- & stage-matched normal."**
Show a tiny per-segment z time series with a threshold line and some segments above it shaded.

**[G] Morgoth gate — three stacked tiers**, each a rounded box with a yes/no branch:
1. `Tier 1 — Abnormal?` → if **no**, a short arrow straight to the output reading *"Normal study."*
2. `Tier 2 — Pathological slowing?` (high specificity)
3. `Tier 3 — Focal? / Generalized?` (two **non-exclusive** heads, so draw both branches able to fire)
Label the whole block **"expert-calibrated foundation model."**

**[H] Description synthesis.** A hub where the gate's branch selects *which* description to build, and the
deviation summaries fill it in. Show six small chips feeding the hub:
`severity (z)` · `prevalence (% segments)` · `persistence (runs, episodes)` · `band (δ / θ / mixed)` ·
`localization (region + side, from asymmetry)` · `stage-accentuation`.

**[I] Output.** A "report card" containing one real generated sentence, set in a clinical serif:

> *"Frequent mild left temporal mixed theta/delta slowing — present in 48% of segments; peak 2.1 SD above
> age- and stage-matched norms; longest run 3.8 min over 4 episodes; accentuated in N2."*

Underneath, small italic: *"Detection by the gate; every adjective and number by the normative model."*

---

## Emphasis, in priority order
1. **[E] is the hero.** Largest area, richest rendering. If space is tight, shrink [B]/[C], never [E].
2. **The two-track split and re-merge** must be obvious in one glance — this is the paper's core design idea
   (*detection ≠ description*).
3. **Vigilance-matching**: on the arrow entering [E], add a small selector glyph reading
   `(age, sleep stage, alert vs drowsy)` — this is a novel methodological point and readers miss it.
4. Keep all text ≥7 pt at final size. No more than ~40 words of label text on the whole figure.

## Things to avoid
- Do **not** draw the gate as a black box in the middle of the flow — it sits *beside* the normative track.
- Do **not** imply the growth curve is a classifier; it is a **reference**, and the arrow out of it is a z.
- No 3-D effects, no drop shadows, no gradient fills inside the percentile bands (flat tints only).
