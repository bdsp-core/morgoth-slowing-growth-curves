"""Shared fleet-ingest logic — config + helpers used by the ingest worker (`scripts/30`).

Lifted from the legacy `scripts/26_slowing_ingest_pilot.py` so the fleet worker does not import a script
named *pilot* by file path (analysis_plan.md §12.1: "inventory & separate the fleet code"). All paths are
env-configurable so the same code runs locally (Mac/MPS) and on a cloud GPU box (CUDA).

Re-exports the feature/io modules the worker needs (`ex`, `rec`, `af`, `st`, `load_edf_referential`) so
callers import them from one place.
"""
from __future__ import annotations
import os, json, time, subprocess
from pathlib import Path
import pandas as pd

from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.features import extract as ex, recording as rec, artifact as af
from morgoth_slowing.io import staging as st

# --- config (env-overridable; defaults reproduce the original local behavior) --------------------
RC = os.environ.get("RCLONE_BIN", str(Path.home() / ".local/bin/rclone"))
REPO = os.environ.get("BDSP_EEG_REPO", "bdsp-opendata-repository/EEG")
SCRATCH = Path(os.environ.get("PILOT_SCRATCH", "scratch"))            # holds eegmeta/ and reports/
M2 = os.environ.get("MORGOTH2_DIR", str(SCRATCH / "morgoth2"))
VENV = os.environ.get("PILOT_VENV", "python")
DEVICE = os.environ.get("MORGOTH_DEVICE", "mps")                      # "cuda" on the cloud GPU box
SHIMS = os.environ.get("MORGOTH_SHIMS", "scripts/shims")             # lightweight pyhealth shim for the stager
OUT = Path("data/derived"); STAGES = ["W", "N1", "N2", "N3", "REM"]
PROG = OUT / "progress.jsonl"


def _prog(**kw):
    """Append one timestamped progress event (drives the burndown dashboard)."""
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        with open(PROG, "a") as fh:
            fh.write(json.dumps({"t": time.time(), **kw}) + "\n")
    except Exception:
        pass


def rclone(args):
    subprocess.run([RC] + args, check=True, capture_output=True)


def eligible():
    """Full pool of ingestable recordings: report-labeled, 6-48 h, not already in the growth-curves
    cohort. Returns the joined/filtered metadata frame (one row per recording)."""
    meta = pd.concat([pd.read_csv(f, low_memory=False) for f in sorted((SCRATCH / "eegmeta").glob("S000*_eeg_metadata*.csv"))])
    fnd = pd.concat([pd.read_csv(f, low_memory=False) for f in sorted((SCRATCH / "reports").glob("S000*_EEG__reports_findings.csv"))])
    fnd["pid"] = fnd.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    fnd["date"] = pd.to_datetime(fnd["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    hr = lambda c: fnd[c].astype(str).str.contains("report", case=False, na=False)
    fnd = fnd.assign(rnorm=hr("normal").astype(int), rfoc=hr("foc slowing").astype(int), rgen=hr("gen slowing").astype(int))
    meta["pid"] = meta.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    meta["date"] = pd.to_datetime(meta.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    meta["dur_h"] = meta.DurationInSeconds / 3600
    j = meta.merge(fnd[["pid", "date", "rnorm", "rfoc", "rgen"]], on=["pid", "date"], how="inner")
    j = j[(j.dur_h > 6) & (j.dur_h < 48) & ((j.rnorm | j.rfoc | j.rgen) > 0)]
    cohort = set(pd.read_csv("metadata/cohort_metadata.csv").bdsp_id.str.replace(r"^S000\d", "", regex=True))
    return j[~j.pid.isin(cohort)]


def select(n):
    j = eligible()
    picks = pd.concat([j[j.rnorm == 1].head(n // 2), j[j.rfoc == 1].head(n - n // 2),
                       j[j.rgen == 1].head(2)]).drop_duplicates("pid").head(n)
    return picks


def edf_path(row):
    site = row.SiteID; bf = row.BidsFolder; ses = row.SessionID
    d = f"{REPO}/bids/{site}/{bf}/ses-{ses}/eeg"
    out = subprocess.run([RC, "lsf", f"bdsp:{d}"], capture_output=True, text=True)
    edfs = [l for l in out.stdout.splitlines() if l.endswith(".edf")]
    return f"{d}/{edfs[0]}" if edfs else None


def stage_dir(indir, outdir):
    _shims = os.path.abspath(SHIMS)
    subprocess.run(["bash", "-lc",
        f"cd {M2} && PYTHONPATH={_shims}:${{PYTHONPATH}} PYTORCH_ENABLE_MPS_FALLBACK=1 KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 {VENV} finetune_classification.py "
        f"--abs_pos_emb --model base_patch200_200 --predict --task_model checkpoints/ss_hm_1.pth "
        f"--dataset SLEEPPSG --data_format mat --sampling_rate 0 --already_format_channel_order no "
        f"--already_average_montage no --allow_missing_channels yes --max_length_hour no "
        f"--eval_sub_dir {indir} --eval_results_dir {outdir} --prediction_slipping_step_second 5 "
        f"--polarity 1 --rewrite_results no --num_workers 0 --device {DEVICE}"], check=True, capture_output=True)
