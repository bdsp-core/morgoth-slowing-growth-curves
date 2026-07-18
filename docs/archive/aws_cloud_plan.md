> REGION VERIFIED (2026-07-03): both bdsp-opendata buckets are in **us-east-1**. Brandon's
> existing EC2 is us-west-2 — for the 60 TB ingestion, launch the fleet in **us-east-1**
> (same region = free transfer, ~$1k total). Running in us-west-2 costs ~$1,200 cross-region
> (inter-region S3→EC2 ~$0.02/GB). Pilot (~10 recordings) is negligible cost in either region.

# AWS cloud plan — running the full-wave EEG ingestion

Cost-effective-but-fast plan to ingest the **priority ≥ 4 first wave: 33,946 recordings** (≈ 60 TB raw,
median 21 h/recording) from the BDSP open-data S3 buckets, featurize them, and write per-recording
feature parquet back to S3 — **without ever mirroring the 60 TB**.

> **TL;DR (recommended config):** a spot fleet of **~25× `g4dn.xlarge`** in the bucket's region,
> AWS Batch managed, containerized pipeline. **~$1,000 total compute, ~6 days wall-clock.** Storage of
> the resulting features is **< $5/month**. In-region S3→EC2 transfer is **free** (vs ~$5.4k if run
> out-of-region). Go to `g5.xlarge` only if the CUDA-ported stager turns out GPU-bound — see §2.

Pricing below is us-east-1, mid-2026, and will drift — spot re-prices every few minutes. Re-check with
`aws ec2 describe-spot-price-history` before launch. Sources listed at the bottom.

---

## 0. Preconditions (from the pilot — do not skip)

`docs/coverage_expansion_plan.md` §"Pilot findings" lists **scientific blockers that gate the full
wave**: (a) artifact rejection + pipeline harmonization so EDF-derived features match the norm
distribution (pilot saw whole-head rel_delta ≈ 0.055 vs cohort ~0.34); (b) a ~100-recording validation
pilot; (c) selection fixes — drop the ~60 impossible-duration outliers and add the per-recording
**EDF path (BidsFolder + SessionID)** to the candidate CSV so each recording can actually be pulled.
This document assumes (a)–(c) are done and the pipeline is frozen. Run the same container on the
100-recording pilot on **one** instance first; only then open the fleet.

**Region.** The whole cost model depends on compute living in the **same region as the buckets**
(`bdsp-opendata-repository`, `bdsp-opendata-credentialed`) — same-region S3↔EC2 transfer is $0. BDSP
open data is in **us-east-1**; confirm with `aws s3api get-bucket-location --bucket
bdsp-opendata-repository` and launch the fleet there. Out-of-region would add ~$0.09/GB × 60 TB ≈
**$5,400** in egress alone — more than the entire compute budget.

---

## 1. Architecture — work-queue, pull→process→drop, no persistent disk

The unit of work is **one recording** (one `bdsp_id` + session). Each worker loops:

```
claim next recording from queue
  → aws s3 cp / rclone  raw BIDS EDF  → local scratch (~2–15 GB, one file)
  → sleep-stage        (GPU)          → per-epoch W/N1/N2/N3/REM
  → featurize + artifact-reject (CPU) → segment + recording feature tables
  → aws s3 cp  <recording>.parquet    → s3://…/features/  + write a .done marker
  → rm the raw EDF from scratch       (peak disk = a few recordings, not 60 TB)
  → ack / delete queue message
```

Because raw is dropped immediately, **no large persistent volume is needed** — a 100–200 GB gp3 root
per instance holds a handful of in-flight recordings. This is the single most important cost lever
after region: we never pay to store 60 TB.

**Two ways to run the queue:**

| | **AWS Batch (recommended)** | **EC2 spot fleet + SQS/S3-manifest (DIY)** |
|---|---|---|
| Queue | Batch array job (one child per recording) or SQS-fed | SQS queue seeded from the candidate CSV, or an S3 manifest + atomic claim |
| Scaling | Managed compute environment, spot, scales to `maxvCpus` and back to 0 | Auto Scaling Group of spot instances, you own scale-in/out |
| Spot reclaim | Auto-requeues the interrupted job | You handle SIGTERM → re-queue the message |
| Ops burden | Low — retries, logging, teardown built in | Higher, but maximally transparent/cheap |
| Best when | You want it done with least babysitting (this project) | You want fine control or already run a Slurm/ASG pattern |

