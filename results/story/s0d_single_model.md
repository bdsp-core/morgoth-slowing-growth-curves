# ONE report-trained Morgoth-free model — externally validated on the OccasionNoise expert panel

A single segment-level model (two heads), trained ONLY on the single-scored REPORT data (patient-stratified
split balanced over lifespan × focal/gen/both/control, ~16k training recordings), then applied UNCHANGED to
the OccasionNoise expert panel — never seen in training. Each 15 s segment → stage-matched deviation features
(amount z for generalized; region peak / focality / asymmetry for focal, against the shared grid_norm.json).
Works on a lone clip (segment output) and aggregates for full recordings. Experts scored vs the leave-one-out
consensus of the others.

## Result — OccasionNoise (slowing-vs-normal panel; our model vs Morgoth vs 18 experts)

| axis | our aggregation | our AUROC | % experts under ROC / PR | Morgoth |
|---|---|---|---|---|
| **generalized** | segment-score pooling (top-5) | **0.946** | **78% / 72%** | 0.853 · 11% / 6% |
| **focal** | recording-level feature aggregation | **0.923** | **~50% / ~41%** | 0.908 · 41% / 47% |

Both axes beat Morgoth. GENERALIZED puts ~three-quarters of the panel under the curve; FOCAL about half. The
aggregation split is mechanistic: focal is a spatial+intermittent judgement that needs the rich recording-
level aggregation of the localization features; generalized is a diffuse amount that a pooled segment score
captures best. Both come from the SAME segment representation.

*Trained on NOISY report labels, the model generalizes to the CLEAN expert consensus far better (0.92–0.95)
than its own report-test number (~0.73) implies — the report labels are the limiting noise, not the signal.*
