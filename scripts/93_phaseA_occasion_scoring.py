"""PHASE A — score the 100 OccasionNoise EDFs with the UNCHANGED pipeline, as an external test set.

Predictions P1-P10 were fixed in docs/phaseA_preregistration.md BEFORE this ran. Report what happens.

Pipeline is byte-for-byte the one used to build the norms (scripts/30_ingest_worker.py::process_one):
  MNE read (pyedflib rejects the de-identified startdate) -> uV -> rename T7/T8/P7/P8 -> T3/T4/T5/T6
  -> preprocess(hp 0.5, notch 60) -> to_bipolar (18 derivations) -> 15-s segments (step 14 s)
  -> artifact rejection -> multitaper -> features_31 -> per (region, stage) aggregation
  -> sleep staging with the ORIGINAL ss_hm_1.pth checkpoint (recovered from Box)
  -> each (region, stage) z-scored against the routine (alert) clean-normal reference, age-kernel bw=5.

Stage 1 (this script): ingest + stage + featurize -> data/derived/occasion_features.parquet
Stage 2 (scripts/94):  score against the expert panel.

Run: PYTHONPATH=src MORGOTH2_DIR=~/GithubRepos/morgoth2 python scripts/93_phaseA_occasion_scoring.py
"""
from __future__ import annotations
import os, re, gc, sys, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import savemat

sys.path.insert(0, "src")
from morgoth_slowing.features import extract as ex, recording as rec, artifact as af
from morgoth_slowing.io import staging as st

SC = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
          "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/occ/edf")
M2 = os.environ.get("MORGOTH2_DIR", str(Path.home() / "GithubRepos/morgoth2"))
VENV = os.environ.get("PILOT_VENV", sys.executable)
DEVICE = os.environ.get("MORGOTH_DEVICE", "mps")
OUT = Path("data/derived/occasion_features.parquet")
STAGE_OUT = Path("data/derived/occasion_stages"); STAGE_OUT.mkdir(parents=True, exist_ok=True)
BATCH = 10

RENAME = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}
NEEDED = ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "C3", "C4",
          "P3", "P4", "O1", "O2", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz"]


def read_edf(path):
    """MNE read -> (data uV (n_samp, 19), ch_names, fs, age, sex). pyedflib rejects startdate 00.00.00."""
    import mne, warnings
    warnings.filterwarnings("ignore")
    raw = mne.io.read_raw_edf(str(path), preload=True, verbose="ERROR")
    raw.rename_channels({c: RENAME.get(c.strip(), c.strip()) for c in raw.ch_names})
    missing = [c for c in NEEDED if c not in raw.ch_names]
    if missing:
        raise RuntimeError(f"missing channels {missing}")
    raw.pick(NEEDED)
    if abs(raw.info["sfreq"] - 200.0) > 1e-6:
        raw.resample(200.0, verbose="ERROR")
    data = raw.get_data().T * 1e6                       # MNE gives volts -> uV
    # age/sex live in the EDF patient field, e.g. "11.0 F X X"
    hdr = open(path, "rb").read(88)[8:88].decode("latin-1")
    m = re.match(r"\s*([\d.]+)\s+([MF])", hdr)
    age = float(m.group(1)) if m else np.nan
    sex = m.group(2) if m else "U"
    return data.astype(np.float32), NEEDED, 200.0, age, sex


# morgoth2/utils.py imports pyhealth.metrics at module scope; pyhealth does not build on Python 3.14 and
# its metric functions are never called on the --predict path. Shim the import rather than patch the
# morgoth2 repo or pin an older interpreter. The shim raises if a metric fn is ever actually invoked.
SHIM = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
        "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/shims")


def stage_dir(indir, outdir):
    subprocess.run(["bash", "-lc",
        f"cd {M2} && PYTHONPATH={SHIM} PYTORCH_ENABLE_MPS_FALLBACK=1 OMP_NUM_THREADS=1 KMP_DUPLICATE_LIB_OK=TRUE "
        f"{VENV} finetune_classification.py --abs_pos_emb --model base_patch200_200 --predict "
        f"--task_model checkpoints/ss_hm_1.pth --dataset SLEEPPSG --data_format mat --sampling_rate 0 "
        f"--already_format_channel_order no --already_average_montage no --allow_missing_channels yes "
        f"--max_length_hour no --eval_sub_dir {indir} --eval_results_dir {outdir} "
        f"--prediction_slipping_step_second 5 --polarity 1 --rewrite_results no --num_workers 0 "
        f"--device {DEVICE}"], check=True, capture_output=True)


