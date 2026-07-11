# Fleet launch (AWS) — turnkey run of the clean-room pipeline

Prereqs: `docs/fleet_dependencies.md` (code, checkpoints, env). The worker `scripts/31_segment_master_worker.py`
is validated end-to-end (features + van Putten + Morgoth stage + per-segment gate). This is how to run it at
scale on the AWS GPU box.

## 0. One-time setup on the box
```bash
export MORGOTH2_DIR=/path/to/morgoth2 MORGOTH_DEVICE=cuda PILOT_VENV=$(which python)
export MORGOTH_SHIMS=$(pwd)/scripts/shims RCLONE_BIN=$(which rclone)
export KMP_DUPLICATE_LIB_OK=TRUE RUN_GATE=1 PYTHONPATH=src
export MANIFEST=data/manifest/report_manifest_v4.parquet     # 25,663 EEGs (cohort+expansion+backfill)
# link the 6 checkpoints into $MORGOTH2_DIR/checkpoints/ (see fleet_dependencies.md §3)
```

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
Output: `data/derived/segment_master/eeg_id=<id>/part.parquet` (one per recording) + `recording_meta` /
`recording_labels`. Rough cost: ~30–60 s/recording/worker → ~25k EEGs / N workers.

## 1b. Outputs — WHERE every result lands (so the analysis plan can run)

Everything is written under **`OUTPUT_ROOT`** (env; default `data/derived`). Point it at durable/shared
storage on the box and **sync to the S3 output bucket** so all shards' outputs assemble into one dataset.

| Output | Path (under `OUTPUT_ROOT`) | Produced by | Consumed by |
|---|---|---|---|
| `segment_master/eeg_id=<id>/part.parquet` | one partition per recording | fleet (`scripts/31`) | norms, all analyses |
| `recording_meta.parquet` | one row per eeg_id | fleet | Table 1, filters |
| `recording_labels.parquet` | one row per eeg_id | fleet | label-dependent analyses |
| `segment_master/_done/<id>.done` | provenance + resumability | fleet | monitoring |
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
python scripts/32_segmaster_summary.py          # stage-conditioned feature table + figure
python -c "import glob,pandas as pd; from morgoth_slowing.io import canonical as C; \
  sm=C.load_segment_master(); C.validate_schema(sm); \
  print('EEGs', sm.eeg_id.nunique(), 'rows', len(sm), 'artifact%', round(100*sm[sm.region=='whole_head'].artifact_flag.mean(),1))"
```
Check: row counts, stage fractions, artifact fractions vs Table 1 expectations, gate coverage
(`p_slowing` non-null), and (once panels are in) panel presence.

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
- **Panels** (OccasionNoise + MoE): not yet in the manifest — see `scripts/127` (their EDFs need format
  handling: OccasionNoise EDFs have non-compliant/shifted-date headers; MoE recordings are MATLAB v7.3).
  The main cohort run does not depend on them; they are appended for the human-ceiling aim (SAP §3.6, §8.3).
- Reproduction: the run is pinned by the manifest version + the code git tag (`git tag run-vN`) +
  `fleet_dependencies.md`.
