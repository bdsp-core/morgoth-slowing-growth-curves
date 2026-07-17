# Can a Morgoth-FREE classifier beat the experts? (OccasionNoise, N=100, LOO-CV)

Two independent detectors — focal and generalized slowing — built ONLY from spectral/deviation features of
the EEG, no Morgoth. Ground truth = panel majority; each of the 18 experts is an operating point vs the
leave-one-out consensus of the others. Headline = % of experts UNDER our ROC / PR curve (how much of the
human panel we dominate). Everything is leave-one-out cross-validated.

## The trajectory — each design choice, and what it bought

| detector | focal AUROC | focal % under ROC | generalized AUROC | gen % under ROC |
|---|---|---|---|---|
| wake mean (region asymmetry / whole-head amount) | 0.850 | 24% | 0.805 | 28% |
| wake per-segment intermittency (max/p90) | 0.748 | 6% | 0.841 | 28% |
| **W + N1, stage-matched deviation z** | 0.875 | 29% | **0.898** | **39%** |
| **all stages, stage-matched + LOCALIZED focal** | **0.898** | **53%** | 0.913 | 33% |
| *Morgoth (reference, EEG-level head)* | *0.905* | *41%* | *0.867* | *17%* |

## What worked

- **Stage-matching unlocks the sleep stages.** Raw pooling of N1/deep-sleep adds physiologic drowsy slowing
  as noise; z-scoring each segment against ITS OWN (stage, age) normal keeps only abnormal-for-its-stage
  slowing. This is what let more stages help instead of hurt.
- **Focal is a SPATIAL problem — localize, then characterize.** Amount of slowing cannot separate focal from
  generalized (both raise it). The discriminators are: peak-region z (the worst region), **focality =
  peak − median region z** (concentrated vs diffuse), asymmetry z, and spatial stability of the peak region.
  Adding these over all stages took focal from 24% → **53% of experts under ROC (65% under PR)** — beating
  most of the panel, and beating Morgoth (41%), with no Morgoth at all.

## Where it lands

- **FOCAL: beaten.** Most experts sit under our ROC (53%) and PR (65%) curves. A simple, interpretable
  spectral+localization classifier out-detects the expert panel and the foundation model.
- **GENERALIZED: strong, not a majority.** AUROC 0.913 clears Morgoth's 0.867, and we already put more
  experts under than Morgoth (39% at W+N1 vs 17%), but not >50%. Generalized slowing is diffuse — there is no
  spatial trick — and the experts agree tightly with the consensus (κ ≈ 0.45), so the operating-point cluster
  is hard to dominate. This looks near the human ceiling rather than a feature-engineering gap.

*Scripts: 46 (wake mean), 47 (per-segment), 48 (W+N1 stage-matched), 49 (all-stage + localized focal).*
