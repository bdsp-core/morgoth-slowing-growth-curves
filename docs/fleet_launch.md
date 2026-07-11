# Fleet launch (AWS) — turnkey run of the clean-room pipeline

Prereqs: `docs/fleet_dependencies.md` (code, checkpoints, env). The worker `scripts/31_segment_master_worker.py`
is validated end-to-end (features + van Putten + Morgoth stage + per-segment gate). This is how to run it at
scale on the AWS GPU box.

## 0. One-time setup on the box
```bash
export MORGOTH2_DIR=/path/to/morgoth2 MORGOTH_DEVICE=cuda PILOT_VENV=$(which python)
export MORGOTH_SHIMS=$(pwd)/scripts/shims RCLONE_BIN=$(which rclone)
export KMP_DUPLICATE_LIB_OK=TRUE RUN_GATE=1 PYTHONPATH=src
export MANIFEST=data/manifest/report_manifest_v6.parquet     # KNOWN-GOOD: every BIDS row provably resolves (§0a)
export PANEL_ROOT=s3://<run-bucket>/panels                   # where §0b uploaded the panel EDF/MAT files
# link the 6 checkpoints into $MORGOTH2_DIR/checkpoints/ (see fleet_dependencies.md §3)
```
BDSP recordings stream from the open-data S3 bucket via rclone (worker `resolve_edf`). The **panel** EEGs
(OccasionNoise + MoE) are NOT in that bucket — they live only on the local machine that built the
manifest, so §0b uploads them once and `PANEL_ROOT` tells the worker where to pull them from.

## 0a. Pre-flight resolution → the KNOWN-GOOD manifest v6 (do this BEFORE spending fleet compute)
BIDS `eeg_id = patient_id+eeg_datetime`; some datetimes came from report metadata and have **no EDF** on
S3. Resolve every BIDS row up front (match `eeg_datetime`→BIDS `scans.tsv` acq_time — the SAME `decide_edf`
the worker uses) and drop-and-replace the unresolvable ones so the total does not shrink:
```bash
PYTHONPATH=src python scripts/129_preflight_resolve.py --manifest data/manifest/report_manifest_v5.parquet
PYTHONPATH=src python scripts/130_finalize_v6.py        # -> report_manifest_v6 (>= |v5|) + manifest_rejects
```
`v6` stamps each row's resolved session path + match reason; `manifest_rejects.parquet` lists what was
dropped and why. Only run the fleet on `v6`, so unresolvable rows never reach the expensive stage.
(Existence + unique resolution is guaranteed here; full *usability* — ≥5 min, ≥20 usable seg, ≥0.20 usable
fraction, SAP §3.2 — is confirmed post-run in the ledger §1c and topped up if a bin falls short.)

## 0b. Upload the panel source files to S3 (one-time — the manifest references them by relative path)
The 1,861 panel rows in `report_manifest_v5` carry a **relative** `source_path`
(`occasionnoise/<fid>.edf`, `moe/<event>.mat`); the worker's `fetch_panel` resolves it against
`PANEL_ROOT`. Stage them into one canonical tree on the machine that has the scratchpad, then push to S3:
```bash
# on the local machine that downloaded/repaired the panels (has the scratchpad):
PYTHONPATH=src python scripts/128_stage_panels.py        # -> panels/occasionnoise/*.edf + panels/moe/*.mat (~2.5 GB)
aws s3 sync panels/ s3://<run-bucket>/panels/            # one-time upload; same tree the worker pulls from
```
Then on the box set `PANEL_ROOT=s3://<run-bucket>/panels` (§0). `fetch_panel` supports `s3://…` (via
`aws s3 cp`), an rclone remote (`remote:prefix`, via rclone), or a local dir — so for a **local** pilot use
`PANEL_ROOT=$(pwd)/panels` and skip the upload. If `PANEL_ROOT` is unset, panel rows are skipped
(`nopanelfile`) and only BDSP recordings featurize.

