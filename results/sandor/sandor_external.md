# Sandor 60-EMU — external pipeline run + feasibility findings

**What this is.** A test of running OUR interpretable slowing pipeline end-to-end on the **Sandor 60-EMU**
dataset (box: `Brandon - PHI/Datasets/Sandor_60EMU` — 60 scalp-EEG EMU clips, ~20 min each, 1024 Hz,
average-referenced `EEG Fp1-AVGloro` montage; ratings in `E-ratings TimepointsExtracted.xlsx`) — a dataset
the model has never seen. `scripts/sandor_external_validation.py`.

## Headline: the pipeline runs on brand-new external EDFs ✅

Our front-end ingested and scored **55/60** clips end-to-end with no dataset-specific tuning beyond one
channel-name fix (harmonizing `EEG Fp1-AVGloro` + new-nomenclature T7/T8/P7/P8 → our canonical 10-20):
EDF → referential (200 Hz) → 18 bipolar → per-15 s multitaper features → age (from the EDF header) →
age-matched deviation z against `grid_norm.json` → per-recording slowing amount + focal descriptors +
a generated description. **This confirms the extraction/deviation pipeline generalizes to external data.**

## But three things must be fixed before this is a VALID slowing evaluation

This run is *not* a slowing validation, and the numbers below should not be read as one — for three concrete
reasons it surfaced:

1. **Sleep staging is required here (the biggest issue).** **44 of 55 clips are sleep-heavy** (our crude
   high-δ / low-α flag). The event timepoints in the ratings span day and night (02:00, 05:45, 19:27), so
   most clips contain physiologic sleep. We scored them **wake-referenced** (the Morgoth `ss_hm_1` stager is
   present at `~/GithubRepos/morgoth2/checkpoints/ss_hm_1.pth` and torch/MPS work, but it is **not wired**
   for arbitrary local EDFs in this script), which **inflates the slowing score of every sleep clip** —
   normal N2/N3 delta is read as excess against the wake norm. The pipeline's whole point is per-stage
   normalization; this dataset needs it. Wiring the stager (reuse `scripts/31`'s `fleet.ingest.stage_dir`
   path) is the single change that makes the scores meaningful.
2. **Ages are de-identification-shifted.** 9/55 clips carry implausible header ages (>90, up to 118 y),
   so the "age-matched" norm uses wrong ages for them. Real ages (or a ≥90 cap) are needed.
3. **The labels are the wrong task.** The ratings are **E / NE** (balanced 30/30) with marked **event
   timepoints** from **3 raters** — this is an **epileptiform-discharge** interrater study (Beniczky), **not
   slowing**. A slowing validation needs slowing ground truth (the "AKS score"? — confirm the intended
   labels / dataset).

## Exploratory only — do NOT interpret as a result

With all three caveats live (sleep-confounded, wrong ages, wrong task), our wake-referenced slowing score vs
the epileptiform E/NE gold standard gave **AUROC 0.60** (E median amount_z +1.42 vs NE +1.18; n=55).
`figures: results/sandor/sandor_amount_by_gold.png`. This is uninformative noise — expected, since a slowing
score need not (and here cannot cleanly) separate an epileptiform label.

## To turn this into a real external validation

- **Wire the `ss_hm_1` stager** into the external path (or run the 60 EDFs through `scripts/31` with
  `MORGOTH2_DIR=~/GithubRepos/morgoth2`, `KMP_DUPLICATE_LIB_OK=TRUE`) → proper per-segment stages → valid
  stage-matched deviation. Then re-run the Morgoth-free detector.
- **Get real ages** (cap ≥90) and **confirm the slowing labels** (is there an "AKS"/slowing rating, or is
  Sandor the intended dataset at all?).
- Then evaluate our slowing detector against the confirmed slowing labels, exactly as on OccasionNoise.

## Questions for MBW

1. Is **Sandor_60EMU** the dataset you meant by "SB / sandor aks score AI dataset"? Its labels look
   **epileptiform (E/NE)**, not slowing. Is there a separate slowing / "AKS score" label set (perhaps in a
   Chenxi *morgoth-1* folder I haven't found — nothing matched `morgoth`/`chenxi` in box)?
2. Should I **wire the sleep stager** (it's available locally) and re-run the full staged pipeline? That is
   the remaining work to make this a genuine external validation.

*Outputs: `results/sandor/sandor_scores.parquet` (per-recording), `sandor_amount_by_gold.png`. Raw EDFs live
in the session scratchpad (not committed; PHI). Ages >89 are de-identification artifacts.*
