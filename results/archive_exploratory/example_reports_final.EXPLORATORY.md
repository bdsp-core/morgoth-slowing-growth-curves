> # ⚠️ ARCHIVED — EXPLORATORY, DO NOT CITE
>
> These sentences violate four rows of `docs/claims_table.md` at once. Example:
> *"Rare mild generalized mixed theta/delta slowing — peak 0.0 SD above age/stage-matched norms."*
> — a severity adjective (row 9, FORBIDDEN: ρ = 0.050 across 168 variants), a frequency word
> (row 6b, FORBIDDEN: ρ = 0.077), a band claim (row 5, FORBIDDEN: AUROC 0.579 against a ceiling of
> 0.541), and a peak statistic (row 10, FORBIDDEN: artifact-dominated) — asserting slowing at a
> deviation of **zero**, on a recording labelled normal.
>
> Superseded by `scripts/110_generate_sentence.py` (to be written against the claims table).

# Final gated reports (Morgoth gate + normative description)

Gate: report slowing only if Morgoth P(slowing) >= 0.311.

## focal_slow (gated-in examples)

- (age 50 F, P_slow=0.32, focal) Frequent mild bilateral temporal mixed theta/delta slowing — present in 48% of segments; peak 1.9 SD above age/stage-matched norms; longest run 3.8 min over 4 episodes.
- (age 38 F, P_slow=0.88, generalized) Frequent mild generalized mixed theta/delta slowing — present in 19% of segments; peak 1.3 SD above age/stage-matched norms; longest run 0.7 min over 6 episodes; present only during sleep; accentuated in N1.
- (age 71 M, P_slow=0.53, focal) Frequent mild left parasagittal mixed theta/delta slowing — present in 17% of segments; peak 2.3 SD above age/stage-matched norms; L>R temporal mixed asymmetry 1.5 SD; longest run 0.7 min over 4 episodes; accentuated in N3.
- (age 71 M, P_slow=0.55, generalized) Occasional mild generalized mixed theta/delta slowing — present in 7% of segments; peak 1.1 SD above age/stage-matched norms; longest run 0.5 min over 2 episodes.
- (age 81 F, P_slow=0.39, generalized) Abundant mild generalized mixed theta/delta slowing — present in 57% of segments; peak 1.6 SD above age/stage-matched norms; longest run 1.9 min over 8 episodes; present only during sleep; accentuated in N2.

## general_slow (gated-in examples)

- (age 19 M, P_slow=0.39, generalized) Rare mild generalized mixed theta/delta slowing — peak 0.6 SD above age/stage-matched norms.
- (age 69 F, P_slow=0.60, focal) Rare mild right parasagittal mixed theta/delta slowing — peak 1.4 SD above age/stage-matched norms; R>L temporal mixed asymmetry 2.3 SD.
- (age 68 F, P_slow=0.70, focal) Rare mild left parasagittal mixed theta/delta slowing — peak 1.4 SD above age/stage-matched norms; L>R temporal mixed asymmetry 4.0 SD.
- (age 70 F, P_slow=0.74, focal) Rare mild left temporal mixed theta/delta slowing — peak 1.7 SD above age/stage-matched norms; L>R temporal mixed asymmetry 1.9 SD.
- (age 39 M, P_slow=0.91, focal) Rare mild right parasagittal mixed theta/delta slowing — peak 2.1 SD above age/stage-matched norms; R>L temporal mixed asymmetry 5.3 SD.

## normal (gated-in examples)

- (age 67 F, P_slow=0.33, generalized) Occasional mild generalized mixed theta/delta slowing — present in 5% of segments; peak 0.2 SD above age/stage-matched norms; longest run 0.2 min over 2 episodes; accentuated in REM.
- (age 55 F, P_slow=0.48, focal) Rare mild bilateral parasagittal mixed theta/delta slowing — peak 1.3 SD above age/stage-matched norms.
- (age 38 F, P_slow=0.49, generalized) Rare mild generalized mixed theta/delta slowing — peak 0.0 SD above age/stage-matched norms.
- (age 59 M, P_slow=0.32, generalized) Rare mild generalized mixed theta/delta slowing — peak 0.0 SD above age/stage-matched norms.
- (age 2 M, P_slow=0.36, generalized) Rare mild generalized mixed theta/delta slowing — peak 1.1 SD above age/stage-matched norms.
- (age 77 F, P_slow=0.14) No pathological slowing.
- (age 30 F, P_slow=0.30) No pathological slowing.

