# Morgoth slowing outputs — where they are and how they key to each EEG

These are the Morgoth head outputs this project consumes as the **gate** (docs/report_architecture.md)
and that can feed other analyses. Produced by running the Morgoth heads (see the run recipe in
`tele-eeg-publishing/MORGOTH_INFERENCE_INSTRUCTIONS.md`); this doc is about the **outputs**.

## The per-EEG slowing probabilities (one row per recording)
Written by the EEG-level step (`EEG_level_head.py --mode predict`) into `<eval_results_dir>/`:
- **Focal slowing** → `pred_EEG_level_FOC_SLOWING.csv`
- **Generalized slowing** → `pred_EEG_level_GEN_SLOWING.csv`
- **Normal vs abnormal** → `pred_EEG_level_NORMAL.csv`

Columns: `file_name, probability, pred_class_p, confidence, pred_class`.
- **`probability`** = probability of that class (focal / generalized slowing). This is the number to use.
- `pred_class` = binary call at 0.5; `confidence` / `pred_class_p` = alternative thresholded views.
- Focal and generalized are **separate heads** → each recording has **both** a focal and a generalized
  probability (not mutually exclusive; a record can be high on both, e.g. multifocal).

## Which EEG each row is
`file_name` = `sub-<BDSPPatientID>_<StartDateTime>` (e.g. `sub-S0001114208778_20190130083848`).
Maps 1:1 to the input recording and to `EEG/eeg-metadata/<site>_eeg_metadata_*.csv` via
**BDSPPatientID** + **StartTime** (the 14-digit `YYYYMMDDHHMMSS` = recording start). Parse those out of
`file_name` to join to a cohort. (In this repo the same id convention is `hashid = "S000<site>" +
OMOP person_id`.)

## Which part of the EEG (time-resolved)
The EEG-level probability is aggregated over the whole recording. For *when* slowing occurs, use the
**window-level** file `<eval_results_dir>/pred_SLOWING_1sStep/<file_name>.csv`:
- one row per window; columns `class_*_prob, pred_class`.
- **row _i_ = window starting at _i × slipping-step_ seconds** from recording start
  (step = `--prediction_slipping_step_second`). window→clock = `StartTime + i*step`.
- per-channel columns indicate roughly *where* on the head. (Focal-vs-generalized split is only made at
  the EEG level; the window file tells you *when*.)

## How this project uses it
`scripts/14_aggregate_gate.py` reads the window/EEG-level slowing outputs → per-recording P(slowing);
`scripts/16_gated_report.py` gates the normative description on it (report slowing only if the Morgoth
head fires), then describes it with our physiological features.
