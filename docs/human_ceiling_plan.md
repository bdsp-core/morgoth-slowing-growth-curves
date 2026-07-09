# The human ceiling — what MoE and OccasionNoise contain, and how to use them

Explored 2026-07-09. These two datasets supply the missing anchor identified as **V2** in
`docs/validation_plan.md`: what two neurophysiologists agree on **with each other**. Without it, "equal value
to a clinical neurophysiologist" is not merely unproven — it is unfalsifiable.

Box paths (read via `rclone`, remote `box:`):
`Brandon - DeID/0_People/ChenXiSun/ChenXiSun/Morgoth1/Datasets/{MoE,OccasionNoise}`

**PHI/identity note.** MoE label columns are the raters' *usernames* (real people, incl. `bwestove`). Never
commit rater names. Anonymize to `R01…R18` in every derived artifact. OccasionNoise already uses integer `uid`.

---

## 1. What is actually in them

### OccasionNoise — recording-level, and the better match to our design

| item | value |
|---|---|
| EEGs | **100** (`edf/1.edf` … `edf/121.edf`, non-contiguous ids) |
| format | EDF, **20 channels**, **200 Hz**, ~**50 min** each, raw/unfiltered, zero-padded to whole seconds |
| channels | Fp1 Fp2 F3 F4 F7 F8 C3 C4 Cz Fz Pz P3 P4 P7 P8 O1 O2 T7 T8 + EKG |
| age/sex | in the EDF **patient field**, e.g. `"11.0 F X X"` → 11.0 y, female |
| raters | **18** (`uid`), 15–18 raters per EEG, median 100 EEGs per rater |
| axes | `FS` focal epileptiform, **`FN` focal non-epileptiform (= focal slowing)**, `GS` generalized epileptiform, **`GN` generalized non-epileptiform (= generalized slowing)** |
| occasions | **Part I and Part II** — 15 raters re-read the same EEGs (1,335 repeat rows) → **within-rater test–retest** |
| reference | `Files` sheet gives each EEG a category **derived from its signed report** — the same label type our main analysis uses |
| design | balanced: 20 focal-epileptiform / 20 generalized-epileptiform / 20 focal-non-epileptiform / 20 generalized-non-epileptiform / 16 normal / 4 normal-variant |

`startdate` is de-identified to `00.00.00`, which **pyedflib rejects**. `mne.io.read_raw_edf` reads it fine
(verified). Channel names use the modern T7/T8/P7/P8 convention → map to T3/T4/T5/T6 for our montage.

### MoE — event-level, band-resolved

| item | value |
|---|---|
| structure | `labels/{r1,r2,r3}_csv_labels_20241028/moe_<n><category>.csv`; one CSV per category, **raters as columns**, events as rows |
| raters | **18** (round 2), 13 (round 3) |
| events | round 2: 1,000; round 3: 962 — **zero shared event ids** |
| categories | 57 in rounds 2–3 (45 in round 1), incl. **`focalslowing-{alpha,beta,delta,theta}`** and **`genslowing-{…}`**, plus stages (W/N1/N2/N3/REM), IEDs, artifacts, burst-suppression |
| cohort mix | of 1,000 round-2 events, **500 are BDSP** (`sub-S000…_task-rEEG`), 500 are `icare_*` (cardiac-arrest ICU) |
| BDSP linkage | 493 unique `bdsp_id`; **only 157 in `labels_unified`, 145 in `channel_stage_features`** |
| signals | `events_raw/*.mat`, `events/*.mat` (1,761 / 2,761 files) — the event snippets |

**Two important limits.** (i) Rater coverage is wildly unbalanced: votes per rater range **7 → 1,000**; only
13 of 18 covered ≥500 events. Restrict to well-covered raters. (ii) Rounds are **disjoint event batches**, not
repeat reads, so **MoE yields no within-rater test–retest.** Only OccasionNoise does.

**Open question for ChenXi Sun:** what distinguishes rounds r1/r2/r3 (taxonomy grew 45→57), and were raters
blinded to each other between rounds?

---

## 2. The ceiling, measured (already computed)

### Between-rater agreement, OccasionNoise Part I (n = 100 EEGs, 18 raters)

| axis | Fleiss κ | pairwise Cohen κ (median [IQR]) |
|---|---|---|
| Focal epileptiform (FS) | 0.585 | 0.643 [0.558–0.704] |
| **Focal slowing (FN)** | **0.373** | **0.394 [0.285–0.461]** |
| Generalized epileptiform (GS) | 0.739 | 0.805 [0.731–0.859] |
| **Generalized slowing (GN)** | **0.450** | **0.451 [0.346–0.534]** |

**Slowing is the least reliable thing experts judge** — markedly worse than epileptiform discharges.

### Expert vs consensus (leave-one-out majority of the other raters)

| axis | sensitivity | specificity | balanced accuracy | κ |
|---|---|---|---|---|
| **Focal slowing** | 0.703 | 0.899 | **0.801** (range 0.578–1.000) | 0.526 |
| **Generalized slowing** | 0.735 | 0.884 | **0.809** (range 0.686–0.943) | 0.576 |

### Within-rater, same expert re-reading the same EEG (Part I vs Part II; 15 raters, 1,335 pairs)

| axis | raw agreement | κ |
|---|---|---|
| Focal epileptiform | 0.913 | 0.716 |
| **Focal slowing** | 0.873 | **0.563** |
| Generalized epileptiform | 0.955 | 0.832 |
| **Generalized slowing** | 0.879 | **0.642** |

