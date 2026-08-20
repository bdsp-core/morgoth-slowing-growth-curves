# Section 2d — per-segment deviation field (stage-appropriate)

Each segment carries a deviation z per feature × region, scored against its own (sleep-stage, age) normal. Below: whole-head median segment-z by sleep stage — clean-normal (should sit ~0, confirming per-stage calibration) vs abnormal (shifted positive).

| feature | group | W | N1 | N2 | N3 | REM |
|---|---|---|---|---|---|---|
| delta excess | clean-normal | +0.24 | +0.18 | +0.00 | -0.04 | +0.19 |
| delta excess | abnormal | +0.83 | +1.57 | +0.48 | +0.13 | +1.01 |
| theta/alpha ratio | clean-normal | +0.33 | +0.17 | -0.02 | +0.06 | +0.18 |
| theta/alpha ratio | abnormal | +1.03 | +1.25 | +0.65 | +0.42 | +0.71 |
| delta/alpha ratio | clean-normal | +0.34 | +0.24 | +0.09 | -0.05 | +0.18 |
| delta/alpha ratio | abnormal | +0.96 | +1.36 | +0.83 | +0.42 | +0.72 |