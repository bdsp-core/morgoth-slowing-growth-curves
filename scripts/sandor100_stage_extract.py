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
import os, sys, shutil, subprocess, tempfile, importlib.util
from pathlib import Path
import numpy as np, pandas as pd

# --- Morgoth env (must be set BEFORE importing fleet.ingest, which reads them at import) ---
# The repo lives under ~/Desktop/GithubRepos on this machine; the old default pointed at
# ~/GithubRepos/morgoth2, which does not exist, so staging failed with a missing-checkpoint error that
# looked like the model was unavailable rather than mislocated. Search the plausible roots.
def _morgoth_dir():
    from pathlib import Path as _P
    for c in (_P.home() / "Desktop/GithubRepos/morgoth2", _P.home() / "GithubRepos/morgoth2",
              _P("../morgoth2").resolve()):
        if (c / "checkpoints" / "ss_hm_1.pth").exists():
            return str(c)
    return str(_P.home() / "GithubRepos/morgoth2")


os.environ.setdefault("MORGOTH2_DIR", _morgoth_dir())
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

# SANDOR_DIR must be settable: this defaulted to one developer's Box CloudStorage mount, so the SAI-100
# external validation could not be reproduced anywhere else. The default is the historical path purely
# so the old machine keeps working; everyone else exports SANDOR_DIR.
def _resolve_sandor_dir():
    """Locate the SAI-100 source, or say exactly how to point at it.

    This used to default to one developer's Box CloudStorage mount, so every other machine died with a
    FileNotFoundError deep inside pandas naming a stranger's home directory. The data is DUA-governed and
    cannot be committed, so a default is still needed -- but it must be a path that can plausibly exist
    here, and when it does not it must fail with an instruction rather than a stack trace.
    """
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("SANDOR_DIR")
    if env:
        return env
    for c in (_P.home() / "Desktop/GithubRepos/Sandor_100_local",
              _P.home() / "Sandor_100",
              _P("data/external/Sandor_100"),
              _P("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/"
                 "ChenXiSun/Morgoth1/Datasets/Sandor_100")):    # historical, so the original machine works
        if _P(c).is_dir():
            return str(c)
    raise SystemExit(
        "SAI-100 source not found. It is DUA-governed and not committed, so set SANDOR_DIR to the "
        "directory\nholding validation_study_excel_export.xlsx and Morgoth_results/, e.g.\n"
        "  export SANDOR_DIR=~/Desktop/GithubRepos/Sandor_100_local\n"
        "or run scripts/reproduce_story.sh, which skips this step cleanly when SANDOR_DIR is unset.")


SB_DIR = Path(os.environ.get("SANDOR_DIR") or
              _resolve_sandor_dir())
EDF = SB_DIR / "EDF"
SM = Path("data/derived/segment_master")
# Scratch space for the Morgoth staging hand-off. This was hardcoded to one session's scratchpad on another
# machine ("/private/tmp/claude-501/-Users-mwestover-.../543fcf0f-.../scratchpad/sandor100/work"), which is
# the same defect as the old SANDOR_DIR default: it happens to be writable, so staging fails deep inside the
# model call rather than at a clear "path does not exist". Honour SANDOR_WORK, else use a local scratch dir.
WORK = Path(os.environ.get("SANDOR_WORK") or (Path(tempfile.gettempdir()) / "sandor100_work"))


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
    # Prefer the published de-identified panel; the workbook is the fallback (see export_sai100_panel.py).
    _p = Path("data/derived/sai100_panel.parquet")
    if _p.exists():
        _d = pd.read_parquet(_p).drop_duplicates("file_name")
        age_of = {str(k).strip(): float(v) for k, v in zip(_d.file_name, _d.age_years)}
    else:
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
            # copy off Box CloudStorage to local first, with a bounded timeout (Box on-demand download can
            # hang; a big file times out and is skipped rather than wedging the whole run)
            with tempfile.TemporaryDirectory() as td:
                loc = os.path.join(td, "r.edf")
                subprocess.run(["cp", str(p), loc], check=True, timeout=300)
                data, chs, fs = load_edf_referential(loc)
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
