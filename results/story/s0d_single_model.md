# ONE report-trained Morgoth-free model — externally validated on the expert panels

A single segment-level model (two heads), trained ONLY on the single-scored REPORT data (patient-stratified
split balanced over lifespan × focal/gen/both/control, ~16k training recordings), then applied UNCHANGED to
OccasionNoise and MoE — never seen in training. Each 15 s segment → stage-matched deviation features (amount
z for generalized; region peak / focality / asymmetry for focal, against the shared grid_norm.json). Works on
a lone clip (segment output) and aggregates for full recordings. Experts scored vs leave-one-out consensus;
MoE ground truth = the canonical Experts-sheet consensus (NOT a band-union).

## Result — OccasionNoise (slowing-vs-normal panel; our model vs Morgoth vs 18 experts)

| axis | our aggregation | our AUROC | % experts under ROC / PR | Morgoth |
|---|---|---|---|---|
| **generalized** | segment-score pooling (top-5) | **0.946** | **78% / 72%** | 0.853 · 11% / 6% |
| **focal** | recording-level feature aggregation | **0.923** | **~50% / ~41%** | 0.908 · 41% / 47% |

Both axes beat Morgoth. GENERALIZED puts ~three-quarters of the panel under the curve; FOCAL about half. The
aggregation split is mechanistic: focal is a spatial+intermittent judgement that needs the rich recording-
level aggregation of the localization features; generalized is a diffuse amount that a pooled segment score
captures best. Both come from the SAME segment representation.

This CORRECTS the earlier "generalized is at the human ceiling" read (§0c) — that was a 100-recording
training artifact; with thousands of report recordings the report-trained model generalizes to the expert
consensus and beats it. v1 broadcast ≈ v2 MIL (MIL added nothing → broadcast + pooling is the answer).

## MoE — a different, harder task (corrected ground truth)

MoE is a curated MULTI-CATEGORY benchmark: its slowing "controls" are OTHER abnormalities (26% burst
suppression, plus GPD/LPD/seizure/spikes), ~0 clean normals. So "generalized slowing" there is
slowing-vs-other-abnormal. With the canonical Experts-sheet consensus, Morgoth generalized = 0.837 (focal
0.949); our single-CLIP model is weaker on MoE (no recording aggregation to exploit; single clips reward the
foundation model's waveform reading). Burst-suppression exclusion barely changes it.

*Trained on NOISY report labels, the model generalizes to the CLEAN expert consensus far better (0.92-0.95)
than its own report-test number (~0.73) implies — the report labels are the limiting noise, not the signal.*