**Recommendation: AWS Batch** with a **spot** compute environment (`g4dn.xlarge`, allocation strategy
`SPOT_CAPACITY_OPTIMIZED`). Model the 33,946 recordings as a Batch **array job** (or feed an SQS queue
and run N identical workers). Batch handles spot interruptions by re-running the child job — combined
with the `.done` markers (§5) that gives idempotent, resumable ingestion for near-zero ops.

---

## 2. Instance choice + throughput

The pipeline is **CPU-bound, not GPU-bound.** The stager (`ss_hm_1` / `SLEEPPSG.pth`,
`base_patch200_200`: a 12-layer ViT, embed 200 — see `docs/sleep_staging.md`) is a *small* model; the
real time goes to MNE EDF decode + resample (256→200 Hz) + `filtfilt`/notch and the per-segment
multitaper PSD (`features/extract.py`: 7 DPSS tapers × 3000-pt FFT × 18 bipolar channels, one per 15-s
segment). That has two consequences: (1) the cheaper T4 box is the right default because its 4 vCPUs
match the A10G box's 4 vCPUs, and (2) throughput barely changes between g4dn and g5.

| | **g4dn.xlarge (recommended)** | **g5.xlarge** |
|---|---|---|
| GPU | 1× NVIDIA **T4** (16 GB) | 1× NVIDIA **A10G** (24 GB) |
| vCPU / RAM | 4 / 16 GiB | 4 / 16 GiB |
| On-demand $/hr | **$0.526** | $1.006 |
| Spot $/hr (typical) | **~$0.247** | ~$0.552 |
| Role here | CPU-bound pipeline; T4 amply fast for the ViT | only if staging becomes the bottleneck |

**Per-recording time budget** (21 h median, pipelined so S3 pull and CPU/GPU overlap):

| stage | where | ~time / 21 h recording |
|---|---|---|
| S3 pull ~1.8 GB (in-region 150–300 MB/s) | net | 6–12 s (overlapped) |
| MNE read + resample + HP/notch `filtfilt` | CPU (4 vCPU) | 1.5–3 min |
| sleep staging (ViT inference, batched) | GPU | ~30–60 s (T4); ~half on A10G |
| featurize (multitaper) + artifact reject | CPU (4 vCPU) | 1–2.5 min |
| parquet write + `.done` marker | net | ~15 s |
| **end-to-end (pipelined)** | | **~5–6 min → use 6 min** |

So **~10 recordings/hour/instance** (central; ~7.5/hr conservative, ~12/hr optimistic).

**Totals for the wave:**
- Windows to process: 33,946 × 7,560 (a 21 h rec ≈ 7,560 × 10 s windows) ≈ **257 million windows**.
- Instance-hours: 33,946 ÷ 10 ≈ **~3,400 instance-hours** (call it 3,400–3,700 to cover spot restarts).
- **GPU-hours:** the box has a GPU the whole time, so ~3,400 *provisioned* GPU-hours — but actual GPU
  *busy* time is only ~(0.75 min × 33,946)/60 ≈ **~425 GPU-busy-hours.** The 8× gap between provisioned
  and busy GPU is exactly why the cheap T4 box wins and why you could later split staging (GPU) from
  featurize (CPU) — see the note below.

**MPS → CUDA port.** The stager was validated on Mac **MPS** (`run_predict_mac.py`, `--device mps`,
`PYTORCH_ENABLE_MPS_FALLBACK=1`). On AWS switch to `--device cuda`, drop the MPS-fallback env var, and
install the **CUDA** torch/torchvision wheels in the container (§4). Bump `--num_workers` above 0 and
raise the inference batch size to keep the T4 fed. Sanity-check that CUDA staging reproduces a handful
of MPS-staged recordings before the fleet run (op ordering can shift a few epoch labels).

**Optional split (only if you want max cost efficiency at scale):** run staging on a small pool of
g4dn boxes and featurize on cheap compute-optimized CPU instances (e.g. `c7i.2xlarge`, 8 vCPU,
on-demand ~$0.36/hr, spot ~$0.13–0.17/hr) reading the staged output. This stops paying for an idle T4
during the CPU-heavy 60–70% of each recording. For a one-shot 33,946-recording wave the single-box
g4dn path is simpler and already cheap; keep the split in your pocket if you re-run or expand.

---

## 3. Cost estimate

Compute (spot, in-region, ~3,400 instance-hours central; +~10% pad for restarts → 3,750):

