"""SB / Sandor_100 external validation — PHASE 1: Morgoth sleep-stage + feature-extract the 100 EDFs into
segment_master partitions (eeg_id=SB_NNN), exactly as the fleet does for cohort/panels, so the existing
detector (scripts/53->54/55) applies UNCHANGED.

For each ID-NNN.edf: load referential -> preprocess -> 18 bipolar -> savemat -> Morgoth ss_hm_1 staging
(fleet.ingest.stage_dir) -> per-15 s stage -> per-(segment,channel) features (31.segment_master_rows) ->
write data/derived/segment_master/eeg_id=SB_NNN/part.parquet (+ summary). Skips recordings already built.

Env (defaulted here): MORGOTH2_DIR, PILOT_VENV, MORGOTH_DEVICE=mps, MORGOTH_SHIMS. Needs the morgoth2 repo
with checkpoints/ss_hm_1.pth and a torch+timm python.
Run: PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/sandor100_stage_extract.py
"""
from __future__ import annotations
import os, sys, shutil, importlib.util
from pathlib import Path
import numpy as np, pandas as pd

# --- Morgoth env (must be set BEFORE importing fleet.ingest, which reads them at import) ---
os.environ.setdefault("MORGOTH2_DIR", os.path.expanduser("~/GithubRepos/morgoth2"))
os.environ.setdefault("PILOT_VENV", sys.executable)
os.environ.setdefault("MORGOTH_DEVICE", "mps")
os.environ.setdefault("MORGOTH_SHIMS", os.path.abspath("scripts/shims"))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from scipy.io import savemat
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.io import staging as st
from morgoth_slowing.features import extract as ex
from morgoth_slowing.fleet import ingest as fi

# import 31 for segment_master_rows
_s = importlib.util.spec_from_file_location("m31", "scripts/31_segment_master_worker.py")
m31 = importlib.util.module_from_spec(_s); _s.loader.exec_module(m31)

SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100")
EDF = SB_DIR / "EDF"
SM = Path("data/derived/segment_master")
WORK = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
            "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/sandor100/work")


def stage_one(eid, data, chs, fs, n_seg, centers):
    sin, sout = WORK / eid / "in", WORK / eid / "out"
    for d in (sin, sout):
        shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    savemat(str(sin / f"{eid}.mat"), {"Fs": float(fs), "channels": np.array(chs),
            "data": np.ascontiguousarray(data.T)}, do_compression=True)
    fi.stage_dir(str(sin), str(sout))
    df = pd.read_csv(sout / f"{eid}.csv"); pred = df["pred_class"].to_numpy()
    stages = [st.STAGE.get(int(pred[int(c / 5.0)]), "Other") if 0 <= int(c / 5.0) < len(pred) else "Other"
              for c in centers]
    shutil.rmtree(WORK / eid, ignore_errors=True)
    return stages


def main():
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age_of = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    edfs = sorted(EDF.glob("ID-*.edf"), key=lambda p: int(p.stem.split("-")[1]))
    print(f"staging + extracting {len(edfs)} Sandor_100 EDFs -> segment_master (SB_NNN) ...", flush=True)
    done = fail = skip = 0
    for p in edfs:
        n = int(p.stem.split("-")[1]); eid = f"SB_{n:03d}"; key = f"ID{n:03d}"
        out = SM / f"eeg_id={eid}"
        if (out / "part.parquet").exists():
            skip += 1; continue
        try:
            data, chs, fs = load_edf_referential(str(p))
            bip = ex.to_bipolar(ex.preprocess(data.astype(np.float32), fs), chs)
            segidx = ex.segment_indices(bip.shape[0]); centers = [((s + e) / 2 / fs) for s, e in segidx]
            stages = stage_one(eid, data, chs, fs, len(segidx), centers)
            crows, srows = m31.segment_master_rows(eid, key, key, bip, fs, stages, gate=None)
            out.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(crows).to_parquet(out / "part.parquet", index=False)
            sd = SM.parent / "segment_summary" / f"eeg_id={eid}"; sd.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(srows).to_parquet(sd / "part.parquet", index=False)
            done += 1
            sdist = pd.Series(stages).value_counts().to_dict()
            print(f"  {eid} (age {age_of.get(key,'?')}): {len(segidx)} seg, stages {sdist}", flush=True)
        except Exception as e:
            fail += 1; print(f"  {eid}: FAIL {type(e).__name__}: {e}", flush=True)
    print(f"\ndone {done} | skipped(existing) {skip} | failed {fail}")


if __name__ == "__main__":
    main()
