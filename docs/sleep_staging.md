# Sleep staging (morgoth2) — runbook

Goal: assign a sleep stage (W/N1/N2/N3/REM) to each 15-s Growth_curves segment so norms can be built
per stage (v2). The Growth_curves feature set is unstaged (all "Other"); staging runs on the **raw
EEG** with the morgoth2 model. **Feasibility confirmed 2026-07-02** — reverse-engineered end to end
below; the only real blocker is Python-env isolation (see §5).

## 1. Raw data — available and matches 1:1
`s3://bdsp-opendata-credentialed/morgoth1/data/internal_dataset/{NORMAL,FOCALSLOWING,GENSLOWING}/segments_raw/`
- `NORMAL` 83.5 GiB (4,916), `FOCALSLOWING` 18.7 GiB, `GENSLOWING` 50.7 GiB. Filenames match the
  feature files exactly. NORMAL pulled to `data/raw/segments_raw/normal/` via `bdsp:` rclone remote.
- Format (MATLAB v7.3 / HDF5, read with h5py): `Fs` (200), `channels` (19 referential 10-20 EEG:
  Fp1,F3,C3,P3,F7,T3,T5,O1,Fz,Cz,Pz,Fp2,F4,C4,P4,F8,T4,T6,O2 + EKG), `data` (120000×20 =
  **600 s continuous @ 200 Hz**), `score` (label string, e.g. "focal slowing"). Continuous → ideal
  for the stager.

## 2. Model — on S3
`s3://bdsp-opendata-credentialed/morgoth2/models/202605/morgoth/`
- Window-level 5-class stager: **`ss_hm_1.pth`** (referenced by run_predict) — NOT in this S3 prefix;
  **`SLEEPPSG.pth` is the usable substitute** (verified: same arch `base_patch200_200`, `head`=5,
  embed 200, depth 12; saved `args`: nb_classes=5, patch_size=200, data_format=mat). Ask whoever
  manages the models for `ss_hm_1.pth` if the exact production stager is needed.
- EEG-level aggregator: `SLEEPPSG_EEGlevel.pth`. Also present: `SLEEPPSG_6class.pth`,
  `SLEEPPSG_arousal.pth`.
- Model def: `morgoth2/backbone.py::base_patch200_200`. Standalone Mac path: `run_predict_mac.py`.

## 3. Exact command (Mac / MPS) — from run_predict_mac.py SLEEP block
```bash
cd morgoth2
PYTORCH_ENABLE_MPS_FALLBACK=1 OMP_NUM_THREADS=1 python finetune_classification.py \
  --abs_pos_emb --model base_patch200_200 --predict \
  --task_model checkpoints/SLEEPPSG.pth --dataset SLEEPPSG --data_format mat --sampling_rate 0 \
  --already_format_channel_order no --already_average_montage no --allow_missing_channels yes \
  --max_length_hour no --eval_sub_dir <folder_of_raw_mat> --eval_results_dir <out> \
  --prediction_slipping_step_second 1 --polarity 1 --rewrite_results no --num_workers 0 --device mps
```
`sampling_rate 0` = read Fs from the file. Output: per-file predictions at 1-s step, 5-class.

## 4. Dependencies
torch, torchvision, mne, einops, timm, h5py (installed in analysis venv) **plus** `tensorboardX`,
`mat73`, `pyhealth` (utils.py imports these; pyhealth only for metrics, unused in predict).

## 5. ⚠️ The real blocker: environment isolation
`pyhealth` pins **pandas<2**, which conflicts with the analysis stack (tableone/pandas≥2). Do NOT
install morgoth2's deps into the analysis venv. **Create a separate venv** (or use
`morgoth2/environment.yml`) for staging:
```bash
python -m venv .venv-staging && . .venv-staging/bin/activate
pip install torch torchvision mne einops timm h5py tensorboardX mat73 pyhealth
```
A pilot on 3 files reached model load on MPS; only this env conflict stopped it. No fundamental issue.

## 6. After staging
1. Parse morgoth2 output (per-file 1-s stage predictions) → majority stage per 15-s Growth_curves
   segment (align by `start`/`end` in `res`).
2. Replace the "Other" stage column in `segment_features` / the `res` loader.
3. Re-run `scripts/04` and `scripts/06` grouping by stage → **stage-specific growth curves** and
   discrimination (the v2 goal: is delta in N2/N3 vs wake abnormal?).
4. **Validate** stage distributions before trusting: routine EEG clips should be mostly W with some
   drowsy/N1/N2; cross-check a sample against the `morgoth1/.../SLEEPSTAGING` labeled set.

## Status
Pilot reached MPS model-load; blocked only by the pandas/pyhealth env conflict (§5). Raw NORMAL
downloading. Everything else (command, checkpoint, format, mapping) is settled — this is a clean
pickup in a dedicated venv.
