# Morphology-aware EEG features — design proposal

## Why (the gap we are closing)

Validation (results/RESULTS.md §8) shows our slowing descriptions agree with expert reports well on
**location** (region 0.91, side 0.78) but poorly on **band** (delta/theta/mixed = **0.33**), and an
LR on our band-power "deviation-from-age/sex-norm" features reconstructs only **R²≈0.47** of Morgoth's
expert-calibrated P(slowing). Two structural reasons:

1. **Our features only measure power in bands.** A band integral cannot tell delta from theta when the
   spectral mass sits on a band edge, cannot see a peak riding on a 1/f background, and cannot see the
   *shape* of the low-frequency excess. Band edges (delta 1–4 / theta 4–8) are hard cutoffs; the report language
   is about where the *dominant slow rhythm* sits, which is a continuous quantity.
2. **Power is blind to morphology.** feature_spec §8 states the caveat explicitly: a spectrum detects
   delta *excess* but cannot alone distinguish **polymorphic** slowing vs **rhythmic** delta (FIRDA /
   TIRDA) vs periodic pattern vs artifact vs normal variant. These are the distinctions that separate
   an expert's "polymorphic left temporal delta" from "frontal intermittent rhythmic delta" — and
   almost certainly part of what Morgoth sees that our features miss.

This document proposes features **beyond band power** that (a) call band more faithfully, (b) separate
polymorphic vs rhythmic/monomorphic delta, (c) sharpen focal detection, and (d) close the Morgoth gap.

## Design principles / where these compute

