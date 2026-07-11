# Bootstrap — run the fleet on a fresh machine

Goal: go from `git clone` to a running fleet on a new box. Everything **reconstructable** is in this repo
(code + docs + the frozen v6 manifest). Three things are NOT and cannot be in git — they are set up
per-machine: (a) the Morgoth model + checkpoints (separate repos, ~500 MB), (b) S3/rclone credentials
(secrets), (c) the 2.4 GB panel source files (pulled from S3). This guide covers all of it.

## What's already in the repo (arrives with `git pull`)
- All run-control code: worker `scripts/31`, ledger `scripts/33`, verify `scripts/32`, pre-flight
  `scripts/129`/`130`, panel staging `scripts/128`, canonical IO `src/morgoth_slowing/io/canonical.py`.
- **The frozen launch manifest** `data/manifest/report_manifest_v6.parquet` (tracked; 27,524 EEGs) + its
  `.meta.json` (sha256) + `preflight_resolution.parquet` + `manifest_rejects.parquet`.
- Reproducibility anchor `docs/run_manifest_index.md` (v6 sha256 = `8ac7a552…`), run order
  `docs/fleet_launch.md`, deps `docs/fleet_dependencies.md`, readiness `docs/RUN_READINESS.md`.
- `requirements.txt` (worker deps only — no torch/timm; those live in Morgoth's venv, §2), `scripts/shims/` (pyhealth shim +
  eeg_level_wrap).

## What is NOT in the repo (set up per-machine)
| Item | Why not in git | How to get it |
|---|---|---|
| Morgoth model repo `morgoth2` | separate repo | `git clone` it; set `MORGOTH2_DIR` |
| 6 checkpoints (~500 MB) | large binaries | copy/link into `$MORGOTH2_DIR/checkpoints/` (fleet_dependencies.md §3) |
| rclone + S3 creds | secrets | install rclone; configure the `s3:`/BDSP remote (read) + a writable run bucket |
| Panel sources (2.4 GB) | too large + PHI-adjacent | `aws s3 sync s3://<run-bucket>/panels/ panels/` (or set `PANEL_ROOT=s3://…`) |
| Worker Python env | machine-specific | `pip install -r requirements.txt` (no torch/timm) |
| Morgoth Python env | separate, conflicting pins | `pip install -r morgoth2/requirements.txt` into `morgoth2/.venv`; `PILOT_VENV` points here (§2) |

The **report pool CSV** (`EEGs_And_Reports.csv`, 1.1 GB) is NOT needed on this machine — it is only used
to *rebuild* the manifest (`scripts/120–130`). v6 is frozen and in the repo, so the fleet run does not
touch it.

## Steps

### 1. Repo + Python env (WORKER venv — Morgoth's env is separate, §2)
```bash
git clone https://github.com/bdsp-core/morgoth-slowing-growth-curves.git
cd morgoth-slowing-growth-curves && git checkout run-v6      # the frozen tag
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt                              # worker deps only — NO torch/timm (they live in Morgoth's venv, §2)
```

### 2. Morgoth model + checkpoints + its OWN venv
```bash
git clone <morgoth2 repo url> ~/morgoth2 && export MORGOTH2_DIR=~/morgoth2
# link the 6 checkpoints into $MORGOTH2_DIR/checkpoints/ (ss_hm_1 stager + NORMAL/SLOWING + 2 EEG-level
# aggregators); canonical source + exact list: docs/fleet_dependencies.md §3.
# Morgoth runs in a SEPARATE venv from the worker (different, conflicting pins — see fleet_dependencies §4):
python -m venv $MORGOTH2_DIR/.venv && $MORGOTH2_DIR/.venv/bin/pip install -r $MORGOTH2_DIR/requirements.txt
#   (skip apex — CUDA-only build; pyhealth is satisfied by scripts/shims. Then set PILOT_VENV to THIS venv.)
```

