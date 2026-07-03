# AWS getting started — hands-on (single instance → fleet)

Companion to `aws_cloud_plan.md` (the architecture/cost). This is the **step-by-step** to get running.
Strategy: **Phase A** — one GPU instance, validate the pipeline on ~10 recordings (cheap, fast to
debug). **Phase B** — scale to the spot fleet / AWS Batch for the full 33,946.

## Prereqs (one-time)
- An AWS account with permission to launch EC2 + (later) AWS Batch, in **us-east-1** (same region as
  the `bdsp-opendata-*` S3 buckets → transfer is free; other regions cost ~$0.09/GB egress).
- AWS CLI configured on your laptop (`aws configure`) with those permissions.
- The **BDSP S3 keys** (from `~/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv`) — the
  instance uses these to read the credentialed buckets (independent of your EC2 account).
- An EC2 key pair for SSH (or use SSM Session Manager).

## Phase A — one instance, validate (~30–60 min, ~$0.30)
1. **Launch a spot g4dn.xlarge** in us-east-1 with the Deep Learning AMI (has CUDA/PyTorch), 200 GB gp3:
   ```bash
   aws ec2 run-instances --region us-east-1 \
     --image-id <DLAMI-GPU-ami-id> --instance-type g4dn.xlarge \
     --instance-market-options 'MarketType=spot' \
     --key-name <your-keypair> --block-device-mappings \
     'DeviceName=/dev/xvda,Ebs={VolumeSize=200,VolumeType=gp3}' \
     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=morgoth-pilot}]'
   ```
   (Or the console: EC2 → Launch → DLAMI (Ubuntu, GPU) → g4dn.xlarge → Spot → 200 GB gp3.)
2. **SSH in**, set up the pipeline:
   ```bash
   ssh -i <key.pem> ubuntu@<instance-ip>
   git clone https://github.com/bdsp-core/morgoth-slowing-growth-curves.git && cd $_
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt torch torchvision mne einops "timm==1.0.11" h5py tensorboardX mat73 pyhealth hdf5storage pyedflib
   git clone --depth 1 https://github.com/bdsp-core/morgoth2 ../morgoth2   # stager code
   # rclone + BDSP keys for S3, + the ss_hm_1 checkpoint (from Box or S3 models dir)
   ```
   Configure rclone remote `bdsp:` with the BDSP keys; put `ss_hm_1.pth` in `../morgoth2/checkpoints/`.
   **On CUDA, drop the MPS flag** (`--device cuda`); the code is otherwise identical.
3. **Run the pilot on ~10 recordings** and confirm features match local (rel_delta in cohort range,
   sane stages):
   ```bash
   PYTHONPATH=src python scripts/26_slowing_ingest_pilot.py 10
   ```
4. **Confirm** `data/derived/expansion_pilot_features.parquet` looks right, then terminate the instance.

## Phase B — scale to the full wave (see aws_cloud_plan.md)
- Containerize the validated setup (Dockerfile pinning the deps above).
- Put the candidate list (with EDF paths + duration-outliers dropped) as a work manifest in S3.
- **AWS Batch** (managed) or a fleet of ~25 g4dn.xlarge spot: each job = one recording (pull→stage→
  featurize→write features to S3→drop raw); resumable via S3 `.done` markers; `$1,500` AWS Budget
  guardrail. ~$1,000, ~6 days at 25 instances (or fewer/slower — cost is ~flat, pick by wall-clock).

## Guardrails
- Spot only; one-recording work units auto-requeue on interruption.
- Never store raw at scale — pull→process→drop per recording.
- Same-region (us-east-1) to keep S3 transfer free.
- Set an AWS Budgets alert at $1,500 before launching Phase B.
