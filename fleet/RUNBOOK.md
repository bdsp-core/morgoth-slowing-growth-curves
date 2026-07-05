# Fleet Runbook — running Morgoth over a large EEG cohort on AWS spot GPUs

This documents the exact setup used to process **13,034 EEG recordings** through the Morgoth slowing
pipeline on a fleet of AWS GPU spot instances, writing per-recording results to S3. It is written to be
**repeatable** — including for future runs over *different* EEG cohorts and *different Morgoth heads*
(spike, IIC, etc.), not just slowing.

The design goal throughout: **elastic + self-healing + cost-bounded**. Any number of workers fully covers
the cohort, spot interruptions heal automatically, and the fleet shuts itself off when done.

---

## 0. Architecture at a glance

```
 manifest.jsonl (N recordings)                    S3 (rclone remote `bdsp:`)
        │                                          .../Growth_curves/expansion/
        │                                              ├── features/<rid>.parquet
   ┌────┴─────┐   each worker walks the WHOLE          ├── stages/<rid>.csv
   │  AMI of  │   manifest in its own shuffled         ├── gate/<rid>.json
   │ pilot box│   order, skips anything already        ├── provenance/<rid>.json
   └────┬─────┘   .done in S3, uploads results         └── done/<rid>.done   ← resume/progress marker
        │
        ▼
  K× g4dn.xlarge spot  ──(elastic, self-healing)──►  writes results + .done to S3
        │
        ▼
  local dashboards: burndown (progress) + analysis_dashboard (results)
```

- **Elastic worker** (`fleet/batch_worker.py`, `DYNAMIC=1`): every worker reads the full manifest, hashes
  each recording id with its own seed for a unique walk order, and processes any recording lacking a
  `done/<rid>.done` marker in S3. Consequences:
  - **# workers is decoupled from coverage** — 1 worker or 200 workers both fully cover the cohort.
  - **spot interruptions self-heal** — a reclaimed worker's in-progress recording is just picked up by
    another worker on a later pass.
  - **resumable** — rerun anytime; already-`.done` recordings are skipped.
- **Cost is ~flat regardless of worker count** — total = (recordings × minutes-each) worker-hours ×
  spot $/hr. More workers only compress the same hours into fewer days.

---

## 1. Accounts, credentials, network (the fixed facts for this project)

| Thing | Value |
|---|---|
| AWS account | `278057567389` |
| Region / AZ | `us-east-1` / `us-east-1f` |
| Driver IAM user | `fleet-driver` (EC2 full; **no** ServiceQuotas/IAM perms) → aws profile `fleet` |
| Driver keys | `~/Desktop/GithubRepos/AWSKeys/fleet-driver_accessKeys.csv` (**gitignored**) |
| BDSP data keys | `~/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv` (read **and** write same bucket) |
| rclone remote | `bdsp:` (configured with the BDSP keys) |
| SSH key | `morgoth-pilot-key` → `~/Desktop/GithubRepos/AWSKeys/morgoth-pilot-key.pem` |
| Subnet / SG | `subnet-073fad6d014fa4f63` / `sg-05daa9abca4b4bacc` |
| Pilot box | `i-00435e6dec3842d67` (also the AMI source + re-analysis box) |
| Worker AMI | `ami-0558041058267feeb` (built from pilot; has repo + venv + morgoth2 + rclone config + checkpoints) |
| Instance type | `g4dn.xlarge` spot (1× T4, 4 vCPU) — **best GPU density per vCPU of spot quota** |
| S3 results root | `bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/expansion` |
| S3 worker code | `bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/code/batch_worker.py` |

`aws` CLI lives in the repo venv: `source .venv/bin/activate` before any `aws`/`rclone` command.
BDSP env for rclone against the credentialed bucket:
```bash
export AWS_ACCESS_KEY_ID=$(python3 -c "import csv;print(list(csv.DictReader(open('.../bdsp_opendata_write_accessKeys.csv',encoding='utf-8-sig')))[0]['Access key ID'])")
export AWS_SECRET_ACCESS_KEY=$(python3 -c "import csv;print(list(csv.DictReader(open('.../bdsp_opendata_write_accessKeys.csv',encoding='utf-8-sig')))[0]['Secret access key'])")
```

---

## 2. Spot quota (the throughput bottleneck)

Parallelism is capped by the EC2 quota **"All G and VT Spot Instance Requests"** (`L-3819A6DF`), measured
in **vCPUs**. Each `g4dn.xlarge` = 4 vCPU, so **max workers = quota ÷ 4**.

- Default is often ~64 (16 workers). We raised it to **512 (128 workers)**.
- `fleet-driver` cannot request increases (no ServiceQuotas perm). Request in the **console** as an admin:
  Service Quotas → EC2 → *All G and VT Spot Instance Requests* → Request increase → e.g. `512`.
- **A 0→large first request is auto-denied ("Case Closed").** Request *incrementally* (you already have
  spot usage → step-ups approve fast), or open a Support case (limit type *EC2 Spot Instances*).
