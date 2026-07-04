# Fleet launch package — full slowing-ingestion wave on AWS Batch

Runs the **exact pipeline validated on the single pilot box** (features + sleep stages + focal/gen/
normal Morgoth gate + provenance) across a spot-GPU fleet, writing per-recording outputs to S3 with
`.done` markers for resumability. Same `process_one` code — only the orchestration + output sink change.

> ⚠️ **Status: prepared, not yet run.** The author (autonomous agent) had no AWS credentials, so this
> was **not executed on AWS** — the pilot proved the *pipeline*; this proves out the *packaging*. Review
> the IAM roles and the `EDIT THESE` block in `launch_fleet.sh` before running. Everything is standard
> AWS Batch; expect to iterate once on roles/subnet/SG.

## What it does
- `make_manifest.py` → the stratified work list (label × age-band round-robin), N recordings → S3.
- `Dockerfile` → container (pilot pipeline + morgoth2 + CUDA torch + rclone + awscli).
- `batch_worker.py` → each Batch **array task** takes a strided slice of the manifest, runs `process_one`
  per recording, uploads outputs to `S3_OUT/{features,stages,gate,provenance}/`, writes `S3_OUT/done/<rid>.done`.
- `launch_fleet.sh` → build+push image, upload manifest, create Batch compute-env/queue/job-def, submit
  the array, set a Budgets alarm.

## Cost / scale (targeted ~15k)
~$0.16/hr spot g4dn.xlarge; ~5–8 min/recording (features multicore + sleep + gate at 10 s step).
15k ÷ 50 boxes ≈ **~15–20 h wall-clock, ~$300–500**. Cost is ~flat vs box count (bill is instance-hours);
more boxes = less wall-clock. Budget guardrail defaults to $800.

## Prerequisites (one-time)
1. **AWS creds** for account 278057567389 in **us-east-1** (console CloudShell already has them).
2. An **S3 bucket you own** in us-east-1 (set `BUCKET` in `launch_fleet.sh` + `stage_models.sh`).
3. **IAM roles** (§IAM below).
4. `docker` available where you build (CloudShell has limited disk — a small EC2 or your Mac is easier
   for the ~6 GB image build).
5. **Stage the 6 checkpoints** into your bucket: `BUCKET=s3://... bash fleet/stage_models.sh`.

## Run
```bash
# from a machine with docker + aws configured (us-east-1):
BUCKET=s3://your-bucket/morgoth-slowing bash fleet/stage_models.sh     # once
bash fleet/launch_fleet.sh                                             # edit the top block first
# watch:
aws batch list-jobs --job-queue morgoth-slowing-q --region us-east-1
aws s3 ls s3://your-bucket/morgoth-slowing/expansion/done/ | wc -l     # progress
```
Resumable: re-submitting skips any recording whose `done/<rid>.done` exists.

## Collect results
```bash
aws s3 sync s3://your-bucket/morgoth-slowing/expansion data/derived/expansion
PYTHONPATH=src python scripts/combine_expansion.py       # -> expansion_pilot_features.parquet + provenance + gate CSVs
# then refit curves + rerun analysis (scripts 03/04/06/22 etc.)
```

## IAM (the part to get right)
- **Batch service role** (`AWSBatchServiceRole`) — Batch managed policy.
- **EC2 instance role** (`ecsInstanceRole`, as an instance profile) — `AmazonEC2ContainerServiceforEC2Role`
  + read on the BDSP bucket is via the rclone keys (passed as job env), so instance role just needs ECR pull.
- **ECS task execution role** (`ecsTaskExecutionRole`) — pull image + write logs.
- **Job role** (`morgothSlowingJobRole`) — **S3 read/write to your `$BUCKET`** (the worker's outputs + `.done`).
- Put the **BDSP keys** as job env (`BDSP_KEY_ID/SECRET`) or, better, AWS Secrets Manager refs.

## Notes
- `GATE_STEP=10` (recording-level gate) balances cost/resolution; set `GATE_STEP=5` for finer, or
  `RUN_GATE=0` to skip the gate (features+stages only, ~1.7× faster).
- `PER_TASK=60` recordings/task ≈ 5–8 h/task — good for spot (short enough to re-queue cheaply on
  interruption; each recording is idempotent via `.done`).
- The pilot box already validated the pipeline end-to-end; the fleet is the same code at scale.
