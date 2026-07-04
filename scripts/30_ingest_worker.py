"""Robust, resumable per-recording ingestion worker (replaces the fragile batch-at-end pilot).

For EACH selected recording, independently:
  pull EDF -> size-guard -> load (bounded) -> artifact-reject + featurize -> stage THAT recording
  (morgoth ss_hm_1) -> map stages -> per (region,stage) medians -> WRITE its outputs -> mark .done
  -> drop raw. A crash costs only the current recording; rerun skips anything already .done.

Persisted per recording (all with provenance), under data/derived/expansion/:
  features/<rid>.parquet   region x stage aggregated features
  stages/<rid>.csv         morgoth per-window sleep stages (pred_class) — the staging output
  provenance/<rid>.json    rid, source EDF path, code commit, timestamps, usable/total, age/sex/label
  done/<rid>.done          completion marker (resumability)

Gate (focal/gen/normal) probabilities are a separate pass (scripts/31) — needs the slowing checkpoints.

Run:  PYTHONPATH=src python scripts/30_ingest_worker.py [N]      (default N=25)
Env:  same as scripts/26 (RCLONE_BIN, MORGOTH2_DIR, PILOT_VENV, MORGOTH_DEVICE, PILOT_SCRATCH) +
      CODE_COMMIT (provenance), EXPANSION_MAX_GB (size guard, default 3.0).
"""
from __future__ import annotations
import os, sys, gc, json, time, subprocess, importlib.util, tempfile, shutil
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import savemat

# reuse the validated helpers from scripts/26 (select, edf_path, rclone, stage_dir, feature modules)
_spec = importlib.util.spec_from_file_location("p26", str(Path(__file__).with_name("26_slowing_ingest_pilot.py")))
p26 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p26)
ex, rec, af, st = p26.ex, p26.rec, p26.af, p26.st
load_edf_referential = p26.load_edf_referential

OUTDIR = Path("data/derived/expansion")
FEAT, STG, PROV, DONE = OUTDIR / "features", OUTDIR / "stages", OUTDIR / "provenance", OUTDIR / "done"
GATE = OUTDIR / "gate"
for d in (FEAT, STG, PROV, DONE, GATE):
    d.mkdir(parents=True, exist_ok=True)
COMMIT = os.environ.get("CODE_COMMIT", "unknown")
MAX_GB = float(os.environ.get("EXPANSION_MAX_GB", "3.0"))
RUN_GATE = os.environ.get("RUN_GATE", "1") == "1"        # focal/gen/normal Morgoth gate probs
GATE_STEP = os.environ.get("GATE_STEP", "10")            # window step (s) for gate heads (recording-level agg)
PROG = p26.OUT / "progress.jsonl"


def run_gate(sin, sout, rid):
    """Two-stage Morgoth gate on the recording's .mat (already in sin): NORMAL + SLOWING window heads
    -> NORMAL/FOC_SLOWING/GEN_SLOWING EEG-level aggregators. Returns per-recording probabilities."""
    def _win(ckpt, ds, outdir):
        subprocess.run(["bash", "-lc",
            f"cd {p26.M2} && OMP_NUM_THREADS=1 {p26.VENV} finetune_classification.py --abs_pos_emb "
            f"--model base_patch200_200 --predict --task_model checkpoints/{ckpt} --dataset {ds} "
            f"--data_format mat --sampling_rate 0 --already_format_channel_order no "
            f"--already_average_montage no --allow_missing_channels yes --max_length_hour no "
            f"--eval_sub_dir {sin} --eval_results_dir {outdir} --prediction_slipping_step_second {GATE_STEP} "
            f"--polarity 1 --rewrite_results no --num_workers 0 --device {p26.DEVICE}"],
            check=True, capture_output=True)

    def _eeg(ckpt, ds, csvdir, resdir):
        subprocess.run(["bash", "-lc",
            f"cd {p26.M2} && OMP_NUM_THREADS=1 {p26.VENV} EEG_level_head.py --mode predict "
            f"--task_model checkpoints/{ckpt} --dataset {ds} --test_csv_dir {csvdir} --result_dir {resdir}"],
            check=True, capture_output=True)

    pn, ps = f"{sout}/pred_NORMAL", f"{sout}/pred_SLOWING"
    _win("NORMAL.pth", "NORMAL", pn);   _eeg("NORMAL_EEGlevel.pth", "NORMAL", pn, str(sout))
    _win("SLOWING.pth", "SLOWING", ps)
    _eeg("FOC_SLOWING_EEGlevel.pth", "FOC_SLOWING", ps, str(sout))
    _eeg("GEN_SLOWING_EEGlevel.pth", "GEN_SLOWING", ps, str(sout))

    def _p(tag):
        f = Path(sout) / f"pred_EEG_level_{tag}.csv"
        if f.exists():
            d = pd.read_csv(f)
            if len(d):
                return float(d.probability.iloc[0]), int(d.pred_class.iloc[0])
        return None, None
    pnorm, cnorm = _p("NORMAL"); pfoc, cfoc = _p("FOC_SLOWING"); pgen, cgen = _p("GEN_SLOWING")
    return {"normal_head_prob": pnorm, "normal_pred_class": cnorm,
            "p_focal": pfoc, "focal_pred_class": cfoc,
            "p_generalized": pgen, "generalized_pred_class": cgen, "gate_step_s": int(GATE_STEP)}


