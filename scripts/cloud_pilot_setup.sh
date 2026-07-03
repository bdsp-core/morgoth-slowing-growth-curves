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
  source .venv/bin/activate
  export PILOT_VENV="$(command -v python)"
  export PYTHONPATH=src
  echo ">>> torch CUDA check:"; python -c "import torch;print('cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
  python scripts/26_slowing_ingest_pilot.py "$N"
  exit 0
fi

echo ">>> [1/6] system deps"
sudo apt-get update -qq && sudo apt-get install -y -qq unzip git

echo ">>> [2/6] clone repos"
[ -d "$REPO" ] || git clone https://github.com/bdsp-core/morgoth-slowing-growth-curves.git "$REPO"
[ -d "$MORGOTH2_DIR" ] || git clone --depth 1 https://github.com/bdsp-core/morgoth2 "$MORGOTH2_DIR"

echo ">>> [3/6] checkpoint + selection metadata into place"
mkdir -p "$MORGOTH2_DIR/checkpoints" "$PILOT_SCRATCH"
[ -f ~/ss_hm_1.pth ] && mv ~/ss_hm_1.pth "$MORGOTH2_DIR/checkpoints/" || echo "  (ss_hm_1.pth already moved?)"
[ -d ~/eegmeta ] && mv ~/eegmeta "$PILOT_SCRATCH/" || echo "  (eegmeta already in place?)"
[ -d ~/reports ] && mv ~/reports "$PILOT_SCRATCH/" || echo "  (reports already in place?)"

echo ">>> [4/6] python venv (inherits the AMI's CUDA torch via system-site-packages)"
cd "$REPO"
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -q -U pip
# our deps + morgoth2's runtime deps; torch/torchvision come from the AMI (do NOT reinstall)
pip install -q numpy scipy pandas pyarrow pyyaml scikit-learn statsmodels pygam \
    mne boto3 s3fs matplotlib seaborn pyedflib h5py \
    einops "timm==1.0.11" tensorboardX mat73 hdf5storage
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
