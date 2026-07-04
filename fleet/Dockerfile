# Fleet container: the validated slowing-ingestion pipeline for AWS Batch (GPU).
# Build context must contain both repos: morgoth-slowing-growth-curves/ and morgoth2/ (see .dockerignore).
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl unzip ca-certificates && \
    curl -s https://rclone.org/install.sh | bash && \
    curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscli.zip && \
    unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws* && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt
COPY morgoth-slowing-growth-curves /opt/morgoth-slowing-growth-curves
COPY morgoth2 /opt/morgoth2

# torch/torchvision already in the base image — do NOT reinstall
RUN pip install --no-cache-dir \
        numpy scipy pandas pyarrow pyyaml scikit-learn statsmodels pygam tableone \
        mne boto3 s3fs matplotlib seaborn pyedflib h5py tqdm \
        einops "timm==1.0.11" tensorboardX mat73 hdf5storage pyhealth pytest

ENV MORGOTH2_DIR=/opt/morgoth2 \
    PILOT_SCRATCH=/opt/scratch \
    RCLONE_BIN=rclone \
    MORGOTH_DEVICE=cuda \
    PYTHONPATH=/opt/morgoth-slowing-growth-curves/src \
    RUN_GATE=1 GATE_STEP=10

COPY morgoth-slowing-growth-curves/fleet/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh
WORKDIR /opt/morgoth-slowing-growth-curves
ENTRYPOINT ["/opt/entrypoint.sh"]