def _prog(**kw):
    try:
        with open(PROG, "a") as fh:
            fh.write(json.dumps({"t": time.time(), **kw}) + "\n")
    except Exception:
        pass


def process_one(r, work):
    rid = f"{r.SiteID}{r.pid}_{r.date}"
    if (DONE / f"{rid}.done").exists():
        return "skip"
    ep = p26.edf_path(r)
    if not ep:
        return "noedf"
    sin, sout = work / "in", work / "out"
    for d in (sin, sout):
        shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    local = work / f"{rid}.edf"
    t_start = time.time()
    p26.rclone(["copy", f"bdsp:{ep}", str(work)])
    src = next(work.glob("*.edf")); src.rename(local)
    # size guard (bogus-duration multi-day recordings)
    import pyedflib
    _f = pyedflib.EdfReader(str(local)); _ns = _f.getNSamples(); _fs = _f.getSampleFrequencies(); _f._close()
    est_gb = max(int(_ns[k] * 200.0 / _fs[k]) for k in range(len(_ns)) if _fs[k] > 0) * 19 * 4 / 1e9
    if est_gb > MAX_GB:
        local.unlink(missing_ok=True)
        _prog(event="skip", rid=rid, est_gb=round(est_gb, 1))
        return "toobig"
    # featurize (bounded memory)
    data, chs, fs = load_edf_referential(str(local))
    data = data.astype(np.float32, copy=False)
    bip = ex.to_bipolar(ex.preprocess(data, fs), chs)
    segidx = ex.segment_indices(bip.shape[0])
    mask, reasons = af.usable_mask(bip, segidx, fs)
    usable_se = [(s, e) for i, (s, e) in enumerate(segidx) if mask[i]]
    feat_arrs = ex.segment_features_parallel(bip, usable_se, fs)      # multicore (fork+COW)
    feats = [(s, e, f) for (s, e), f in zip(usable_se, feat_arrs)]
    usable, total = int(mask.sum()), len(segidx)
    del bip, mask, segidx; gc.collect()
    # stage THIS recording
    savemat(str(sin / f"{rid}.mat"), {"Fs": float(fs), "channels": np.array(chs),
            "data": np.ascontiguousarray(data.T)}, do_compression=True)
    del data; gc.collect()
    p26.stage_dir(str(sin), str(sout))
    scsv = sout / f"{rid}.csv"
    pred = pd.read_csv(scsv).pred_class.to_numpy() if scsv.exists() else None
    # Morgoth gate (focal/gen/normal) on the same .mat, before it is dropped
    gate = None
    if RUN_GATE:
        try:
            gate = run_gate(sin, sout, rid)
            (GATE / f"{rid}.json").write_text(json.dumps({"bdsp_id": rid, **gate}, indent=2))
        except Exception as ge:
            print(f"    gate FAIL {rid}: {type(ge).__name__}: {ge}")
    # map stages -> per (region,stage) aggregated features
    rows = []
    label = "normal" if r.rnorm else ("focal_slow" if r.rfoc else "general_slow")
    for (s, e, feat) in feats:
        stage = "Other"
        if pred is not None:
            wi = int(((s + e) / 2 / 200.0) / 5.0)
            if 0 <= wi < len(pred):
                stage = st.STAGE.get(int(pred[wi]), "Other")
        base = {"bdsp_id": rid, "age": r.AgeAtVisit, "sex": r.SexDSC, "label": label, "stage": stage}
        for reg, chans in rec.REGIONS.items():
            bp = feat[chans, :6]
            d = rec._derived(np.nanmean(np.where(bp > 0, bp, np.nan), axis=0, keepdims=True))
            rows.append({**base, "region": reg, **{k: float(v[0]) for k, v in d.items()}})
    pd.DataFrame(rows).to_parquet(FEAT / f"{rid}.parquet")
    if scsv.exists():
        shutil.copy(scsv, STG / f"{rid}.csv")             # persist sleep staging
    (PROV / f"{rid}.json").write_text(json.dumps({
        "bdsp_id": rid, "source_edf": f"s3://bdsp-opendata-repository/EEG/{ep}", "code_commit": COMMIT,
        "processed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "usable_segments": usable, "total_segments": total, "n_stage_windows": int(len(pred)) if pred is not None else 0,
        "age": float(r.AgeAtVisit) if pd.notna(r.AgeAtVisit) else None, "sex": str(r.SexDSC), "label": label,
        "gate": gate, "seconds": round(time.time() - t_start, 1)}, indent=2))
    (DONE / f"{rid}.done").touch()
    local.unlink(missing_ok=True)
    return dict(rid=rid, usable=usable, total=total, label=label)