- To let me (the automation) submit it, attach `ServiceQuotasFullAccess` to `fleet-driver`.

---

## 3. Build the manifest

`fleet/make_manifest.py` builds `fleet/manifest.jsonl` — one JSON row per recording with at least
`SiteID, pid, date, BidsFolder, SessionID, AgeAtVisit, SexDSC` (recording id `rid = f"{SiteID}{pid}_{date}"`).
It interleaves labels and age-bands so any strided/shuffled slice is class-balanced, and prepends
targeted priority strata (here: extra theta-focal + posterior cases).

**For a new cohort:** point `make_manifest.py` at the new BIDS index / cohort table and regenerate.
Keep it **lean and text-free** (no report text, no PHI) — GitHub rejects >100 MB and raw text is policy-out.

---

## 4. Prepare the worker AMI (once per pipeline change)

The AMI bakes the working pilot environment (repo, venv, `morgoth2` checkpoints, rclone config with BDSP
keys, aws creds). Rebuild it only when the *non-worker* code changes (worker code is fetched from S3 at
boot — see §5). To rebuild after editing e.g. `scripts/30_ingest_worker.py`:
```bash
rsync -az -e "ssh -i $KEY" scripts/30_ingest_worker.py ubuntu@$PILOT_IP:~/morgoth-slowing-growth-curves/scripts/
AMI=$(aws ec2 create-image --profile fleet --region us-east-1 --instance-id i-00435e6dec3842d67 \
      --name "morgoth-fleet-$(date +%Y%m%d%H%M)" --no-reboot --query ImageId --output text)
aws ec2 wait image-available --profile fleet --region us-east-1 --image-ids "$AMI"
echo "$AMI" > fleet/.ami_id
```

---

## 5. The worker (`fleet/batch_worker.py`)

- Reuses the validated local worker `scripts/30_ingest_worker.py::process_one` unchanged (same features +
  sleep stages + Morgoth gate + provenance), then uploads the 4 output files + a `.done` marker to S3.
- `DYNAMIC=1` → elastic full-manifest walk (see §0). `DYNAMIC=0` → legacy strided slice
  (`FLEET_INDEX::FLEET_TOTAL`) — only use if #workers is fixed and known.
- Unprocessable recordings (no EDF / too short) are marked `.done` with body `noout` so they aren't
  retried forever. Recordings that *error* are logged `FAIL` and left un-`.done` (retried next pass; if
  the whole remaining tail is un-fixable errors, a full pass processes 0 new → workers self-terminate).
- **Worker code is fetched from S3 at boot**, so iterating on the worker needs no AMI rebuild:
  ```bash
  rclone copyto fleet/batch_worker.py bdsp:.../Growth_curves/code/batch_worker.py   # publish
  ```

---

## 6. Launch & scale

Per-instance user-data (identical for all workers; unique walk via `SEED=$RANDOM$RANDOM` on-instance):
fetches the latest worker from S3, sets env, runs it under a `timeout 216000` (60h) backstop, then
`shutdown -h now` (instance is `--instance-initiated-shutdown-behavior terminate`).

- **`fleet/scale_elastic.sh <target>`** — top up to `<target>` workers. Launches spot singles until the
  target or the quota cap; safe to run every tick (at the cap it launches 0). **Also self-heals** — if
  spot reclaimed some workers, the next run relaunches them.
  ```bash
  bash fleet/scale_elastic.sh 128
  ```
- Launch singles, **not** `run-instances --count N` (for spot, `--count MIN:MAX` is effectively
  all-or-nothing at MAX and fails with `MaxSpotInstanceCountExceeded`; singles in a loop degrade
  gracefully to the quota cap).

---

## 7. Monitor (dashboards)

- **Progress / burndown:** `scripts/fleet_progress.py` counts S3 `.done` markers, appends a timestamped
  sample to `data/derived/fleet_progress.jsonl`, and rebuilds `results/fleet_burndown.html` via
  `scripts/build_burndown.py` (burndown curve, **recent windowed** rate + ETA, throughput chart, recent
  completed recordings). Publish it as an Artifact for a phone-friendly live view.
- **10-min throughput sampler** (fine-grained rate plot), detached:
  ```bash
  nohup bash -c 'source .venv/bin/activate; for i in $(seq 1 120); do python scripts/fleet_progress.py 13034; sleep 600; done' & echo $! > fleet/.sampler_pid
  ```
- **One-shot monitoring tick** (`fleet/tick.sh`): refresh burndown → then **SCALE** (top up to 128 while
  `remaining > 400`) / **DRAIN** (stop topping up for the tail so self-terminating workers aren't
  relaunched) / **FINALIZE** (`remaining ≤ 0`, or workers drained with only a tiny unprocessable tail).
  Prints a `STATE=` line. Run it on a schedule (we drive it from a ~30-min loop).

---

## 8. Completion — auto-shutdown & results (`fleet/finalize.sh`)