### 3. rclone + aws CLI + S3
```bash
# install rclone (https://rclone.org), then configure the `s3:` remote (worker resolve_edf lists
# s3:bdsp-opendata-repository/…) + a writable run bucket for panels + outputs.
#   (Apple-Silicon: ad-hoc sign a downloaded rclone — `codesign --force --sign - $(which rclone)` — or it
#    is SIGKILLed on exec.)
rclone listremotes            # confirm the read remote resolves
export RCLONE_BIN=$(which rclone)
# aws CLI is ALSO required (not just boto3): the worker shells out to `aws s3 cp` for panel sources +
# output sync. `pip install awscli` (or system package); confirm `aws --version` resolves on PATH.
```

### 4. Verify the manifest matches the freeze
```bash
python -c "import json,hashlib;p='data/manifest/report_manifest_v6.parquet';\
h=hashlib.sha256(open(p,'rb').read()).hexdigest();\
print('OK' if h==json.load(open(p+'.meta.json'))['sha256'] else 'MISMATCH', h)"
# expect: OK 8ac7a552d5144e1cc424f74d512d4c3a0c23cb13ce875f8710dc2b65ae912b4d
```

### 5. Panels (only for the panel subset; main cohort run does not need them)
Uploaded to the **credentialed** bucket `s3://bdsp-opendata-credentialed/morgoth-slowing/panels/`
(occasionnoise/*.edf + moe/*.mat). Point the worker straight at it:
```bash
export PANEL_ROOT=s3://bdsp-opendata-credentialed/morgoth-slowing/panels   # worker fetch_panel pulls per-file
# credentialed bucket -> the box needs write-less READ creds for it (AWS_ACCESS_KEY_ID/SECRET or an
# instance role with access). Same keys used to upload (AWSKeys/bdsp_opendata_write_accessKeys.csv).
# If PANEL_ROOT is unset, panel rows are skipped and only the 25.6k BDSP recordings featurize.
```

### 6. Run (per docs/fleet_launch.md)
```bash
export MORGOTH_DEVICE=cuda PILOT_VENV=$MORGOTH2_DIR/.venv/bin/python MORGOTH_SHIMS=$(pwd)/scripts/shims
export KMP_DUPLICATE_LIB_OK=TRUE RUN_GATE=1 PYTHONPATH=src
export MANIFEST=data/manifest/report_manifest_v6.parquet OUTPUT_ROOT=/data/run
N=8; for i in $(seq 0 $((N-1))); do SHARD="$i/$N" nohup python scripts/31_segment_master_worker.py > logs/fleet_$i.log 2>&1 & done
# after all shards finish:
python scripts/33_assemble_ledger.py        # -> recording_meta / recording_labels (the run ledger)
python scripts/32_segmaster_summary.py      # verify: schema + stage-conditioned table + figure
aws s3 sync $OUTPUT_ROOT/ s3://<run-output-bucket>/   # collect outputs for the analysis machine
```

## Sanity smoke test before the full run (recommended)
```bash
# 3 EEGs, gate on, no S3 upload — proves the box's Morgoth + S3 + featurize path end to end:
PILOT_MIX=1 PANEL_ROOT=$(pwd)/panels python scripts/31_segment_master_worker.py 1
```

## Notes
- Reproduction is pinned by: tag `run-v6` (code) + `docs/run_manifest_index.md` (manifest sha256) +
  `docs/fleet_dependencies.md` (Morgoth version + checkpoints + env). Same three → identical run.
- torch/timm live ONLY in Morgoth's venv (`morgoth2/requirements.txt`), NOT the worker venv. The old "model
  class expects timm 0.9.16 / newer breaks staging" claim was disproved by the smoke test (Morgoth ran on
  timm 1.0.11). See docs/fleet_dependencies.md §4.
- All worker paths are env-driven (no hardcoded local paths on the run path); `scripts/{127,128,130}` have
  local-scratchpad defaults but are manifest-BUILD tools, not needed to run the frozen v6.
