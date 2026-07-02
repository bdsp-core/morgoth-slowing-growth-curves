# Project Plan — Morgoth Slowing Growth Curves

**Goal.** Build *normative growth curves* (age × sex percentile curves) for quantitative EEG
slowing features, per sleep/wake state, so that the [morgoth-viewer](https://github.com/bdsp-core/morgoth-viewer)
automated-report pipeline can characterize **pathological slowing** — distinguishing
**focal vs. generalized** slowing, accounting for **sleep stage**, and emitting a clinician-style
verbal statement backed by a reproducible quantitative substrate.

Example target output sentences:

> *"Awake: frequent moderate right temporal delta slowing, present in 34% of artifact-free awake
> segments; right temporal delta burden 4.1 SD above age/state norms; right–left temporal delta
> asymmetry 3.3 SD above normal; maximum continuous run 5.0 minutes."*

> *"Abnormal due to generalized delta slowing with paucity of faster (alpha/theta) activity."*

---

## 1. Scientific framing

Slowing is not one number. Following Dr. Jing's feature framework (see
[docs/feature_spec.md](docs/feature_spec.md)), we score along the same axes clinicians use —
**location, band, amplitude, continuity, symmetry, and state** — via a hierarchical pipeline:

```
15-s segment z-scores  →  time burden  →  spatial / laterality burden
   →  state-level patient z-score  →  topographic class  →  verbal phrase
```

Key principles carried into the design:
- **State-specific norms.** Delta in N3 is normal; delta in alert wake is not. Norms are built
  separately for **eyes-open wake, eyes-closed wake, drowsy/transitional wake, N1, N2, N3, REM**.
- **Reference *subjects*, not segments, are the unit of analysis.** A 30-min EEG is not 120
  independent observations. Segment-level norms are built, but patient-level scores are validated
  by leave-one-subject-out (LOSO) / subject-level bootstrap.
- **Relative power and ratios**, not just absolute power (absolute delta inflates with amplitude,
  montage/reference, breach, artifact). Store DAR, TAR, relative delta/theta, LF AUC, SEF, etc.
- **Empirical percentile → z** patient-level scoring: score every *normal* control as if a patient
  (against a model excluding them) to get a null burden distribution, then map a patient's burden to
  `Z = Φ⁻¹(F_norm(burden))`. This is the "N SD above normal" number that is actually meaningful.
- **Age as a continuous variable** (GAM / GAMLSS / quantile regression), not coarse bins — this is
  what makes them *growth curves* rather than lookup tables.

---

## 2. Data sources

All on AWS S3, bucket `bdsp-opendata-credentialed` (credentialed access required — see
[docs/data_sources.md](docs/data_sources.md)).

| Purpose | S3 path |
|---|---|
| **Normative feature set** (build growth curves) | `s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/` |
| **Focal-slowing examples** (validation / positives) | `s3://bdsp-opendata-credentialed/morgoth1/data/internal_dataset/FOCALSLOWING/` |
| **Generalized-slowing examples** (validation / positives) | `s3://bdsp-opendata-credentialed/morgoth1/data/internal_dataset/GENSLOWING/` |

**Open question to resolve first (Phase 0):** does `Growth_curves/` already contain
*precomputed segment-level features with sleep stages* (what the framework assumes), or raw/BIDS
EEG that we must featurize ourselves? This changes disk footprint and compute by 1–2 orders of
magnitude. See §7.

### 2.1 Age (and sex) at EEG — via OMOP  *(prerequisite for everything)*

Age is the **x-axis of every growth curve**, so we must have a trustworthy age-at-EEG for every
subject before using them. Unless age is already in the Growth_curves metadata (check first), derive
it from the **BDSP de-identified OMOP database** (`bdsp_omop`, Aurora Postgres) — see
[docs/omop-query-instructions.txt](docs/omop-query-instructions.txt), implemented in
[src/morgoth_slowing/io/omop.py](src/morgoth_slowing/io/omop.py):

- **BDSP id = OMOP `person_id`.** Join `work_meem.bdsp_recording_detail` (one row per EDF, has
  `s3_path`, `start_time`, `modality`) → `omop_prod.person` (`birth_datetime`, `gender_concept_id`).