Triggered by `tick.sh` at completion. **Money safety net** — three independent layers ensure nothing runs
forever:
1. Each worker **self-terminates** when a full pass finds no new work.
2. `timeout 216000` (60h) per-instance backstop, then `shutdown -h now` (terminate).
3. `finalize.sh` **terminates every `tag:fleet=morgoth-slowing` instance** as a sweep, and stops the sampler.

`finalize.sh` then runs `fleet/reanalyze.sh` to regenerate the all-results dashboard from the full S3
outputs. **The pilot box is left running** for that re-analysis — terminate it manually when fully done:
```bash
aws ec2 terminate-instances --profile fleet --region us-east-1 --instance-ids i-00435e6dec3842d67
```

---

## 9. Cost model

Measured: ~**12.6 min/recording** average (mixed routine + multi-day EMU). For N recordings:
- worker-hours ≈ `N × 12.6 / 60`  (13,034 → ~2,750 wh)
- **cost ≈ worker-hours × ($spot/hr + ~$0.013 EBS/hr)**, ~$0.24/hr → **~$660 total, flat**
- wall-clock ≈ `worker-hours / #workers`  (128 workers → ~15–17 h)

Check the live spot price: `aws ec2 describe-spot-price-history --instance-types g4dn.xlarge --product-descriptions Linux/UNIX ...`

---

## 10. Adapting to a DIFFERENT Morgoth head or cohort (future runs)

The fleet infrastructure (AMI, launch, scale, monitor, finalize, dashboards) is **head-agnostic**. To run
a different head or cohort, change only:

1. **The cohort** → rebuild `fleet/manifest.jsonl` (§3) for the new recordings.
2. **The Morgoth head / model** → the model is invoked inside `scripts/30_ingest_worker.py::process_one`,
   which uses config from `scripts/26_slowing_ingest_pilot.py` (`MORGOTH2_DIR`, the venv, and the
   window-model + `EEG_level_head` **checkpoints**, gate step, `RUN_GATE`). Point those at the new head's
   checkpoints and adjust what `process_one` extracts/saves for that head's outputs. Env knobs already
   exposed: `RUN_GATE`, `GATE_STEP`, `CODE_COMMIT`, `EXPANSION_MAX_GB`.
3. **The S3 output prefix** → change `S3_OUT` (and the `code/` path) so a new run doesn't collide with
   this one's `.done` markers. e.g. `.../Growth_curves/spike_run/`.
4. Republish the worker to S3 (§5), rebuild the AMI only if you changed non-worker code (§4), then §6–§8
   are unchanged.

Everything else — elasticity, self-healing, quota handling, dashboards, auto-shutdown — carries over.

---

## 11. Gotchas hit during this run (so you don't rediscover them)

- **zsh doesn't word-split** unquoted `$vars` → passing a tab/space list to `--instance-ids` sends one
  malformed arg. Use `echo "$IDS" | tr '\t' '\n' | xargs aws ...` or `${=var}`.
- **macOS has no `timeout`** → don't wrap `aws` in `timeout`; use `--cli-connect-timeout` /
  `--cli-read-timeout`. (`timeout` *does* exist on the Ubuntu instances, used for the 60h backstop.)
- **`aws ... --user-data "$string"` base64-encodes for you** → passing an already-base64 string double
  encodes it. Pass a plain script file with `--user-data file:///path/to/script.sh`.
- **Spot `run-instances --count MIN:MAX` is all-or-nothing** → launch singles in a loop; stop on
  `MaxSpotInstanceCountExceeded`.
- **Terminated spot requests linger ~30–60 s** against the quota → wait for instances to reach
  `terminated` (not just `shutting-down`) before relaunching to the cap.
- **A 0→large spot-quota request auto-denies** ("Case Closed", applied value unchanged) → request
  incrementally.
- **Provenance `source_edf`** had a doubled `s3://.../EEG/` prefix (fixed in `scripts/30`); the path is
  `f"s3://{ep}"` where `ep` already includes the bucket/prefix.
- **Burndown "rate" must be a recent window, not a lifetime average** — during a scale-up the cumulative
  average badly understates current throughput.

---

## 12. Quick reference — resume / operate an in-flight run

```bash
cd ~/Desktop/GithubRepos/morgoth-slowing-growth-curves && source .venv/bin/activate
bash fleet/tick.sh                 # refresh dashboard + scale/drain/finalize (one tick)
bash fleet/scale_elastic.sh 128    # force top-up to 128 workers
bash fleet/finalize.sh             # shut the whole fleet down now + regenerate results
# count done:
rclone lsf bdsp:.../Growth_curves/expansion/done/ | wc -l
# list live workers:
aws ec2 describe-instances --profile fleet --region us-east-1 \
  --filters "Name=tag:fleet,Values=morgoth-slowing" "Name=instance-state-name,Values=running" \
  --query 'length(Reservations[].Instances[])' --output text
```
