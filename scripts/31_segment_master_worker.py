"""Canonical fleet worker (SAP §4–§5): per-recording -> segment_master + recording_meta + recording_labels.

Replaces the legacy aggregate worker (scripts/30, archived-behaviour). For EACH recording on the frozen
report manifest:
  resolve EDF on S3 -> pull -> cap to 24 h -> bipolar -> per-15s-segment multitaper PSD ->
  RETAIN every segment with artifact_flag/reason (flag, NOT strip) -> per (segment, region) features +
  van Putten metrics -> stage each segment (Morgoth ss_hm_1) -> per-segment gate (SEPARATE pass; needs the
  NORMAL/SLOWING checkpoints, RUN_GATE=1) -> write partitioned segment_master + sidecars -> mark .done.

Output (data/derived/segment_master/):
  segment_master/eeg_id=<id>/part.parquet   one row per (segment, region) — the canonical table
  recording_meta.parquet (appended)          one row per eeg_id
  recording_labels.parquet (appended)        one row per eeg_id (from the manifest)

Keyed on eeg_id (NOT bdsp_id). Env: MORGOTH2_DIR, PILOT_VENV, MORGOTH_DEVICE (staging); RUN_GATE=0 to skip
the gate locally (no slowing checkpoints); EXPANSION_MAX_GB; RCLONE_BIN; MANIFEST.
Run: PYTHONPATH=src python scripts/31_segment_master_worker.py [N]
"""
from __future__ import annotations
import os, sys, gc, json, time, subprocess, tempfile, shutil
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import savemat

from morgoth_slowing.features import extract as ex, artifact as af, vanputten as vp
from morgoth_slowing.features.recording import _AGG, _derived
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.fleet import ingest as fi

RC = os.environ.get("RCLONE_BIN", "/opt/homebrew/bin/rclone")
MANIFEST = os.environ.get("MANIFEST", "data/manifest/report_manifest_v3.parquet")
OUT = Path("data/derived/segment_master"); OUT.mkdir(parents=True, exist_ok=True)
DONE = OUT / "_done"; DONE.mkdir(exist_ok=True)
MAX_GB = float(os.environ.get("EXPANSION_MAX_GB", "3.0"))
RUN_GATE = os.environ.get("RUN_GATE", "0") == "1"       # Morgoth gate (NORMAL/SLOWING checkpoints in M2/checkpoints)
GATE_STEP = os.environ.get("GATE_STEP", "5")            # window step (s) for the per-window slowing head
COMMIT = os.environ.get("CODE_COMMIT", subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                                       capture_output=True, text=True).stdout.strip() or "unknown")
FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
         "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]


def resolve_edf(row):
    """List the subject dir and pick the EDF of the right task nearest the recording date."""
    out = subprocess.run([RC, "lsf", row.source_subject_dir, "--recursive", "--include", "*.edf"],
                         capture_output=True, text=True, timeout=120)
    edfs = [l for l in out.stdout.splitlines() if l.endswith(".edf") and f"task-{row.bids_task}" in l]
    if not edfs:
        edfs = [l for l in out.stdout.splitlines() if l.endswith(".edf")]
    if not edfs:
        return None
    # prefer a session whose scans date matches eeg_datetime; else the first (single-session = unambiguous)
    return row.source_subject_dir + sorted(edfs)[0]


def stage_segments(sin, sout, rid, n_seg, seg_centers_s):
    """Morgoth sleep-stage the recording; map per-5s-window pred_class to each 15-s segment center."""
    try:
        fi.stage_dir(str(sin), str(sout))
    except Exception as e:
        print(f"    stage FAIL {rid}: {type(e).__name__}"); return ["Other"] * n_seg
    scsv = sout / f"{rid}.csv"
    if not scsv.exists():
        return ["Other"] * n_seg
    pred = pd.read_csv(scsv).pred_class.to_numpy()
    from morgoth_slowing.io import staging as st
    stages = []
    for c in seg_centers_s:
        wi = int(c / 5.0)                                # 5-s stager window step
        stages.append(st.STAGE.get(int(pred[wi]), "Other") if 0 <= wi < len(pred) else "Other")
    return stages


