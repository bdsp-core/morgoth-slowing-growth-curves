# Section 2d — per-segment deviation field (stage-appropriate)

Each segment carries a deviation z per feature × region, scored against its own (sleep-stage, age) normal. Below: whole-head median segment-z by sleep stage — clean-normal (should sit ~0, confirming per-stage calibration) vs abnormal (shifted positive).

| feature | group | W | N1 | N2 | N3 | REM |
|---|---|---|---|---|---|---|
| delta excess | clean-normal | +0.22 | +0.13 | -0.01 | -0.09 | +0.23 |
| delta excess | abnormal | +0.80 | +1.44 | +0.48 | +0.12 | +1.08 |
| theta/alpha ratio | clean-normal | +0.39 | +0.05 | +0.01 | -0.18 | +0.18 |
| theta/alpha ratio | abnormal | +1.08 | +1.17 | +0.72 | +0.08 | +0.71 |
| delta/alpha ratio | clean-normal | +0.36 | +0.21 | +0.09 | -0.32 | +0.11 |
| delta/alpha ratio | abnormal | +0.97 | +1.41 | +0.82 | +0.14 | +0.70 |