An expert does not even reproduce **their own** slowing call reliably.

### Signed report vs expert panel

On EEGs whose **signed clinical report** called them focal non-epileptiform, only **50.8%** of experts marked
focal slowing. For generalized non-epileptiform, **64.4%**. Normals: 1.5% / 4.8%.

This bounds every agreement number in our paper. Our "agreement with the report" cannot exceed what experts
themselves achieve against the report.

### MoE — band-resolved slowing, round 2, 13 well-covered raters

| category | prevalence | pairwise Cohen κ (median) |
|---|---|---|
| focalslowing-delta | 0.117 | 0.352 |
| **focalslowing-theta** | 0.028 | **0.087** |
| genslowing-delta | 0.392 | 0.323 |
| genslowing-theta | 0.356 | 0.317 |

Experts barely agree on the **band** of slowing at all. This directly re-frames our band agreement of 0.74.

---

## 3. Plan

### Phase A — OccasionNoise: our model vs the expert panel (primary; highest value)

1. **Ingest.** Pull all 100 EDFs (~2 GB). Read with MNE (pyedflib chokes on the de-identified `startdate`).
   Map T7→T3, T8→T4, P7→T5, P8→T6; drop EKG. Parse **age and sex from the EDF patient field**.
2. **Score with the existing pipeline, unchanged.** Bipolar double-banana → artifact rejection → 15-s segments
   → multitaper → `features_31`; run the stager; compute stage-specific normal-referenced z against our
   **routine (alert) W/N1 reference**. No refitting, no tuning: this is an external test set.
3. **Targets.** (a) expert-consensus majority for FN and GN; (b) the **consensus proportion** (fraction of
   experts who marked it) as a graded target; (c) the signed-report category, the label type we already use.
4. **The headline figure.** Plot our ROC against consensus-majority for focal and generalized slowing, and
   **overlay each individual expert as a single (1−specificity, sensitivity) point**, with the mean expert
   operating point marked. The question the figure answers in one glance: *does our curve pass above the cloud
   of experts?* Add the within-rater test–retest κ as a reliability band.
5. **The claim this licenses.** Not "AUROC 0.875" in a vacuum, but *"our agreement with the consensus read is
   X against an expert-vs-consensus ceiling of 0.801 (focal) / 0.809 (generalized)."* That is the only
   defensible form of the comparative claim.

### Phase B — the graded target that may rescue the severity axis

The **consensus proportion** — what fraction of 18 experts saw slowing — is a *graded, human, quantitative*
target. It is not an adjective, it is a measurement of **conspicuity**.

Test: does our deviation z correlate with consensus proportion? If it does, we have a severity-like axis
validated against humans, recovering honestly what the report adjective failed to give us (V1's null).

**Say plainly what it is.** This measures *how conspicuous the slowing is*, not *how severe the pathology is*.
Those coincide often but not always. Pre-register the prediction and the interpretation **before** running it,
so this cannot become another post-hoc rescue of a null (see the standing risk in V4).

### Phase C — MoE: the band ceiling, and focal-vs-generalized

1. Anonymize raters → `R01…R18`; keep only the 13 with ≥500 events.
2. Report between-rater κ per band and per focal/generalized, with bootstrap CIs. This contextualizes our band
   agreement (0.74) against a ceiling that appears to be **κ ≈ 0.09–0.35**.
3. Features: 145 of the BDSP recordings are already in `channel_stage_features`; for the rest, compute from
   `events_raw/*.mat` (structure not yet inspected — check channels/fs/duration first).
4. Consider excluding the `icare_*` events (cardiac-arrest ICU) — a different population from our norms.

### Phase D — write-up

- New Results section **"The human ceiling for slowing"** + figure from Phase A.
- Rewrite every agreement claim as *"X against a ceiling of Y."*
- Revise the V1 severity null: it must now be read against expert band κ ≈ 0.09–0.35 and within-rater slowing
  κ ≈ 0.56–0.64. Our failure to reproduce the adjective is at least partly a **ceiling effect**, not purely
  our defect — but this must be argued with the numbers, not asserted.
- `bwestove` is a rater in MoE. Disclose it, and exclude that rater from any analysis used to validate a
  system this author built.

---

## 4. Caveats to state up front

1. **Enriched prevalence.** OccasionNoise is balanced by design (20/20/20/20/16/4), not natural prevalence.
   AUROC and κ transfer; PPV and prevalence-dependent metrics do **not**.
2. **Different recordings.** ~50-min EEGs, unknown provenance relative to our routine/overnight split. Check
   the stage distribution before applying the vigilance-matched routine reference; if they contain substantial
   sleep, report both routine- and union-referenced scores.
3. **Whole-recording labels vs segment scores.** Experts marked the whole EEG; our score is a recording-level
   summary of W/N1 segments. Same granularity, but the expert saw the entire study including sleep.
4. **No `bdsp_id` linkage for OccasionNoise**, so nothing can be reused — the pipeline must be run fresh. That
   is a feature: it makes this a genuine **external validation set**.
5. **MoE rater imbalance** (7–1,000 events) and **disjoint rounds**; no within-rater estimate available there.
6. **Consensus is not truth.** A majority of experts can be wrong together, and for sleep slowing we have
   argued they systematically are (V4a). Report agreement *with consensus*, never *accuracy*.
