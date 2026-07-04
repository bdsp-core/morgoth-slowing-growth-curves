#!/usr/bin/env bash
# One-shot setup for the slowing-ingestion PILOT on a fresh us-east-1 GPU box
# (Deep Learning OSS Nvidia Driver AMI, Ubuntu 24.04, g4dn.xlarge).
#
# Prereqs already on the box (scp'd from the Mac into ~ before running this):
#   ~/bdsp_opendata_write_accessKeys.csv   (BDSP S3 keys)
#   ~/ss_hm_1.pth                          (sleep-staging checkpoint, 67 MB)
#   ~/eegmeta/  ~/reports/                 (selection metadata CSVs)
#
# Run:  bash cloud_pilot_setup.sh   then   bash cloud_pilot_setup.sh run 10
set -euo pipefail

REPO=~/morgoth-slowing-growth-curves
export MORGOTH2_DIR=~/morgoth2
export PILOT_SCRATCH=~/pilot_data
export RCLONE_BIN=rclone
export MORGOTH_DEVICE=cuda

if [ "${1:-setup}" = "run" ]; then
  N="${2:-10}"
  cd "$REPO"
  mkdir -p data/derived results/figs                  # data/ is excluded from the copy
  source .venv/bin/activate
  export PILOT_VENV="$(command -v python)"
  export PYTHONPATH=src
  export PYTHONUNBUFFERED=1                            # live progress when redirected to a log
  echo ">>> torch CUDA check:"; python -c "import torch;print('cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
  python scripts/26_slowing_ingest_pilot.py "$N"
  exit 0
fi

if [ "${1:-setup}" = "worker" ]; then                   # robust, resumable per-recording ingestion
  N="${2:-25}"
  cd "$REPO"
  mkdir -p data/derived results/figs
  source .venv/bin/activate
  export PILOT_VENV="$(command -v python)"
  export PYTHONPATH=src PYTHONUNBUFFERED=1
  export CODE_COMMIT="$(cat ~/CODE_COMMIT 2>/dev/null || echo unknown)"
  echo ">>> torch CUDA check:"; python -c "import torch;print('cuda',torch.cuda.is_available())"
  python scripts/30_ingest_worker.py "$N"
  exit 0
fi

echo ">>> [1/6] system deps"
sudo apt-get update -qq && sudo apt-get install -y -qq unzip git rsync python3.12-venv

echo ">>> [2/6] verify repos (rsync'd from the Mac — both are private, so no git clone)"
for d in "$REPO" "$MORGOTH2_DIR"; do
  [ -d "$d" ] || { echo "  !! $d missing — rsync it from your Mac first (see block above)"; exit 1; }
done

echo ">>> [3/6] checkpoint + selection metadata into place"
mkdir -p "$MORGOTH2_DIR/checkpoints" "$PILOT_SCRATCH"
[ -f ~/ss_hm_1.pth ] && mv ~/ss_hm_1.pth "$MORGOTH2_DIR/checkpoints/" || echo "  (ss_hm_1.pth already moved?)"
[ -d ~/eegmeta ] && mv ~/eegmeta "$PILOT_SCRATCH/" || echo "  (eegmeta already in place?)"
[ -d ~/reports ] && mv ~/reports "$PILOT_SCRATCH/" || echo "  (reports already in place?)"

echo ">>> [4/6] python venv (self-contained: CUDA torch from PyPI + all deps; apex NOT needed for --predict)"
cd "$REPO"
python3 -m venv .venv
source .venv/bin/activate
pip install -q -U pip
pip install -q torch torchvision                      # Linux x86 PyPI wheel = CUDA build
# our deps + morgoth2's runtime deps for inference (tableone added for the live Table 1 refresh)
pip install -q numpy scipy pandas pyarrow pyyaml scikit-learn statsmodels pygam tableone \
    mne boto3 s3fs matplotlib seaborn pyedflib h5py tqdm \
    einops "timm==1.0.11" tensorboardX mat73 hdf5storage pyhealth
python -c "import torch;assert torch.cuda.is_available(),'CUDA not visible!';print('  torch',torch.__version__,'CUDA OK:',torch.cuda.get_device_name(0))"

echo ">>> [5/6] rclone + BDSP S3 remote 'bdsp:'"
command -v rclone >/dev/null || { curl -s https://rclone.org/install.sh | sudo bash; }
mkdir -p ~/.config/rclone
KID=$(python3 -c "import csv;r=list(csv.DictReader(open('$HOME/bdsp_opendata_write_accessKeys.csv')))[0];print(r.get('Access key ID') or r.get('Access key id'))")
SEC=$(python3 -c "import csv;r=list(csv.DictReader(open('$HOME/bdsp_opendata_write_accessKeys.csv')))[0];print(r['Secret access key'])")
cat > ~/.config/rclone/rclone.conf <<EOF
[bdsp]
type = s3
provider = AWS
access_key_id = $KID
secret_access_key = $SEC
region = us-east-1
EOF
rclone lsd bdsp:bdsp-opendata-repository/EEG/bids 2>/dev/null | head -3 && echo "  rclone bdsp: OK" || echo "  !! rclone could not list — check keys"

echo ">>> [6/6] setup done. Now run:  bash scripts/cloud_pilot_setup.sh run 10"