| config | $/hr | inst-hours | **compute total** |
|---|---:|---:|---:|
| **g4dn.xlarge spot (recommended)** | $0.247 | 3,750 | **~$925** |
| g4dn.xlarge on-demand | $0.526 | 3,400 | ~$1,790 |
| g5.xlarge spot | $0.552 | 3,600 | ~$1,990 |
| g5.xlarge on-demand | $1.006 | 3,400 | ~$3,420 |

**Storage of results.** Per-recording feature parquet is small — segment-level ~7,560 seg × 18 ch × 31
features plus recording-level rollups, a few MB compressed per recording. 33,946 × ~2–5 MB ≈
**70–170 GB** → at $0.023/GB-month ≈ **$2–4/month.** (You are *not* storing the 60 TB raw — it is
dropped.) S3 GET/PUT requests for the wave are ~$0.10 total. Transient EBS scratch: ~100–200 GB gp3
per instance for the ~6-day run ≈ a few dollars per instance across the fleet.

**Data transfer: $0** (same-region S3↔EC2). This is the headline saving — see §0.

**Fast-vs-cheap tradeoff** (recommended g4dn.xlarge spot; total compute ≈ constant because spot
bills by the hour with no idle — more instances only buys wall-clock):

| parallel instances | wall-clock | compute cost | notes |
|---:|---|---:|---|
| 5 | ~31 days | ~$925 | slow; long spot-exposure window |
| 20 | ~7.7 days | ~$925 | comfortable |
| **25 (recommended)** | **~6 days** | **~$925** | balanced; easily under any spot-capacity ceiling |
| 50 | ~3.1 days | ~$925 | fastest sane; watch us-east-1 g4dn spot capacity/AZ spread |

For contrast, the same table on **g5.xlarge spot** is ~2.2× the cost (~$1,990) for essentially the
same wall-clock, since the workload is CPU-bound — hence g4dn is the default. Cost is flat across
parallelism; **pick the column by how fast you need it, not by budget.** More parallelism only raises
cost via spot-interruption re-work (a few %) and per-instance scratch EBS.

---

## 4. Reproducibility — containerize this repo, pin everything

One Docker image = the local pipeline, byte-for-byte, on every worker.

- **Base:** an NVIDIA CUDA runtime image (e.g. `nvidia/cuda:12.x-runtime`) so the T4/A10G is visible.
- **Install this repo** (`src/morgoth_slowing/…`: `io/edf.py`, `features/extract.py`, `features/
  morphology.py`, the batch entrypoints modeled on `scripts/13`/`scripts/24`) as a package.
- **Pin versions** in a lockfile — CUDA wheels, not MPS: `torch`/`torchvision` (CUDA build),
  **`timm==1.0.11`**, `mne`, `einops`, `h5py`, `scipy`, `numpy`, `pandas`, `pyarrow`, plus the stager's
  `tensorboardX`, `mat73`, `pyhealth`. Heed `docs/sleep_staging.md` §5: **`pyhealth` pins `pandas<2`**
  and conflicts with the analysis stack — the *ingestion* container only needs staging + featurize, so
  build it around the staging env (pandas<2 is fine for writing parquet) and keep it isolated from the
  analysis venv. Pin `awscli`/`rclone` too.
- **Bake the model** into the image or pull `ss_hm_1.pth` (or `SLEEPPSG.pth` substitute) from
  `s3://bdsp-opendata-credentialed/morgoth2/models/202605/morgoth/` at container start via the task IAM
  role. Prefer the real `ss_hm_1.pth` for the production wave (ask the model owner) so cloud output
  matches the current cohort's stager.
- Tag the image immutably (git SHA) and record it in the run manifest so the wave is reproducible.
- Push to **Amazon ECR** in-region; Batch/EC2 pulls from there.

Entrypoint = "claim one recording → run the §1 loop → exit," parameterized by the queue/array index.
Same code path as `scripts/13`/`scripts/24`, just fed one recording at a time from the queue instead of
globbing a local dir.

---

## 5. Ops — resume, monitoring, spot, guardrails

