> ⚠ **SUPERSEDED — historical only.** This doc asserts facts now overridden by `docs/analysis_plan.md` (the SAP) and `docs/claims_table.md` (e.g. theta = 4–8 Hz; severity adjectives / ACNS frequency words / band-from-our-features are FORBIDDEN output; artifact segments are flagged not stripped; zero reuse of prior derived tables). Do not implement from this file. Retained for provenance.

# Artifact / flat-segment rejection — method & validation plan

Essential for two reasons: (1) norms must be computed on clean brain signal, not flat/artifact
sections; (2) real reporting must ignore artifact. Implemented in `src/morgoth_slowing/features/
artifact.py` (per 15-s bipolar segment).

## Detection rules (segment usable iff all pass)
- **Flat / disconnected:** median channel peak-to-peak < 1 µV, or >50% of channels flat → reject.
- **High-amplitude (movement/electrode pop):** any channel p2p > 500 µV → reject.
- **EMG / muscle:** fraction of 1–45 Hz power above 20 Hz > 0.55 → reject.
- (Extensible: eye-blink via frontal slow transients, 50/60 Hz line dominance, clipping/saturation.)
Thresholds are provisional — calibrate against manual review (below).

## Validation on a real full recording (pilot, done)
One BIDS EDF (mostly flat/disconnected): 253 segments → **93 usable (37%)**; rejected 156 flat + 4
high-amplitude. Whole-head **rel_delta: 0.047 (all segments) → 0.323 (usable only)**, matching the
cohort norm (~0.34). → flat/artifact rejection recovers valid features on full recordings.

## Plan to CONFIRM artifact rejection works (before trusting at scale)
1. **Manual-review gold standard:** sample ~300 segments across recordings/ages; expert (or 2 raters)
   label clean vs artifact(type). Report sensitivity/specificity/PPV of our flags per artifact type;
   target high specificity for "clean" (don't keep artifact) and reasonable sensitivity.
2. **Against existing annotations:** where BDSP/XLTEK/Persyst artifact or IIIC annotations exist, check
   our rejects overlap flagged artifact/movement/EMG epochs.
3. **Norm-stability test:** recompute normal growth curves with vs without rejection; rejection should
   (a) reduce variance/outliers in normals, (b) leave the age/stage trajectory shape unchanged, and
   (c) not systematically shift medians except by removing artifact inflation.
4. **Round-trip on curated data:** run rejection on the already-curated Growth_curves segments (should
   keep ~all — low false-reject rate on clean data); measure false-reject %.
5. **Downstream invariance:** confirm discrimination AUCs / report agreement do not drop (ideally
   improve) after rejection; and that Morgoth stage/finding predictions on kept vs all segments agree.
6. **Report the denominator:** always log usable-segment count/%, so low-yield recordings are flagged
   rather than silently scored on a few segments.

## Integration
Apply `artifact.usable_mask` in the full-recording featurizer (io/edf → extract) before computing
segment features and before staging aggregation; carry usable-% into scoring (feature_spec §9.5).