def run_gate(sin, sout, rid, n_seg, centers_s):
    """Morgoth gate: per-window SLOWING head -> per-SEGMENT p_slowing; EEG-level FOC/GEN heads -> recording
    p_focal/p_generalized (broadcast to every segment). Needs NORMAL/SLOWING checkpoints in M2/checkpoints."""
    shim = os.path.abspath(fi.SHIMS)
    def _win(ckpt, ds, outdir):
        subprocess.run(["bash", "-lc",
            f"cd {fi.M2} && PYTHONPATH={shim}:${{PYTHONPATH}} PYTORCH_ENABLE_MPS_FALLBACK=1 KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 "
            f"{fi.VENV} finetune_classification.py --abs_pos_emb --model base_patch200_200 --predict "
            f"--task_model checkpoints/{ckpt} --dataset {ds} --data_format mat --sampling_rate 0 "
            f"--already_format_channel_order no --already_average_montage no --allow_missing_channels yes "
            f"--max_length_hour no --eval_sub_dir {sin} --eval_results_dir {outdir} "
            f"--prediction_slipping_step_second {GATE_STEP} --polarity 1 --rewrite_results no "
            f"--num_workers 0 --device {fi.DEVICE}"], check=True, capture_output=True)
    def _eeg(ckpt, ds, csvdir, resdir):
        subprocess.run(["bash", "-lc",
            f"cd {fi.M2} && PYTHONPATH={shim}:${{PYTHONPATH}} KMP_DUPLICATE_LIB_OK=TRUE {fi.VENV} EEG_level_head.py --mode predict "
            f"--task_model checkpoints/{ckpt} --dataset {ds} --test_csv_dir {csvdir} --result_dir {resdir}"],
            check=True, capture_output=True)
    ps = f"{sout}/pred_SLOWING"
    _win("SLOWING.pth", "SLOWING", ps)                      # per-window slowing (the per-segment source)
    # per-window slowing prob -> per-segment p_slowing (map segment center to window index)
    p_slow = [np.nan] * n_seg
    wf = next(Path(ps).glob("*.csv"), None)
    if wf is not None:
        w = pd.read_csv(wf)
        col = next((c for c in ("probability", "prob", "score", "pred_class") if c in w.columns), None)
        pw = w[col].to_numpy() if col else np.array([])
        step = float(GATE_STEP)
        for i, c in enumerate(centers_s):
            wi = int(c / step)
            if 0 <= wi < len(pw):
                p_slow[i] = float(pw[wi])
    # EEG-level focal/gen (best-effort; does not block per-segment p_slowing)
    p_focal = p_gen = np.nan
    def _eeg_prob(tag):
        f = Path(sout) / f"pred_EEG_level_{tag}.csv"
        if f.exists() and len(d := pd.read_csv(f)):
            return float(d.probability.iloc[0])
        return np.nan
    try:
        _eeg("FOC_SLOWING_EEGlevel.pth", "FOC_SLOWING", ps, str(sout)); p_focal = _eeg_prob("FOC_SLOWING")
        _eeg("GEN_SLOWING_EEGlevel.pth", "GEN_SLOWING", ps, str(sout)); p_gen = _eeg_prob("GEN_SLOWING")
    except Exception as e:
        print(f"    gate EEG-level (focal/gen) failed, p_slowing still captured: {type(e).__name__}")
    return p_slow, p_focal, p_gen


def segment_master_rows(eid, pid, edt, bip, fs, stages, gate=None):
    """One row per (segment, region) — retain ALL segments with artifact_flag (flag, not strip)."""
    segidx = ex.segment_indices(bip.shape[0])            # capped to 24 h
    rows = []
    for i, (s, e) in enumerate(segidx):
        seg = bip[s:e]
        ok, reason = af.segment_usable(seg, fs)
        freqs, psd = ex.multitaper_psd(seg.T, fs)        # (18, n_freq)
        stage = stages[i] if i < len(stages) else "Other"
        base = {"eeg_id": eid, "patient_id": pid, "eeg_datetime": edt, "segment": i,
                "t_start_s": float(s / fs), "stage": stage,
                "artifact_flag": (not ok), "artifact_reason": ("none" if ok else reason),
                "p_slowing": (float(gate[0][i]) if gate and i < len(gate[0]) else np.nan),
                "p_focal": (float(gate[1]) if gate else np.nan),
                "p_generalized": (float(gate[2]) if gate else np.nan)}
        for reg, chans in _AGG.items():
            bp = ex.band_powers(freqs, psd[chans])       # per-band mean over region channels
            bpmean = {k: float(np.mean(v)) for k, v in bp.items()}
            d = _derived(np.array([[bpmean[b] for b in ["delta", "theta", "alpha", "beta", "gamma", "total"]]]))
            row = {**base, "region": reg, **{k: float(v[0]) for k, v in d.items()}}
            row.update(DTABR=vp.dtabr(freqs, psd, chans), ADR=vp.adr(freqs, psd, chans),
                       SEF95=vp.sef(freqs, psd, 0.95, chans), median_freq=vp.median_freq(freqs, psd, chans),
                       peak_freq=vp.peak_freq(freqs, psd, chans))
            if reg == "whole_head":
                row.update(Q_SLOWING=vp.q_slowing(freqs, psd), Q_APG=vp.q_apg(freqs, psd),
                           r_sBSI=vp.r_sbsi(freqs, psd), pdBSI=vp.pdbsi(freqs, psd),
                           Q_ASYM=vp.q_asym(freqs, psd))
            rows.append(row)
    return rows