**Checkpoint / resume (idempotent).** Before processing, the worker checks for
`s3://…/features/<bdsp_id>_<session>.done` (or `HeadObject` on the output parquet) and **skips** if
present. Write the `.done` marker only *after* the parquet upload succeeds. This makes the whole wave
safe to re-run: relaunch the array/queue and finished recordings are no-ops. Seed the queue from the
fixed candidate CSV (priority ≥ 4, with the pilot's path/duration fixes) so the work set is frozen.

**Spot-interruption handling.** Spot gives a ~2-minute termination notice. Keep the unit of work at
one recording (~6 min) so an interruption loses at most one in-flight recording — which is simply
re-queued (AWS Batch does this automatically; DIY: catch SIGTERM, don't delete the SQS message so it
returns after the visibility timeout). No partial parquet is ever published because the `.done` marker
is last. Spread the compute environment across **multiple AZs** and use
`SPOT_CAPACITY_OPTIMIZED` to reduce reclaim rate; optionally allow g4dn **and** g5 in the environment
so Batch can fall back if T4 capacity is tight.

**Monitoring.** CloudWatch: Batch job state (SUBMITTED/RUNNING/FAILED/SUCCEEDED), a custom
`recordings_done` count (from `.done` markers), GPU/CPU utilization (CloudWatch agent or DCGM), and a
dead-letter queue for recordings that fail 2× (e.g. `<15/19 channels`, corrupt EDF — `io/edf.py` and
the extractor already `raise`/`skip` these; route them to a "needs-review" list rather than blocking
the wave). A one-line progress query: `aws s3 ls s3://…/features/ | grep -c .done` vs 33,946.

**Hard cost guardrail.** This is a one-shot job — cap it:
- **AWS Budgets** action at, say, **$1,500** (≈ 1.5× the g4dn estimate) that triggers an SNS alert and,
  via a Budgets action, **stops the Batch compute environment / scales the ASG to 0**.
- A **max-vCPU ceiling** on the Batch compute environment (e.g. 25 instances × 4 = 100 vCPU) so it
  physically cannot balloon.
- Since the fleet auto-scales to 0 when the queue drains, idle spend is naturally ~0 — the budget
  action is the backstop against a runaway loop or a stuck retry.
- Tag every resource (`project=morgoth-slowing`, `wave=priority4`) for clean cost attribution and a
  one-click teardown afterwards.

---

## Summary (recommended config)

1. **~25× `g4dn.xlarge` spot** via AWS Batch, containerized (this repo, CUDA torch, `timm==1.0.11`,
   `ss_hm_1` stager), **in the buckets' region (us-east-1)** so S3 transfer is free.
2. Work-queue over the 33,946 priority ≥ 4 recordings; each worker pulls one EDF → stages (GPU) →
   featurizes + artifact-rejects (CPU) → writes a small feature parquet + `.done` marker → drops raw.
   Peak disk is a handful of recordings, never the 60 TB.
3. Throughput ≈ 10 recordings/hr/instance (CPU-bound; T4 ample) → ~3,400–3,750 instance-hours;
   GPU is idle ~85% of the time, which is why the cheap T4 box beats g5.
4. **Headline: ~$1,000 compute + < $5/month feature storage, ~6 days wall-clock.** Scale to 50
   instances for ~3 days at the same dollar cost, or drop to 5 for ~1 month.
5. Resumable via `.done` markers, spot-safe (one-recording units auto-requeued), capped by an AWS
   Budgets **$1,500** guardrail + a 100-vCPU ceiling; do the 100-recording validation pilot on one box
   first.

---

### Sources (verify before launch — spot re-prices continuously)
- [EC2 Spot Instances Pricing](https://aws.amazon.com/ec2/spot/pricing/) · [EC2 On-Demand Pricing](https://aws.amazon.com/ec2/pricing/on-demand/)
- [g5.xlarge specs & price (Vantage)](https://instances.vantage.sh/aws/ec2/g5.xlarge) — A10G, 4 vCPU/16 GiB, on-demand $1.006/hr, spot ~$0.552/hr
- [g4dn.xlarge specs & price (Vantage)](https://instances.vantage.sh/aws/ec2/g4dn.xlarge) — T4, 4 vCPU/16 GiB, on-demand $0.526/hr, spot ~$0.247/hr
- [S3 Pricing](https://aws.amazon.com/s3/pricing/) — S3 Standard $0.023/GB-mo (first 50 TB), us-east-1
- Repo: `docs/coverage_expansion_plan.md`, `docs/sleep_staging.md`, `src/morgoth_slowing/features/extract.py`, `src/morgoth_slowing/io/edf.py`, `scripts/13_recompute_features.py`, `scripts/24_morphology_features.py`
