# Cohort-vs-overnight difference: artifact ruled out (investigation A + B)

The normative median growth curves differ between the routine cohort (JJ `.mat` pipeline) and the overnight
expansion (extract.py). We interrogated whether this is artifactual before accepting it as physiology.

## Ruled OUT as the cause of the delta/slowing difference
- **Channels** — identical. Both pipelines extract the same C3/C4 bipolar chains (the `.mat`'s own
  `channels` field byte-matches extract.py's BIPOLAR order). (scripts/78 header)
- **Normal-label asymmetry (A)** — the overnight manifest used a looser "report-normal" filter (and
  hardcoded rfoc/rgen=0). Re-deriving the *strict* cohort standard on the overnight set removes only
  ~25–30% of the adult-wake gap (W adult 0.368→0.336 vs routine 0.252). Minor contributor. (scripts/77)
- **Pipeline, for delta (B)** — extract.py vs JJ `.mat` on the SAME 25 routine rEEG recordings: **rel_delta
  bias = −0.016** (medians 0.293 vs 0.306). The extractor was independently validated at r=0.89–0.95 on
  log band powers (scripts/12). So delta/total is computed consistently. (scripts/78)

## CONFIRMED real (physiology / population), for the delta difference
- **Vigilance state** — overnight "wake" is drowsy: rel_alpha 0.06 vs 0.24, more delta. Routine wake is
  alert (eyes-closed, prominent alpha); overnight wake is lights-out drowsy. Different states, same "W" label.
- **Disjoint populations** — 0 of 4,457 routine patients appear among 8,660 overnight patients. Routine
  outpatients vs overnight/inpatients (sicker, more neurologic disease, worse sleep, more likely medicated,
  even when a given EEG reads normal).
- **Internal control** — adult N2/N3 rel_delta agrees across sources (Δ≈0); only wake and pediatric sleep
  diverge. A pipeline artifact would shift every stage equally. It doesn't.

## GENUINE pipeline artifact — but only for alpha-based ratio features
extract.py alpha (8–13 Hz) is ~0.05 lower than JJ's on the same recordings (bias rel_alpha −0.049,
r=0.83), which propagates to DAR (+0.29) and TAR (−0.25). alpha was never calibrated to JJ the way delta
was. **Consequence: TAR/DAR/rel_alpha are NOT comparable across the two sources** — build them from a
single pipeline (the keystone Figure 1 uses overnight-only for exactly this reason).

## Implication for a single, setting-independent model
The slowing signal (delta) is pipeline-consistent, so a unified delta-based norm is valid. The
routine-vs-overnight difference is a **vigilance-state + population** effect, not a computational one — so
the fix is to define each vigilance state consistently, not to keep separate inpatient/outpatient models.
For the delta growth curves, the source-appropriate norm (alert wake from routine EEG + real sleep from
overnight EEG) is defensible because rel_delta is cross-consistent. For alpha-based ratio features, use a
single source. See [[cohort-expansion-harmonization]] in memory.