- **Same unit of analysis** as today: 18 bipolar (double-banana) channels × 15-s segments @ 200 Hz,
  with a sleep stage per segment. Every feature below is defined **per segment, per channel** (or per
  channel-pair), then aggregated to region/side and scored against age/sex/**stage** norms exactly
  like the existing features (norms/, scoring/burden.py, patient_z.py). Nothing changes in the norm /
  z / burden machinery — we are only adding columns to the per-segment feature table.
- **Two signal sources are already in hand inside `features/extract.py`:** the raw bipolar segment
  `bip[s:e]` (before PSD — free for time-domain features) and the multitaper `psd` (18 × n_freq — free
  for spectral-shape features). Cross-channel features reuse the same 18-channel segment array.
- **Home for the code:** a new `src/morgoth_slowing/features/morphology.py` called from the segment
  loop in `extract.py`, emitting extra channels appended to the (n_seg, 18, F) tensor; `recording.py`
  aggregates them to region/segment rows the same way it does the 31 base features. Spectral-shape
  helpers can extend the stub `features/spectra.py`; the current `spectra.py`/`bandpower.py` are
  unimplemented placeholders, so `extract.py` is the real integration point.
- **Calibration targets we already have:** `results/report_extracted_labels.csv` (band/side/region
  per recording) for band-calling thresholds, and Morgoth P(slowing/focal/gen) for distillation
  (scripts/15, 17). Every proposed decision rule is *fit* to these, not set by theory.

---

## 1. Better BAND composition (delta vs theta vs mixed) — the weakest axis

The 0.33 band agreement is the single biggest, cheapest win. Replace the implicit "which band integral
is bigger" logic with continuous descriptors of *where the slow mass sits* and a decision rule fit to
report labels.

### 1.1 Slow-band spectral centroid
**Measures.** Center of mass of power in the pathological-slow range, a continuous "dominant slow
frequency."
**Helps.** BAND (delta/theta/mixed) directly — the calling axis.
**Definition.** Per channel, from the existing `psd` restricted to `[0.5, 7] Hz`:
```
f_centroid = Σ_f f·PSD(f) / Σ_f PSD(f)          over 0.5 ≤ f ≤ 7 Hz
```
Delta-dominant → f_centroid ≈ 1.5–3 Hz; theta-dominant → ≈ 5–6.5 Hz; mixed → intermediate/broad.
**Implementation.** ~5 lines on `psd` in `morphology.py`. Negligible cost.

### 1.2 Slow peak frequency
**Measures.** Frequency of the dominant slow spectral peak (as opposed to the centroid, which a broad
shoulder can drag).
**Helps.** BAND; also feeds rhythmicity (§3) as the expected rhythm frequency.
**Definition.** Smooth `PSD` over 0.5–7 Hz (e.g. 3-bin Hann), take `argmax`; optionally parabolic
interpolation on the three bins around the max for sub-bin resolution:
```
f_peak = argmax_f smooth(PSD)(f),   0.5 ≤ f ≤ 7 Hz
```
Report `f_peak` and its prominence (peak height above the local 1/f baseline, see §2.1).
**Implementation.** `morphology.py` on `psd`. Negligible.

### 1.3 Slow-band spread / bimodality (the "mixed" detector)
**Measures.** Whether slow power is concentrated at one frequency (pure delta OR pure theta) or spread
across delta+theta (mixed).
**Helps.** BAND, specifically the *mixed* label that a single band-ratio cannot express.
**Definition.** Spectral bandwidth around the centroid, and a two-peak test:
```
BW_slow = sqrt( Σ_f (f − f_centroid)²·PSD(f) / Σ_f PSD(f) )        over 0.5–7 Hz
bimodality = (2nd-highest local-max height) / (highest local-max height)   in 0.5–7 Hz
```
Large `BW_slow` and/or `bimodality → 1` with one max in delta and one in theta ⇒ mixed.
**Implementation.** `morphology.py`. Negligible.

### 1.4 Calibrated band-decision rule (replaces implicit ratio calling)
**Measures.** The delta / theta / mixed / low-frequency call itself.
**Helps.** BAND — turns the descriptors above into the reported word, calibrated to experts.
**Definition.** Per abnormal segment (already flagged by z>τ), form the feature vector
`[f_centroid, f_peak, BW_slow, bimodality, DTR (=log δ/θ, existing)]`; classify:
```
delta   if f_centroid < c1 and bimodality < m
theta   if f_centroid > c2 and bimodality < m
mixed   if bimodality ≥ m OR c1 ≤ f_centroid ≤ c2 OR BW_slow > w
low-freq (0.5–7 broad) if BW_slow very large and no dominant peak
```
Fit thresholds `c1,c2,m,w` (or better, an **ordinal logistic / small tree**) against the report band
labels in `report_extracted_labels.csv`. Aggregate to the recording by majority vote over abnormal
segments (weighted by burden), so the report word comes from a calibrated model, not a hard band edge.
**Implementation.** New calibration script analogous to scripts/20; the phrase builder
(`report/phrase.py`) consumes the aggregated call. Low cost, high ROI.

---

## 2. Spectral shape / sharpness & peakedness (oscillation vs 1/f background)

### 2.1 Aperiodic (1/f) decomposition + oscillatory peaks (specparam / FOOOF-style)
**Measures.** Splits the log-PSD into an **aperiodic** background (offset + exponent) and **periodic**
peaks (center freq, power-over-background, bandwidth).
**Helps.** The **Morgoth gap** and BAND. Directly implements the feature_spec §7 interpretation table:
"abs high but rel not high / broadband high" = an elevated aperiodic *offset* (amplitude/technical/
breach), whereas true oscillatory slowing is a **peak above** the 1/f. Peak center-freq is a
morphology-faithful band call (§1). The aperiodic **exponent** is a strong age/maturation and
encephalopathy marker that our band ratios do not capture — a prime candidate for the ~53% of Morgoth
we currently miss.
**Definition.** Fit on log-PSD over ~1–40 Hz:
```
log PSD(f) ≈ (b − χ·log f)                aperiodic: offset b, exponent χ
           + Σ_k G_k(f; μ_k, a_k, σ_k)     Gaussian peaks: center μ, power a, width σ
```
Emit per channel: `aperiodic_offset b`, `aperiodic_exponent χ`, and for the largest slow peak
(μ_k in 0.5–7 Hz) its `center μ`, `power a` (height above 1/f), `bandwidth σ`. Use the `specparam`
(fooof) library or a lightweight robust log-log fit (RANSAC line for aperiodic, then peak-pick
residual) to avoid a heavy dependency.
**Implementation.** `morphology.py`/`spectra.py` on the existing `psd`. Moderate cost (per-channel
optimization); fit once per segment×channel. Cache the aperiodic fit — it also supplies §2.2.

### 2.2 Spectral peakedness / concentration
**Measures.** How peaked vs flat the (background-removed) slow spectrum is.
**Helps.** Rhythmic vs polymorphic (§3) and BAND.
**Definition.** After removing the aperiodic background (§2.1), either the peak **prominence**
`a / (background at μ)`, or a spectral kurtosis of the residual over 0.5–7 Hz. High ⇒ narrow rhythmic
peak; low ⇒ broad polymorphic excess.
**Implementation.** Reuses §2.1 fit. Negligible incremental cost.

---

## 3. Rhythmicity / regularity — polymorphic vs rhythmic (FIRDA / TIRDA)

This family targets the feature_spec §8 caveat head-on: the spectrum sees delta *excess* but cannot
say whether it is **polymorphic** (irregular, arrhythmic — most focal/structural slowing) or
**rhythmic/monomorphic** (FIRDA frontal, TIRDA temporal). Compute all on the slow-band-filtered
segment `y = bandpass(bip[s:e,ch], 0.5–4 Hz)` (theta variant on 4–8 Hz).

### 3.1 Autocorrelation rhythmicity index
**Measures.** Whether the slow activity repeats at a stable period.
**Helps.** Polymorphic vs rhythmic (FIRDA/TIRDA); improves BAND-type wording.
**Definition.**
```
ACF(τ) = normalized autocorrelation of y
R_rhythm = height of first prominent ACF peak at τ>0 (near lag 1/f_peak) relative to ACF(0)
```
Rhythmic (monomorphic) ⇒ large, slowly-decaying oscillatory ACF with a clear secondary peak;
polymorphic ⇒ ACF decays fast, no secondary peak. Combine with region: high `R_rhythm` + frontal ⇒
FIRDA candidate; + temporal ⇒ TIRDA candidate.
**Implementation.** `morphology.py` on bandpassed `bip`. Cheap (one FFT-based ACF per channel).

### 3.2 Spectral entropy
**Measures.** Flatness of the normalized spectrum (Shannon entropy).
**Helps.** Rhythmic vs polymorphic (fast, robust proxy for §3.1); Morgoth gap.
**Definition.** With `p(f) = PSD(f)/Σ PSD(f)` over the slow band (and a full-band variant):
```
H = −Σ_f p(f)·log p(f)   (optionally / log N to normalize to [0,1])
```
Low H = concentrated/rhythmic; high H = broadband/polymorphic.
**Implementation.** `morphology.py` on existing `psd`. Negligible.

### 3.3 Peak sharpness (Q factor)
**Measures.** Narrowness of the dominant slow peak.
**Helps.** Rhythmic vs polymorphic; BAND (a sharp narrow peak is a "rhythm," a broad hump is not).
**Definition.** `Q = f_peak / FWHM` of the dominant slow peak (FWHM from §2.1's σ: `FWHM ≈ 2.355·σ`).
High Q ⇒ rhythmic; low Q ⇒ polymorphic.
**Implementation.** Reuses §1.2 / §2.1. Negligible.

### 3.4 Cycle-regularity (period & amplitude CV)
**Measures.** Beat-to-beat regularity of individual slow waves (a bycycle-style time-domain view).
**Helps.** The cleanest polymorphic-vs-rhythmic separator; underwrites "rhythmic delta activity"
morphology wording that §8 says requires morphology support.
**Definition.** Detect cycles in `y` (zero-crossings or peak/trough pairs); for the cycle set:
```
CV_period    = sd(period) / mean(period)
CV_amplitude = sd(peak-to-peak) / mean(peak-to-peak)
```
Low CVs ⇒ monomorphic/rhythmic (FIRDA/TIRDA); high CVs ⇒ polymorphic.
**Implementation.** `morphology.py`; robust cycle detection is the only fiddly part. Cheap per segment.

---

## 4. Waveform morphology (time domain) — line length, amplitude, sharpness

Cheap time-domain summaries on the raw / band-filtered `bip[s:e]`. They add amplitude and transient
"sharpness" information the spectrum smears out, and are strong, cheap candidates for the Morgoth gap.

### 4.1 Line length
**Measures.** Cumulative waveform excursion — jointly sensitive to amplitude and frequency.
**Helps.** Morgoth gap; focal detection (localizes to active channels).
**Definition.** `LL = Σ_n |x[n] − x[n−1]|` per channel (raw and slow-band variants). Normalize by
segment length; a slow-band LL rises with slow-wave amplitude and steepness.
**Implementation.** `morphology.py` on `bip`. Trivial.

### 4.2 Amplitude (RMS / peak-to-peak / slow-band envelope)
**Measures.** The literal amplitude clinicians grade ("high-amplitude delta").
**Helps.** Morgoth gap; severity wording; complements relative power (§7 table: high amplitude vs true
excess).
**Definition.** Per channel: `RMS = sqrt(mean(x²))`, robust peak-to-peak (95th−5th pct), and the
median Hilbert envelope of the 0.5–4 Hz band.
**Implementation.** `morphology.py`. Trivial.

### 4.3 Sharpness / waveform asymmetry
**Measures.** Steepness at peaks/troughs and rise/decay & peak/trough asymmetry — sinusoidal
(rhythmic) vs sawtooth vs sharp/transient morphology.
**Helps.** Rhythmic vs polymorphic; flags sharp/epileptiform-tinged slowing (consistency/QC); Morgoth
gap.
**Definition.** Per detected cycle (from §3.4): peak/trough **sharpness** = magnitude of the local 2nd
derivative at the extremum; **rise-decay asymmetry** = risetime/(risetime+decaytime);
**peak-trough asymmetry** = time-above-midline / period. Aggregate mean/median per channel.
**Implementation.** Reuses §3.4 cycle set. Cheap.

### 4.4 Hjorth parameters
**Measures.** Compact time-domain shape: activity (variance), mobility (~mean frequency), complexity
(~bandwidth).
**Helps.** Cheap morphology summary; mobility is a robust, artifact-tolerant "slowing" index; Morgoth
gap.
**Definition.**
```
activity  = var(x)
mobility  = sqrt( var(x') / var(x) )
complexity= mobility(x') / mobility(x)
```
**Implementation.** `morphology.py` on `bip`. Trivial.

---

## 5. Temporal continuity / intermittency dynamics

feature_spec §3 already covers *cross-segment* prevalence/persistence (longest run, #episodes) on the
band-power z-series — keep that. This family adds **sub-segment** dynamics that distinguish *continuous*
slowing from *intermittent/paroxysmal* slowing (the "I" in FIRDA/TIRDA is *intermittent* by
definition) and *runs* (rhythmic bursts) from scattered waves.

### 5.1 Slow-band envelope duty cycle & burstiness
**Measures.** Within a segment, fraction of time slow activity is "on," and how bursty it is.
**Helps.** IRDA (intermittent by definition) vs continuous polymorphic slowing; Morgoth gap.
**Definition.** From the Hilbert envelope `E(t)` of the 0.5–4 Hz band, with threshold `θ` (e.g. median
+ k·MAD of E over the recording's normal segments):
```
duty_cycle = fraction of t with E(t) > θ
burst_rate = number of supra-θ excursions / second
CV_env     = sd(E)/mean(E)                 (paroxysmal ⇒ high; steady ⇒ low)
```
**Implementation.** `morphology.py`; envelope reused from §4.2. Cheap.

### 5.2 Rhythmic-run length
**Measures.** Length of consecutive regular slow cycles (a "run" of rhythmic delta).
**Helps.** Rhythmic FIRDA/TIRDA ("runs of…") vs isolated polymorphic waves; morphology support for the
"rhythmic delta activity" phrase.
**Definition.** Using the cycle set (§3.4), find the longest / mean run of consecutive cycles whose
period and amplitude stay within tolerance of the running median (a rhythmicity streak). Report max &
mean run length (in cycles / seconds), and count of runs ≥ N cycles.
**Implementation.** Reuses §3.4. Cheap.

---

## 6. Spatial coherence / field

Cross-channel structure over the 18-channel segment array. The current asymmetry features
(recording.py) compare L/R *power*; these add *field topology*, which separates a restricted focal
polymorphic field from a bilaterally synchronous generalized rhythm (FIRDA) — a direct consistency
check on Morgoth's Tier-3 focal/generalized call.

### 6.1 Slow-band inter-channel coherence
**Measures.** Frequency-resolved synchrony between channels in the slow band.
**Helps.** Focal (locally (in)coherent, restricted field) vs generalized/bisynchronous (FIRDA);
Tier-3 consistency.
**Definition.** Magnitude-squared coherence from the multitaper cross-spectra (the DPSS tapers already
computed in `multitaper_psd` give the cross terms for free):
```
C_xy(f) = |S_xy(f)|² / (S_xx(f)·S_yy(f))   averaged over tapers, then over 0.5–4 Hz
```
Report homologous-pair coherence and mean neighbor coherence. High homologous slow coherence ⇒
bisynchronous/generalized; low ⇒ independent focal fields.
**Implementation.** Extend `multitaper_psd` to keep per-taper cross-spectra (moderate memory/compute);
compute for the pairs/neighbors that matter, not all 153 pairs. Moderate cost.

### 6.2 Spatial extent / field size
**Measures.** How many channels are simultaneously slow.
**Helps.** Focal (few contiguous channels) vs generalized (widespread); severity of a focal field.
**Definition.** Per segment, count channels whose slow-band envelope (§4.2) simultaneously exceeds its
own normal threshold; also the size of the largest **contiguous** (montage-adjacent) active cluster.
**Implementation.** `morphology.py` on the 18-channel envelope stack. Cheap (reuses §4.2).

### 6.3 Global field synchrony
**Measures.** Overall spatial synchrony of the slow field.
**Helps.** Generalized rhythmic (high) vs multifocal polymorphic (low); Morgoth gap.
**Definition.** Mean pairwise Pearson correlation of the 0.5–4 Hz band-filtered channel signals over
the segment (a cheap, phase-sensitive alternative to §6.1). Optionally weighted phase-lag index for a
volume-conduction-robust variant.
**Implementation.** `morphology.py`. Cheap (correlation matrix of 18 signals).

---

## Priority order (ROI)

Ranked by (expected gap closed) ÷ (cost). Cheap features that ride on the already-computed `psd` and
`bip` come first.

| # | Feature group | Primary gap | Cost | Rationale |
|---|---|---|---|---|
| **P1** | §1 Band composition: spectral centroid, slow peak freq, spread/bimodality + **calibrated decision rule** | BAND (0.33 → ↑) | Very low | The weakest, most-reported axis; all cheap on existing `psd`; calibratable today against `report_extracted_labels.csv`. Biggest single win. |
| **P2** | §2 Aperiodic/oscillatory decomposition (exponent, offset, peak-over-1/f) + §3.2 spectral entropy + §3.3 Q | Morgoth gap + BAND + rhythmic/polymorphic | Low–moderate | Separates true oscillatory slowing from amplitude/technical (§7 table); aperiodic exponent is a strong unmodeled marker → prime Morgoth-gap candidate; entropy/Q are near-free rhythmicity proxies. |
| **P3** | §4 Time-domain morphology: line length, amplitude/envelope, Hjorth, sharpness | Morgoth gap + focal + severity | Very low | Trivial on raw `bip`; adds amplitude & transient info the spectrum loses; strong cheap distillation candidates. |
| **P4** | §3.1/§3.4 Rhythmicity: autocorrelation index, cycle period/amplitude CV, §5.2 run length | Polymorphic vs rhythmic (FIRDA/TIRDA) | Moderate | The distinction feature_spec §8 says needs morphology; enables the "rhythmic delta activity" wording faithfully. |
| **P5** | §6 Spatial coherence/field: homologous coherence, spatial extent, global synchrony | Focal vs generalized (Tier-3 consistency) | Moderate | Adds field topology beyond L/R power; sharpens focal detection and cross-checks Morgoth's focal/gen branch. |
| **P6** | §5.1 Sub-segment intermittency: duty cycle, burstiness, envelope CV | IRDA intermittency | Moderate | More niche (targets the "intermittent" qualifier); depends on envelope from P3, so cheap once P3 lands. |

**Suggested first sprint:** P1 + P3 together (both are near-free additions inside the existing
`extract.py` segment loop) plus the P1 calibration script — this should move the band axis materially
and add the cheapest Morgoth-gap features. Then P2 for the Morgoth gap, P4 for FIRDA/TIRDA.

## Validation plan (how we'll know it worked)

1. **Band axis:** re-run the scripts/20 report-text agreement with the P1 calibrated call — target
   band agreement well above 0.33 (side/region should stay ≥0.78/0.91, unaffected).
2. **Morgoth gap:** re-run scripts/17 (LR/GBM of our features → Morgoth P) with P2–P3 added — target
   R² above 0.47; read SHAP to confirm aperiodic exponent / line length / entropy carry new signal.
3. **Polymorphic vs rhythmic:** on the subset of reports that state FIRDA/TIRDA/"rhythmic" vs
   "polymorphic," check that §3 features separate the groups (AUC), and that region+rhythmicity
   reproduces the FIRDA(frontal)/TIRDA(temporal) distinction.
4. **Focal:** add §6 features to the focal discrimination (RESULTS §4) and check AUC lift over the
   current `|asym_ch_*_delta|` top discriminator; check Morgoth-focal consistency improves.
5. **Feature selection:** fold all new features into scripts/15 (two-track keep-list, correlation
   clustering + stability selection per report_architecture.md) so we keep only the ones that earn it.