- `age_at_eeg = (recording start_time − birth_datetime) / 365.25`; sex from `gender_concept_id`
  (8532=F, 8507=M).
- De-identified dates are shifted per-patient but **internally consistent**, so within-patient date
  arithmetic (EEG time − DOB) is valid even though absolute calendar dates are not.
- Match each EEG to its feature/segment source via `s3_path` in `bdsp_recording_detail`.
- Access needs an SSH tunnel to `localhost:5433` + read-only creds (ask Brandon; nothing committed).

Deliverable: an age/sex table keyed by subject + s3_path, QC'd for missing/implausible ages, joined
into the control cohort and every scored patient.

---

## 3. Finding the control group (lifespan-representative "normal")

This is a first-class task, not an afterthought — the growth curves are only as good as the
"normal" definition. **We must not assume JJ already did this**; Phase 1 audits it explicitly.

**Definition of a control.** A subject whose EEG was **clinically reported as normal** (no
epileptiform activity, no pathological slowing, no focal abnormality), on **no strongly
EEG-altering medication** where determinable, with a technically adequate recording and enough
usable (artifact-free, staged) segments per state.

**Coverage target — even representation across the lifespan.** Stratify by:
- **Age bands** (e.g. 0–2, 3–5, 6–12, 13–17, 18–29, 30–44, 45–59, 60–74, 75+), and
- **Sex**.

Produce a **coverage matrix** (age band × sex × state) with subject counts and total usable
segment-minutes per cell. Flag under-populated cells (children, very old, REM in short routine
EEGs are the usual gaps). Deliverable: `notebooks/01_control_group_selection.ipynb` +
`scripts/02_build_control_cohort.py` emitting `data/derived/control_cohort.parquet` and a coverage
report.

**Where the "normal" label comes from.** Options, in priority order — confirm which is available:
1. Structured normal/abnormal flags already in the Growth_curves metadata (ideal).
2. NLP/keyword parse of the free-text clinical EEG report ("normal EEG", "no epileptiform…").
3. Manual expert confirmation on a sample for QC.

**Handling sparse cells.** Where a cell is thin, (a) widen the continuous age model rather than
hard-binning (GAMLSS borrows strength across ages), and (b) explicitly report reduced confidence
(wide CIs) rather than silently extrapolating.

---

## 4. Feature computation

Per 15-s segment, per channel/region, per band — implemented in `src/morgoth_slowing/features/`:

- **Spectra:** multitaper PSD (mirror morgoth-viewer's parameters for consistency).
- **Band power:** δ 0.5–4, θ 4–7, α 8–13, β 13–30, broadband 0.5–30 (log power).
- **Slowing features:** absolute δ/θ/LF, relative δ/θ, **DAR** (α/δ), **TAR** (α/θ), median
  frequency, spectral edge frequency, alpha peak frequency, low-frequency spectral AUC.
- **Regions:** aggregate channels → L/R frontal, temporal, central, parietal, occipital (+ midline).
- **Asymmetry:** homologous **left–right log ratios** per region pair per band.

**Critical constraint:** *identical preprocessing for reference and patient* — same montage,
reference, filters, notch, sampling rate, artifact rejection, channel interpolation, band edges.
Artifact/eye-movement/muscle/epileptiform/HV/photic/arousal segments are excluded or annotated.

---

## 5. Normative modeling & scoring

`src/morgoth_slowing/norms/` and `src/morgoth_slowing/scoring/`:

1. **Reference model** per (state, region, band): feature ~ smooth(age) × sex, robust
   (median/MAD, GAMLSS, or quantile regression). Emits percentile curves = the growth curves.
2. **Segment z-score:** `z = (logP − μ_age,state,r,b) / σ_age,state,r,b`.
3. **Burden** (best single number): `Burden = (1/T) Σ max(z − τ, 0)` — combines prevalence &
   severity, with τ≈2 calibrated on held-out normals. Also compute prevalence, conditional
   severity, longest run, episode count/duration.
4. **Patient-level z** via empirical percentile→z against the LOSO null burden distribution.
5. **Asymmetry z** the same way, from the homologous-ratio reference model.
6. **Topographic classification** (`scoring/topography.py`): focal / lateralized / generalized /
   multifocal from per-region burden + a **dominance ratio** = max-region burden / median of
   others. Thresholds calibrated against expert labels, not set theoretically.

---

## 6. Discrimination analysis & report generation

- **Which features carry signal?** Overlay individual patients on the growth curves, colored by
  clinical label (normal / focal-slowing / generalized-slowing), per age band and state. Quantify
  separation (AUC, effect size) per feature to find the discriminative ones. Use the
  FOCALSLOWING / GENSLOWING example sets as labeled positives.
- **Sanity checks:** curves monotonic/physiologically plausible with age; N3 shows expected high
  delta; children show expected higher slow power; LOSO normals sit near the middle of their own
  null (calibration check); asymmetry ~0 in symmetric normals.
- **Report phrase generation** (`report/phrase.py`): deterministic template
  `[state] [prevalence-word] [severity-word] [location/laterality] [band] slowing (quantitative
  parenthetical)`, generated *from the quantitative table*, using ACNS-style prevalence words
  (rare/occasional/frequent/abundant/continuous) and provisional severity words (mild/moderate/marked).
  **Caveat baked in:** spectrum can't distinguish polymorphic vs. rhythmic delta vs. periodic vs.
  artifact — phrase notes that morphology review may be needed.

---

## 7. Disk space — assessment

**Local free space: ~7.1 TiB** on `/` (checked). Verdict depends on what `Growth_curves/` actually
contains (Phase 0 resolves this):

| Scenario | Rough footprint | Comfortable? |
|---|---|---|
| Precomputed **segment feature tables** (parquet/npz) | GBs–low tens of GB | **Easily** |
| Precomputed **multitaper spectrograms** per subject | tens–low hundreds of GB | **Yes** |
| **Raw / BIDS EEG** for a lifespan control cohort we must featurize | 0.1–few TB | **Probably**, but tight if it's multi-TB; featurize then discard raw, or stream from S3 |

**Bottom line:** for the feature-level use case (which the framework assumes) there is plenty of
room. If it turns out to be raw EEG in the multi-TB range, we'll process in batches (pull → featurize
→ store features → drop raw) rather than mirroring the whole bucket. First action in Phase 0 is to
measure it: `aws s3 ls --recursive --summarize <path>` (or an rclone S3 remote) — I could not size
it here because AWS credentials / CLI aren't installed on this machine yet.

---

## 8. Phased roadmap

- **Phase 0 — Access & inventory.** Install `aws`/`gh`, load BDSP credentials, measure the three S3
  paths, determine feature-level vs. raw, **and stand up the OMOP tunnel to resolve age/sex at EEG
  for every subject** (§2.1). Deliverable: `notebooks/00_data_inventory.ipynb`, an age/sex table,
  data dictionary in [docs/data_sources.md](docs/data_sources.md).
- **Phase 1 — Control cohort + lifespan coverage audit.** Define "normal", build cohort (joined to
  the OMOP age/sex table), produce the age×sex×state coverage matrix, flag gaps. (§3)
- **Phase 2 — Feature pipeline.** Port/confirm multitaper + band/ratio/asymmetry features,
  aligned with morgoth-viewer preprocessing. (§4)
- **Phase 3 — Reference models / growth curves.** Fit continuous age×sex percentile models per
  state/region/band; export curves + sanity plots. (§5.1)
- **Phase 4 — Scoring engine.** Segment z → burden → patient z → asymmetry → topography, with LOSO
  calibration. (§5.2–5.6)
- **Phase 5 — Discrimination study.** Overlay labeled normal/focal/generalized cases; rank features
  by discriminative power. (§6)
- **Phase 6 — Report generation + morgoth-viewer integration.** Table→phrase module; wire into the
  viewer's report path.

---

## 9. Open questions for the team

1. Does `Growth_curves/` hold precomputed features (+ sleep stages + normal/abnormal labels), or raw
   EEG? → sets Phase 0/2 scope.
2. Is there an existing curated control list from JJ, and does it cover the full lifespan? (§3)
3. Source of the normal/abnormal + focal/generalized labels — structured field vs. report NLP?
4. Which montage/reference does morgoth-viewer use, so features match exactly? (§4)
5. Pediatric scope — include young children (very different norms) or adults-first?