def process_one(m, work):
    eid = m.eeg_id
    if (DONE / f"{eid}.done").exists():
        return "skip"
    ep = resolve_edf(m)
    if not ep:
        return "noedf"
    local = work / "rec.edf"
    subprocess.run([RC, "copyto", ep, str(local)], check=True, capture_output=True, timeout=600)
    data, chs, fs = load_edf_referential(str(local))
    data = ex.cap_to_hours(data.astype(np.float32, copy=False), fs)
    n_hours = data.shape[0] / fs / 3600
    bip = ex.to_bipolar(ex.preprocess(data, fs), chs)
    segidx = ex.segment_indices(bip.shape[0])
    centers = [((s + e) / 2 / fs) for s, e in segidx]
    # stage (needs the full recording as .mat)
    sin, sout = work / "in", work / "out"
    for d in (sin, sout):
        shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    savemat(str(sin / f"{eid}.mat"), {"Fs": float(fs), "channels": np.array(chs),
            "data": np.ascontiguousarray(data.T)}, do_compression=True)
    del data; gc.collect()
    stages = stage_segments(sin, sout, eid, len(segidx), centers)
    gate = None
    if RUN_GATE:
        try:
            gate = run_gate(sin, sout, eid, len(segidx), centers)
        except Exception as e:
            print(f"    gate FAIL {eid}: {type(e).__name__}: {e}")
    rows = segment_master_rows(eid, m.patient_id, m.eeg_datetime, bip, fs, stages, gate)
    sm = pd.DataFrame(rows)
    n_seg, n_art = sm.segment.nunique(), int(sm[sm.region == "whole_head"].artifact_flag.sum())
    (OUT / f"eeg_id={eid}").mkdir(parents=True, exist_ok=True)
    sm.to_parquet(OUT / f"eeg_id={eid}" / "part.parquet", index=False)
    (DONE / f"{eid}.done").write_text(json.dumps({
        "eeg_id": eid, "source_edf": ep, "code_commit": COMMIT, "n_hours": round(n_hours, 2),
        "n_segments": int(n_seg), "n_artifact": n_art, "gate": RUN_GATE,
        "processed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
    local.unlink(missing_ok=True)
    return dict(eeg_id=eid, n_seg=int(n_seg), n_art=n_art, hours=round(n_hours, 2), stages=set(stages))


def main(n=10):
    man = pd.read_parquet(MANIFEST)
    meta_cols = ["eeg_id", "patient_id", "eeg_datetime", "src", "age", "sex", "recording_seconds", "bids_task"]
    label_cols = ["eeg_id", "is_abnormal", "has_focal_slow", "has_gen_slow", "clean_normal",
                  "focal_side", "focal_region", "focal_band", "gen_topography", "gen_band", "clean_pair"]
    task = os.environ.get("PILOT_TASK", "rEEG")          # routine EEGs = small/fast for the pilot
    picks = (man[man.bids_task == task] if task in set(man.bids_task.dropna()) else man).head(n)
    work = Path(tempfile.mkdtemp()); ok = 0
    try:
        for _, m in picks.iterrows():
            try:
                r = process_one(m, work)
                if isinstance(r, dict):
                    ok += 1
                    print(f"  OK {r['eeg_id']}: {r['n_seg']} seg, {r['n_art']} artifact, {r['hours']}h, stages={r['stages']}")
                else:
                    print(f"  {r} {m.eeg_id}")
            except Exception as e:
                print(f"  FAIL {m.eeg_id}: {type(e).__name__}: {e}")
            finally:
                for sub in ("in", "out"):
                    shutil.rmtree(work / sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # append the sidecars for the recordings we processed
    done_ids = {p.stem for p in DONE.glob("*.done")}
    sub = man[man.eeg_id.isin(done_ids)]
    sub[[c for c in meta_cols if c in sub.columns]].to_parquet(OUT.parent / "recording_meta.parquet", index=False)
    sub[[c for c in label_cols if c in sub.columns]].to_parquet(OUT.parent / "recording_labels.parquet", index=False)
    print(f"\ndone: {ok}/{len(picks)} -> {OUT} (+ recording_meta/labels). segment_master partitions: {len(done_ids)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