AGE_BINS = [0, 2, 5, 12, 17, 29, 44, 59, 74, 120]


def _ageband_stream(sub):
    """One recording at a time, round-robin across age bands (spreads ages)."""
    groups = [g.reset_index(drop=True) for _, g in sub.groupby("ageband", observed=True)]
    out, gi = [], [0] * len(groups)
    while any(gi[k] < len(groups[k]) for k in range(len(groups))):
        for k in range(len(groups)):
            if gi[k] < len(groups[k]):
                out.append(groups[k].iloc[gi[k]]); gi[k] += 1
    return out


def select_balanced(n):
    """INTERLEAVE the three labels (focal, gen, normal), each drawn round-robin across age bands, so the
    processing order is label-balanced AND age-spread throughout (not clustered by label). Excludes
    already-.done recordings for resumability."""
    j = p26.eligible().copy()
    j["plabel"] = np.where(j.rnorm == 1, "normal", np.where(j.rfoc == 1, "focal_slow", "general_slow"))
    j["ageband"] = pd.cut(pd.to_numeric(j.AgeAtVisit, errors="coerce"), bins=AGE_BINS)
    j["rid"] = j.SiteID.astype(str) + j.pid.astype(str) + "_" + j.date.astype(str)
    done_ids = {p.stem for p in DONE.glob("*.done")}
    j = j[~j.rid.isin(done_ids)]
    streams = {lab: _ageband_stream(j[j.plabel == lab]) for lab in ("focal_slow", "general_slow", "normal")}
    picks, si = [], {k: 0 for k in streams}
    order = ["focal_slow", "general_slow", "normal"]
    while len(picks) < n and any(si[k] < len(streams[k]) for k in order):
        for lab in order:
            if si[lab] < len(streams[lab]):
                picks.append(streams[lab][si[lab]]); si[lab] += 1
                if len(picks) >= n:
                    break
    return pd.DataFrame(picks), len(done_ids)


def main(n=25):
    picks, n_done = select_balanced(n)
    print(f"selected {len(picks)} recordings ({n_done} already done)")
    done_ids = {p.stem for p in DONE.glob("*.done")}
    _prog(event="start", total=int(len(picks)) + len(done_ids), done=len(done_ids))
    work = Path(tempfile.mkdtemp())
    n_ok = len(done_ids)
    try:
        for _, r in picks.iterrows():
            rid = f"{r.SiteID}{r.pid}_{r.date}"
            try:
                res = process_one(r, work)
                if isinstance(res, dict):
                    n_ok += 1
                    print(f"  DONE {rid}: {res['usable']}/{res['total']} ({res['label']})  [{n_ok} total]")
                    _prog(event="done", rid=rid, done=n_ok, usable=res["usable"], seg_total=res["total"], label=res["label"])
                else:
                    print(f"  {res} {rid}")
            except Exception as e:
                print(f"  FAIL {rid}: {type(e).__name__}: {e}")
                _prog(event="fail", rid=rid, done=n_ok, err=type(e).__name__)
            finally:
                for sub in ("in", "out"):
                    shutil.rmtree(work / sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    _prog(event="finish", done=n_ok)
    print(f"\n{n_ok} recordings persisted under {OUTDIR}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 25)
