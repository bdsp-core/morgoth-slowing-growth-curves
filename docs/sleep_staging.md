# Sleep staging (morgoth2)

The Growth_curves feature set is **unstaged** (every segment = "Other"). State-specific norms need a
sleep stage per segment, produced by the **morgoth2** model:
https://github.com/bdsp-core/morgoth2 → `infer_sleep_staging.py` / `run_infer_sleep_staging.sh`.

## What the model needs (from morgoth2)
- **Input: raw PSG**, `.edf` or `.h5` (NOT the feature `.mat` files). H5 = `signals/<ch>` at
  `attrs['sampling_rate']`. Preprocessing: MNE FIR bandpass + notch (50/60 Hz), ÷100 (µV/100),
  window 10 s @ 200 Hz → [N,10,200].
- **Checkpoint:** `checkpoints/finetune_sleep_staging/checkpoint-best.pth` (in the morgoth2 repo;
  likely git-LFS — confirm it pulled).
- **Compute:** a CUDA **GPU** (`CUDA_VISIBLE_DEVICES=0`), torch + mne + einops (`environment.yml`).
- **Output:** one CSV per recording — `window_idx, t_start_sec, predicted_stage,
  stage_name, W_prob..REM_prob`, at `STRIDE_SEC` (10 s default). Stages 0=W 1=N1 2=N2 3=N3 4=REM.

## The gap to close
1. **Get the raw EEG** for the 12,379 Growth_curves recordings. It is **not** in
   `s3://.../morgoth2/data/internal_dataset/` (only feature sets there). The staging script's example
   path `/data/sleep/S0001_age_stratified_data/` suggests the raw lives on the **myelin/BDSP infra**
   — locate it (ask JJ/Brandon) or export from the BDSP signal store keyed by
   `person_id` + `eeg_datetime` (filenames give both).
2. **Run inference on a GPU box** (myelin), not this Mac (no CUDA; 12k × ~10-min recordings is
   infeasible on CPU). Batch over the folder with `run_infer_sleep_staging.sh`.
3. **Align stages → our 15-s segments.** Staging is per 10-s window; our features are per 15-s
   segment (`start`/`end` in `res`). Map by time overlap (majority stage within each 15-s segment).

## Integration point in this repo
`io/staging.py` (to add) will read a morgoth2 `<subject>_predictions.csv`, collapse 10-s windows to
each 15-s segment by max-overlap, and return a per-segment stage series that replaces the "Other"
column before norms are fit (Phase 3). Until then, `scripts/04_fit_reference_models.py` can run
**stage-agnostic** as a sanity check.

## Recommended sequence
1. Confirm raw-EEG location + access. 2. Verify the checkpoint is present (LFS). 3. Run staging on a
**small pilot** (e.g. 20 recordings spanning ages) on a GPU. 4. Validate stage distributions look
sane. 5. Batch the full set. 6. Wire `io/staging.py` and re-fit norms per stage.
