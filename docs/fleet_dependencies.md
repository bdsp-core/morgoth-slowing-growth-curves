# Fleet run dependencies — code, models, checkpoints, environment (complete inventory)

**Why this exists:** the SAP documents *data* provenance exhaustively, but the clean-room run also depends
on **external code and model checkpoints** that were undocumented — so running it meant hunting for the
Morgoth repo and checkpoints by hand. This file is the single inventory of *everything the fleet needs to
run*, so no piece is a surprise. If the run needs a file/model/env var, it is listed here.

Last verified locally: 2026-07-11 (Mac/MPS). On the AWS box, set `MORGOTH_DEVICE=cuda` and the same layout.

---

## 1. Our code (this repo)

| Piece | Path | Role |
|---|---|---|
| Fleet worker | `scripts/31_segment_master_worker.py` | per-recording → `segment_master` + sidecars |
| Shared ingest helpers | `src/morgoth_slowing/fleet/ingest.py` | config, rclone, EDF resolve, `stage_dir` |
| Extractor | `src/morgoth_slowing/features/extract.py` | PSD, bands, 24 h cap, segmentation |
| Artifact | `src/morgoth_slowing/features/artifact.py` | `usable_mask` (flag, not strip) |
| van Putten metrics | `src/morgoth_slowing/features/vanputten.py` | DAR/DTABR/Q_SLOWING/SEF/BSI/… |
| Regions | `src/morgoth_slowing/features/recording.py` | `_AGG` (6 regions), `_derived` |
| EDF loader | `src/morgoth_slowing/io/edf.py` | `load_edf_referential` (→ 200 Hz referential) |
| Stage map | `src/morgoth_slowing/io/staging.py` | `STAGE` code → W/N1/N2/N3/REM |
| pyhealth shim | `scripts/shims/pyhealth/` | stubs so the Morgoth stager imports in `--predict` |

## 2. External Morgoth code (separate repo — NOT in this repo)

- **Repo:** `~/GithubRepos/morgoth2` (env `MORGOTH2_DIR`). Set to the checkout on the box.
- **Scripts used:** `finetune_classification.py` (sleep stager **and** per-window gate heads, `--predict`),
  `EEG_level_head.py` (EEG-level focal/gen aggregation). `utils.py` imports `pyhealth.metrics` →
  satisfied by our shim (only used for evaluation, never in `--predict`).

## 3. Model checkpoints (the load-bearing binaries)

The worker reads `checkpoints/<name>.pth` **relative to `MORGOTH2_DIR`**. Canonical source of the gate
checkpoints is **`~/GithubRepos/morgoth-viewer/morgoth_checkpoints/`** (link/copy them into
`$MORGOTH2_DIR/checkpoints/`). The stager `ss_hm_1.pth` ships in `morgoth2/checkpoints/`.

| Checkpoint | Size | Role | Canonical location |
|---|---|---|---|
| `ss_hm_1.pth` | ~70 MB | **sleep stager** (`--dataset SLEEPPSG`) | `morgoth2/checkpoints/` |
| `SLOWING.pth` | ~70 MB | per-window **slowing** head → per-segment `p_slowing` | `morgoth-viewer/morgoth_checkpoints/` |
| `NORMAL.pth` | ~70 MB | per-window normal head | `morgoth-viewer/morgoth_checkpoints/` |
| `FOC_SLOWING_EEGlevel.pth` | ~2 MB | EEG-level **focal** aggregator → `p_focal` | `morgoth-viewer/morgoth_checkpoints/` |
| `GEN_SLOWING_EEGlevel.pth` | ~2 MB | EEG-level **generalized** aggregator → `p_generalized` | `morgoth-viewer/morgoth_checkpoints/` |
| `NORMAL_EEGlevel.pth` | ~2 MB | EEG-level normal aggregator | `morgoth-viewer/morgoth_checkpoints/` |

