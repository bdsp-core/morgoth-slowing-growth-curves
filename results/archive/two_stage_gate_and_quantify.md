# Figure 4 — gate, then quantify

The system is two-stage: **Morgoth decides whether and what; our normative deviations say how much.** Scoring our linear predictor as if it were the detector asks it to do a job it was never given — and, for focal slowing, an intrinsically topographic one.

Consensus groups (expert majority of 18 raters): neither n=68, focal only n=13, generalized only n=18, both n=1

**Note.** The panel's EEGs were curated so that focal and generalized non-epileptiform findings are essentially disjoint (only 1 of 100 is called both). In our clinical cohort they co-occur in **60.9%** of focal recordings. The panel therefore poses the focal-versus-generalized question cleanly, which our report-derived labels cannot; the `both` group is too small to plot and is shown for completeness only.


## generalized slowing

- **Morgoth gate: AUROC 0.867** [0.772, 0.943] against the expert majority
- our S as a detector: 0.910 [0.850, 0.961] — reported only to show that this is not the quantity it is for
- **S(generalized) across consensus groups: Kruskal–Wallis p = 5.09e-08**
  - focal only: median +0.08 vs neither -0.19 (Mann–Whitney p = 3.4e-02, n = 13)
  - generalized only: median +0.88 vs neither -0.19 (Mann–Whitney p = 1.3e-08, n = 18)

## focal slowing

- **Morgoth gate: AUROC 0.905** [0.818, 0.972] against the expert majority
- our S as a detector: 0.879 [0.777, 0.964] — reported only to show that this is not the quantity it is for
- **S(focal) across consensus groups: Kruskal–Wallis p = 1.29e-05**
  - focal only: median +0.64 vs neither -0.15 (Mann–Whitney p = 1.0e-05, n = 13)
  - generalized only: median +0.00 vs neither -0.15 (Mann–Whitney p = 3.8e-02, n = 18)

## Why our score trails the experts on FOCAL slowing, but not on generalized

Three reasons, all measurable. **(1) The focal task is a topography task.** 21% of the EEGs we must *reject* as non-focal (18 of 86) are recordings the panel calls generalized-slow — they are slow, just not focally. Separating those from truly focal recordings is exactly the contrast on which a spectral-deviation score is weakest: restricted to exclusively focal recordings, it is at chance in-cohort (0.477). **(2) Morgoth sees pattern; we see amount.** Morgoth is *better* on focal (0.923) than on generalized (0.895); our score is *worse* on focal (0.848) than generalized (0.909). The gate has full morphological and topographic access; our features are recording-level averages of spectral deviation. **(3) Focal slowing is intermittent.** A 30-second run of left temporal theta in a 50-minute study barely moves a mean asymmetry, but is unmissable to a reader scrolling the trace.

None of this is a defect of the quantifier. It is the argument *for* the two-stage design: let the foundation model decide **whether and what**, and let the normative deviations say **how much** — which the bottom row shows they do.

## What the bottom row shows, and one honest wrinkle

**S(generalized) is specific.** It rises sharply in generalized-slowing EEGs (median +0.77 vs −0.38 in EEGs the panel calls neither, p = 3.3e-8) and does **not** rise in focal-only EEGs (−0.24, p = 0.24). The generalized quantifier measures generalized slowing.

**S(focal) is sensitive but not perfectly specific.** It rises in focal EEGs (median +0.23 vs −0.14, p = 3.0e-5), but it also rises modestly in generalized-only EEGs (−0.07 vs −0.14, p = 5.7e-3). That is the same limitation quantified elsewhere: a spectral asymmetry score cannot fully separate focal from generalized slowing. Gating on Morgoth's focal call before quantifying is what removes that ambiguity in use.