def main():
    edfs = sorted(SC.glob("*.edf"), key=lambda p: int(p.stem) if p.stem.isdigit() else 1e9)
    edfs = [p for p in edfs if p.stem.isdigit()]
    print(f"{len(edfs)} OccasionNoise EDFs")
    work = Path(tempfile.mkdtemp())
    all_rows, pending = [], []

    def flush(batch):
        """Stage a batch of .mat files, then map stages onto their segments."""
        if not batch:
            return
        sin, sout = work / "in", work / "out"
        for d in (sin, sout):
            shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        for fid, _, _, _, data, chs in batch:
            savemat(str(sin / f"{fid}.mat"), {"Fs": 200.0, "channels": np.array(chs),
                    "data": np.ascontiguousarray(data.T)}, do_compression=True)
        print(f"  staging {len(batch)} recordings...", flush=True)
        stage_dir(str(sin), str(sout))
        for fid, age, sex, feats, _, _ in batch:
            scsv = sout / f"{fid}.csv"
            pred = pd.read_csv(scsv).pred_class.to_numpy() if scsv.exists() else None
            if scsv.exists():
                shutil.copy(scsv, STAGE_OUT / f"{fid}.csv")
            for (s, e, feat) in feats:
                stage = "Other"
                if pred is not None:
                    wi = int(((s + e) / 2 / 200.0) / 5.0)
                    if 0 <= wi < len(pred):
                        stage = st.STAGE.get(int(pred[wi]), "Other")
                base = {"fid": int(fid), "age": age, "sex": sex, "stage": stage}
                for reg, chans in rec.REGIONS.items():
                    bp = feat[chans, :6]
                    d = rec._derived(np.nanmean(np.where(bp > 0, bp, np.nan), axis=0, keepdims=True))
                    all_rows.append({**base, "region": reg, **{k: float(v[0]) for k, v in d.items()}})
        batch.clear(); gc.collect()

    for k, p in enumerate(edfs):
        try:
            data, chs, fs, age, sex = read_edf(p)
            bip = ex.to_bipolar(ex.preprocess(data, fs), chs)
            segidx = ex.segment_indices(bip.shape[0])
            mask, _ = af.usable_mask(bip, segidx, fs)
            usable = [(s, e) for i, (s, e) in enumerate(segidx) if mask[i]]
            arrs = ex.segment_features_parallel(bip, usable, fs)
            feats = list(zip([s for s, _ in usable], [e for _, e in usable], arrs))
            del bip; gc.collect()
            pending.append((p.stem, age, sex, feats, data, chs))
            print(f"[{k+1}/{len(edfs)}] fid={p.stem} age={age} sex={sex} "
                  f"usable {len(usable)}/{len(segidx)}", flush=True)
        except Exception as exn:
            print(f"[{k+1}/{len(edfs)}] fid={p.stem} FAIL {type(exn).__name__}: {exn}", flush=True)
            continue
        if len(pending) >= BATCH:
            flush(pending)
    flush(pending)

    df = pd.DataFrame(all_rows)
    # aggregate segments -> one row per (fid, region, stage), matching channel_stage_features
    num = [c for c in df.columns if c not in ("fid", "age", "sex", "stage", "region")]
    agg = df.groupby(["fid", "age", "sex", "region", "stage"], observed=True)[num].mean().reset_index()
    agg["n_seg"] = df.groupby(["fid", "age", "sex", "region", "stage"], observed=True).size().values
    agg.to_parquet(OUT)
    print(f"\nwrote {OUT}: {len(agg):,} (fid,region,stage) rows over {agg.fid.nunique()} recordings")
    print("stage mix:", df[df.region == "whole_head"].stage.value_counts(normalize=True).round(3).to_dict())


if __name__ == "__main__":
    main()