Setup (once, on the run machine):
```bash
CKS=~/GithubRepos/morgoth-viewer/morgoth_checkpoints
for f in NORMAL SLOWING NORMAL_EEGlevel FOC_SLOWING_EEGlevel GEN_SLOWING_EEGlevel; do
  ln -sf $CKS/$f.pth $MORGOTH2_DIR/checkpoints/$f.pth
done
```
(If `morgoth-viewer` is absent on the box, the checkpoints are also archived in Box under the Morgoth
model set — fetch with rclone `box:` into `morgoth-viewer/morgoth_checkpoints/`.)

## 4. Python environment

- **torch 2.13.0**, **timm 0.9.16** (pinned — the Morgoth model class expects this timm API).
- **`KMP_DUPLICATE_LIB_OK=TRUE`** — REQUIRED. Without it the Morgoth subprocess dies on an OpenMP
  double-init (`libomp.dylib already initialized`). The worker now sets it inside every Morgoth command;
  also export it in the parent shell.
- **`PYTORCH_ENABLE_MPS_FALLBACK=1`**, `OMP_NUM_THREADS=1` (set in the Morgoth commands).
- `np.trapz → np.trapezoid` shim lives in `extract.py` (numpy ≥ 2).

## 5. Data access (rclone)

- Binary: `/opt/homebrew/bin/rclone` (env `RCLONE_BIN`).
- Remotes: **`s3:`** — `bdsp-opendata-repository/EEG/bids/...` (pull EDFs, read-only);
  **`box:`** — checkpoint/model archive (if not local); **`bdsp:`** — legacy EDF copy path.

## 6. Environment variables (one place)

| Var | Local (Mac) | AWS box | Meaning |
|---|---|---|---|
| `MORGOTH2_DIR` | `~/GithubRepos/morgoth2` | box checkout | Morgoth code + `checkpoints/` |
| `MORGOTH_DEVICE` | `mps` | `cuda` | inference device |
| `PILOT_VENV` | `$(which python3)` | box venv python | python with torch/timm |
| `MORGOTH_SHIMS` | `scripts/shims` | same | pyhealth shim on PYTHONPATH |
| `RCLONE_BIN` | `/opt/homebrew/bin/rclone` | box rclone | S3/Box access |
| `KMP_DUPLICATE_LIB_OK` | `TRUE` | `TRUE` | OpenMP double-init guard (required) |
| `RUN_GATE` | `1` to run the gate | `1` | per-segment slowing + EEG-level focal/gen |
| `GATE_STEP` | `5` | `5` | window step (s) for the slowing head |
| `MANIFEST` | `data/manifest/report_manifest_v3.parquet` | same | the frozen EEG list |

## 7. Exact run (one recording, end to end)
```bash
export RCLONE_BIN=/opt/homebrew/bin/rclone MORGOTH2_DIR=$HOME/GithubRepos/morgoth2 \
       MORGOTH_DEVICE=mps PILOT_VENV=$(which python3) MORGOTH_SHIMS=$(pwd)/scripts/shims \
       KMP_DUPLICATE_LIB_OK=TRUE RUN_GATE=1 PYTHONPATH=src
python scripts/31_segment_master_worker.py 1
```
Pipeline per recording: resolve EDF on `s3:` → pull → cap 24 h → bipolar → per-15 s multitaper PSD →
artifact flag (retain) → features + van Putten → Morgoth **stage** (ss_hm_1) → Morgoth **gate**
(SLOWING window head → per-segment `p_slowing`; EEG-level heads → `p_focal`/`p_generalized`) →
write `segment_master/eeg_id=<id>/part.parquet` + `recording_meta`/`recording_labels`.

## 8. Known integration notes (verified 2026-07-11)
- The SLOWING window head's per-window CSV carries `pred_class`; capturing a calibrated **probability**
  (softmax) rather than the class index is the remaining refinement for `p_slowing`.
- The `EEG_level_head.py` focal/gen aggregation currently errors on this input; per-segment `p_slowing` is
  captured regardless (the EEG-level call is best-effort and does not block the run). Tracked as a gate
  follow-up.