## 1. Featurize — parallel, sharded, resumable
The worker shards by `SHARD="i/N"` (worker i of N takes manifest rows where `idx % N == i`) and skips any
`eeg_id` already in `data/derived/segment_master/_done/` — so it is **crash-safe and resumable**. Launch N
workers (N = #GPUs or #processes):
```bash
N=8
for i in $(seq 0 $((N-1))); do
  SHARD="$i/$N" nohup python scripts/31_segment_master_worker.py > logs/fleet_$i.log 2>&1 &
done
```
Each worker writes ONLY per-eeg_id sidecars (crash-safe, shard-safe): `segment_master/eeg_id=<id>/part.parquet`
(per segment×channel), `segment_summary/eeg_id=<id>/part.parquet` (per segment), `segment_master/_done/<id>.done`
(success + stats + sha256), `_status/<id>.status` (non-success outcome). Rough cost: ~30–60 s/recording/worker.

## 1c. Assemble the run ledger (AFTER all shards finish)
The one-row-per-EEG governance table is built by a SEPARATE pass so concurrent shards never clobber a global
file (this replaces the old, race-prone in-worker write):
```bash
PYTHONPATH=src python scripts/33_assemble_ledger.py     # -> recording_meta.parquet (+ recording_labels.parquet)
```
`recording_meta` is the auditable "single file": one row per intended EEG with provenance (source_edf,
sha256, resolve_reason), stats (recording_seconds, n_segments, n_usable, stage fractions, gate coverage),
EEG-level gate (p_focal/p_generalized), and outcome (processed / included / exclusion_reason). Rows that
resolve+featurize but fail usability (SAP §3.2) are flagged `unusable:*` — feed those bins back to §0a/§130
for a top-up so the analyzable N holds.

## 1b. Outputs — WHERE every result lands (so the analysis plan can run)

Everything is written under **`OUTPUT_ROOT`** (env; default `data/derived`). Point it at durable/shared
storage on the box and **sync to the S3 output bucket** so all shards' outputs assemble into one dataset.

| Output | Path (under `OUTPUT_ROOT`) | Produced by | Consumed by |
|---|---|---|---|
| `segment_master/eeg_id=<id>/part.parquet` | one partition per recording, per segment×**channel** | fleet (`scripts/31`) | norms, all analyses (regions via `canonical.to_regions`) |
| `segment_summary/eeg_id=<id>/part.parquet` | per segment: stage, artifact, `p_slowing`, whole-head vP | fleet (`scripts/31`) | norms, detection |
| `segment_master/_done/<id>.done`, `_status/<id>.status` | per-eeg success/outcome sidecars | fleet | ledger, monitoring |
| `recording_meta.parquet` | one row per eeg_id (the run ledger) | **`scripts/33`** (after shards) | Table 1, filters, audit |
| `recording_labels.parquet` | one row per eeg_id | `scripts/33` | label-dependent analyses |
| `norms/` (GAMLSS params) | after featurize | `gamlss_fit.R` | deviation_field |
| `deviation_field/` (z per seg×region×feature) | after norms | analysis | descriptors, detection |
| `descriptors.parquet` | after deviation | describe step | sentences, Tables |

Collect to S3 (periodically during the run + at the end), so a single machine can run the analysis:
```bash
export OUTPUT_ROOT=/data/run                       # durable local disk on the box
aws s3 sync $OUTPUT_ROOT/segment_master/ s3://<run-output-bucket>/segment_master/
aws s3 sync $OUTPUT_ROOT/ s3://<run-output-bucket>/ --exclude 'segment_master/*'
```
Multi-machine: each worker writes locally and syncs its `eeg_id=*` partitions to the same S3 prefix (no
collision — partitions are keyed by eeg_id). The analysis machine `aws s3 sync`s the bucket back down, so it
has the **complete** `segment_master` + sidecars before fitting norms.

## 2. Verify the run (before any analysis)
```bash
python scripts/32_segmaster_summary.py          # validates schema; stage-conditioned region table + figure
python -c "from morgoth_slowing.io import canonical as C; \
  sm=C.load_segment_master(); C.validate_schema(sm); ss=C.load_segment_summary(); C.validate_summary(ss); \
  print('EEGs', sm.eeg_id.nunique(), 'channel-rows', len(sm), 'segments', len(ss), \
  'artifact%', round(100*ss.artifact_flag.mean(),1), 'gate-cov%', round(100*ss.p_slowing.notna().mean(),1))"
```
Check: row counts, stage fractions, artifact fractions vs Table 1 expectations, gate coverage
(`p_slowing` non-null in `segment_summary`), ledger `included`/`excluded` breakdown, and panel presence.

## 3. Norms → deviation field → Tables/Figures
```bash
Rscript scripts/gamlss_fit.R                     # GAMLSS/LMS norms on clean_normal (age×stage×region)
# materialize deviation_field (z per segment×region×feature), then run the analysis scripts
# (repointed to the canonical tables via src/morgoth_slowing/io/canonical.py) -> Tables 1-6, Figures 1-9
```

## 4. Calibrate the gate probability (SAP §4.7)
After the run, fit a Platt/isotonic calibration for `p_slowing` (and focal/gen) vs report/consensus labels
on held-out data; store the calibrated probability alongside the raw one before any operating-point claim.

## Notes
- **Panels** (OccasionNoise + MoE): IN `report_manifest_v5` (1,861 rows: 100 OccasionNoise + 1,761 MoE),
  appended by `scripts/127` for the human-ceiling aim (SAP §3.6, §8.3). Their loaders live in
  `src/morgoth_slowing/io/panels.py` (OccasionNoise EDF header repair + MNE; MoE MATLAB-v7.3 via h5py) and
  featurize through the SAME worker path. Their source files are uploaded via §0b and resolved by
  `PANEL_ROOT`. The main cohort run does not depend on them, so a missing/unset `PANEL_ROOT` just skips them.
- Reproduction: the run is pinned by the manifest version (**v6**) + its **sha256** in
  `docs/run_manifest_index.md` (`8ac7a552…`) + the code git tag (`git tag run-v6`) + `fleet_dependencies.md`.
