"""Canonical fleet worker (SAP §4–§5): per-recording -> segment_master + segment_summary + per-eeg sidecars.

Replaces the legacy aggregate worker (scripts/30, archived). For EACH recording on the frozen manifest
(v6, pre-flight-resolved):
  resolve the EXACT EDF on S3 (decide_edf: match eeg_datetime->scans.tsv, hard-fail on ambiguity) -> pull
  -> cap to 24 h (read-time) -> bipolar -> per-15s-segment multitaper PSD -> RETAIN every segment with
  artifact_flag/reason (flag, NOT strip) -> PER-CHANNEL (18 bipolar) features + van Putten -> stage each
  segment (Morgoth ss_hm_1) -> per-segment gate (SEPARATE pass; NORMAL/SLOWING checkpoints, RUN_GATE=1) ->
  write partitioned segment_master + segment_summary + per-eeg .done/.status sidecars.

Writes ONLY per-eeg_id files (crash-safe, shard-safe); the one-row-per-EEG run ledger (recording_meta /
recording_labels) is assembled SEPARATELY by scripts/33 after all shards finish (never a global write here).
Output under OUTPUT_ROOT (default data/derived):
  segment_master/eeg_id=<id>/part.parquet    one row per (segment, CHANNEL) — regions derived downstream
  segment_summary/eeg_id=<id>/part.parquet   one row per (segment): stage, artifact, p_slowing, whole-head vP
  segment_master/_done/<id>.done             success + stats + sha256 (ledger input)
  segment_master/_status/<id>.status         non-success outcome (noedf / ambiguous / error:*)

Keyed on eeg_id (NOT bdsp_id). Env: MORGOTH2_DIR, PILOT_VENV, MORGOTH_DEVICE (staging); RUN_GATE=1 for the
gate; PANEL_ROOT for panel sources; OUTPUT_ROOT; RCLONE_BIN; MANIFEST; SHARD="i/N" for parallel runs.
Run: PYTHONPATH=src python scripts/31_segment_master_worker.py [N]   (SHARD=i/N for the fleet)
"""
from __future__ import annotations
import os, sys, gc, json, time, subprocess, tempfile, shutil, hashlib
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import savemat

from morgoth_slowing.features import extract as ex, artifact as af, vanputten as vp
from morgoth_slowing.features.recording import _derived, CH_NAMES
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.fleet import ingest as fi

RC = os.environ.get("RCLONE_BIN", "/opt/homebrew/bin/rclone")
# Panel EEGs (OccasionNoise / MoE) carry a RELATIVE source_path (occasionnoise/<fid>.edf, moe/<event>.mat);
# PANEL_ROOT resolves it. Local dir for pilots; s3://<bucket>/panels or an rclone remote for the fleet
# (the box has no scratchpad). See docs/fleet_launch.md §0b.
PANEL_ROOT = os.environ.get("PANEL_ROOT", "").rstrip("/")
MANIFEST = os.environ.get("MANIFEST", "data/manifest/report_manifest_v6.parquet")  # v6 = pre-flight-resolved (scripts/129)
# OUTPUT_ROOT lets the fleet write to a durable/shared location; sync to the S3 output bucket (see
# docs/fleet_launch.md "Outputs"). Everything the analysis plan consumes lands under here.
OUTROOT = Path(os.environ.get("OUTPUT_ROOT", "data/derived"))
OUT = OUTROOT / "segment_master"; OUT.mkdir(parents=True, exist_ok=True)          # per (segment, channel)
SUMM = OUTROOT / "segment_summary"; SUMM.mkdir(parents=True, exist_ok=True)       # per segment (whole-head)
DONE = OUT / "_done"; DONE.mkdir(exist_ok=True)                                  # success sidecars (per eeg_id)
STATUS = OUT / "_status"; STATUS.mkdir(exist_ok=True)                             # non-success outcomes (per eeg_id)
MAX_GB = float(os.environ.get("EXPANSION_MAX_GB", "3.0"))
RUN_GATE = os.environ.get("RUN_GATE", "0") == "1"       # Morgoth gate (NORMAL/SLOWING checkpoints in M2/checkpoints)
GATE_STEP = os.environ.get("GATE_STEP", "5")            # window step (s) for the per-window slowing head
COMMIT = os.environ.get("CODE_COMMIT", subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                                       capture_output=True, text=True).stdout.strip() or "unknown")
FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_gamma", "log_total",
         "rel_delta", "rel_theta", "rel_alpha", "DAR", "TAR", "DTR", "low_freq_rel"]


def _sha256(path, chunk=1 << 20):
    """Streaming sha256 of the analyzed source file (B2 integrity stamp)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def _acq_time(base, rel):
    """Read a BIDS session's scans.tsv acq_time for the EDF `rel` and normalize to YYYYMMDDHHMMSS.
    rel = 'ses-9/eeg/sub-XXX_ses-9_task-rEEG_eeg.edf' -> scans 'ses-9/sub-XXX_ses-9_scans.tsv'."""
    ses = rel.split("/")[0]
    stem = Path(rel).name.split("_task-")[0]                 # 'sub-XXX_ses-9'
    scans = f"{base}{ses}/{stem}_scans.tsv"
    out = subprocess.run([RC, "cat", scans], capture_output=True, text=True, timeout=30)
    for line in out.stdout.splitlines():
        if line.endswith(".edf") or "\t" in line and "acq_time" not in line:
            parts = line.split("\t")
            if len(parts) >= 2 and Path(parts[0]).name == Path(rel).name:
                return "".join(ch for ch in parts[1] if ch.isdigit())[:14]
    return None


def decide_edf(base, task, want, edfs, acq_fn):
    """The ONE resolution decision — shared by the worker (resolve_edf) and the pre-flight (scripts/129)
    so both agree exactly. `edfs` = subject's EDF rel-paths; `acq_fn(rel)` -> scans.tsv acq_time
    (YYYYMMDDHHMMSS) for that rel. Returns (path|None, reason). Hard-fails on zero/ambiguous matches."""
    task_edfs = [l for l in edfs if f"task-{task}" in l] or edfs
    if not task_edfs:
        return None, "noedf"
    if len(task_edfs) == 1:
        return base + task_edfs[0], "single"                       # one candidate = unambiguous
    want = "".join(ch for ch in str(want) if ch.isdigit())[:14]
    if len(task_edfs) > 60:                                         # pathological many-session subject:
        return None, f"toomany:{len(task_edfs)}"                   # bound scans reads (never a real cohort row)
    acq = {rel: acq_fn(rel) for rel in task_edfs}                  # one scans.tsv read each
    sec = [rel for rel, a in acq.items() if a == want]            # exact second match
    if len(sec) == 1:
        return base + sec[0], "sec-match"
    day = [rel for rel, a in acq.items() if a and a[:8] == want[:8]]  # fall back to the calendar day
    if len(day) == 1:
        return base + day[0], "day-match"                          # unique day -> safe despite time rounding
    return None, f"ambiguous:{len(sec)}of{len(task_edfs)}"         # 0 or >1 -> refuse to guess


def resolve_edf(row):
    """Resolve the EXACT session EDF by matching `eeg_datetime` to the BIDS scans.tsv acq_time.
    BIDS sessions are ordinal (ses-2, ses-9, ...) and do NOT encode the date, so a subject with N
    recordings needs date disambiguation. Lists the subject once, then defers to `decide_edf`."""
    base = row.source_subject_dir
    out = subprocess.run([RC, "lsf", base, "--recursive", "--include", "*.edf"],
                         capture_output=True, text=True, timeout=120)
    edfs = [l for l in out.stdout.splitlines() if l.endswith(".edf")]
    return decide_edf(base, row.bids_task, row.eeg_datetime, edfs, lambda rel: _acq_time(base, rel))


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
        # run via the wrapper that disables the nested-tensor fast path (MPS incompat), scoped to this head
        r = subprocess.run(["bash", "-lc",
            f"cd {fi.M2} && PYTHONPATH={shim}:{fi.M2}:${{PYTHONPATH}} KMP_DUPLICATE_LIB_OK=TRUE MORGOTH2_DIR={fi.M2} "
            f"{fi.VENV} {shim}/eeg_level_wrap.py --mode predict "
            f"--task_model checkpoints/{ckpt} --dataset {ds} --test_csv_dir {csvdir} --result_dir {resdir}"],
            capture_output=True, text=True)
        if r.returncode != 0:
            tail = "\n".join([l for l in r.stderr.splitlines() if "libomp" not in l and "warn" not in l.lower()][-6:])
            raise RuntimeError(f"EEG_level_head {ds} failed:\n{tail}")
    ps = f"{sout}/pred_SLOWING"
    _win("SLOWING.pth", "SLOWING", ps)
    # Morgoth's SLOWING window head is 3-class SOFTMAX (CrossEntropyLoss, nb_classes=3), i.e. the classes
    # are MUTUALLY EXCLUSIVE per window:
    #     class_0 = Others (no slowing) | class_1 = Focal Slowing | class_2 = Generalized Slowing
    #     (morgoth2/results_figures.py label_maps, aligned to labels[0]="SLOWING")
    # The recording-level focal/generalized calls come from two SEPARATE BINARY heads
    # (FOC_SLOWING_EEGlevel / GEN_SLOWING_EEGlevel, torch.sigmoid) which are INDEPENDENT — both may fire.
    #
    # HISTORY / WHY ALL THREE ARE KEPT NOW: the first version of this block kept only
    # `p_slowing = 1 - class_0_prob` and discarded class_1_prob / class_2_prob. The CSV lives in a
    # tempfile.mkdtemp() dir that is rmtree'd after every recording, so those two columns were computed and
    # then destroyed on the worker node — they never reached OUTPUT_ROOT and therefore never reached S3.
    # Recovering them costs a full gate re-run. Never collapse the head on the way in again.
    p_slow = [np.nan] * n_seg
    p_foc_seg = [np.nan] * n_seg          # per-SEGMENT P(focal slowing)      <- class_1
    p_gen_seg = [np.nan] * n_seg          # per-SEGMENT P(generalized slowing) <- class_2
    wf = next(Path(ps).glob("*.csv"), None)
    if wf is not None:
        w = pd.read_csv(wf)
        if "class_0_prob" in w.columns:
            pw = (1.0 - w["class_0_prob"]).to_numpy()      # calibrated slowing probability
        elif "pred_class" in w.columns:
            pw = (w["pred_class"].to_numpy() > 0).astype(float)   # fallback: any-slowing class
        else:
            pw = np.array([])
        pf = w["class_1_prob"].to_numpy() if "class_1_prob" in w.columns else np.array([])
        pg = w["class_2_prob"].to_numpy() if "class_2_prob" in w.columns else np.array([])
        step = float(GATE_STEP)
        for i, c in enumerate(centers_s):
            wi = int(c / step)
            if 0 <= wi < len(pw):
                p_slow[i] = float(pw[wi])
            if 0 <= wi < len(pf):
                p_foc_seg[i] = float(pf[wi])
            if 0 <= wi < len(pg):
                p_gen_seg[i] = float(pg[wi])
    # EEG-level focal/gen aggregators (authoritative recording-level focal/gen; broadcast to segments)
    def _eeg_prob(tag):
        f = Path(sout) / f"pred_EEG_level_{tag}.csv"
        if f.exists() and len(d := pd.read_csv(f)):
            return float(d.probability.iloc[0])
        return np.nan
    p_focal = p_gen = np.nan
    try:
        _eeg("FOC_SLOWING_EEGlevel.pth", "FOC_SLOWING", ps, str(sout)); p_focal = _eeg_prob("FOC_SLOWING")
        _eeg("GEN_SLOWING_EEGlevel.pth", "GEN_SLOWING", ps, str(sout)); p_gen = _eeg_prob("GEN_SLOWING")
    except Exception as e:
        print(f"    gate EEG-level focal/gen failed (per-segment p_slowing kept): {e}")
    return p_slow, p_focal, p_gen, p_foc_seg, p_gen_seg


_BANDS6 = ["delta", "theta", "alpha", "beta", "gamma", "total"]


def segment_master_rows(eid, pid, edt, bip, fs, stages, gate=None):
    """Two tables (SAP §5, grain decided 2026-07-11 = per CHANNEL, regions derived downstream):
      channel_rows  — one row per (segment, channel): 18 bipolar channels, per-channel features + vP.
      summary_rows  — one row per segment: stage, artifact, per-segment p_slowing, whole-head vP.
    ALL segments are retained with artifact_flag (flag, not strip). Regions are a downstream groupby
    over `channel` using recording._AGG (whole_head, L/R_temporal, L/R_parasagittal, midline)."""
    segidx = ex.segment_indices(bip.shape[0])            # capped to 24 h
    channel_rows, summary_rows = [], []
    for i, (s, e) in enumerate(segidx):
        seg = bip[s:e]
        ok, reason = af.segment_usable(seg, fs)          # per-segment (whole 18-ch) artifact
        freqs, psd = ex.multitaper_psd(seg.T, fs)        # (18, n_freq)
        stage = stages[i] if i < len(stages) else "Other"
        ctx = {"eeg_id": eid, "segment": i, "t_start_s": float(s / fs), "stage": stage,
               "artifact_flag": (not ok), "artifact_reason": ("none" if ok else reason)}
        # per-segment summary: whole-head/spatial vP + per-segment gate (can't live on one channel)
        summary_rows.append({"patient_id": pid, "eeg_datetime": edt, **ctx,
            "p_slowing": (float(gate[0][i]) if gate and i < len(gate[0]) else np.nan),
            # ALL THREE classes of the SOFTMAX window head, not just 1 - class_0. p_slowing is redundant
            # with these two (p_slowing = p_focal_seg + p_gen_seg up to rounding) but is kept for continuity.
            "p_focal_seg": (float(gate[3][i]) if gate and len(gate) > 3 and i < len(gate[3]) else np.nan),
            "p_gen_seg": (float(gate[4][i]) if gate and len(gate) > 4 and i < len(gate[4]) else np.nan),
            "Q_SLOWING": vp.q_slowing(freqs, psd), "Q_APG": vp.q_apg(freqs, psd),
            "r_sBSI": vp.r_sbsi(freqs, psd), "pdBSI": vp.pdbsi(freqs, psd), "Q_ASYM": vp.q_asym(freqs, psd)})
        bp_all = ex.band_powers(freqs, psd)              # dict band -> (18,) power, all channels at once
        for c, ch in enumerate(CH_NAMES):
            d = _derived(np.array([[float(bp_all[b][c]) for b in _BANDS6]]))
            row = {**ctx, "channel": ch, **{k: float(v[0]) for k, v in d.items()}}
            row.update(DTABR=vp.dtabr(freqs, psd, [c]), ADR=vp.adr(freqs, psd, [c]),
                       SEF95=vp.sef(freqs, psd, 0.95, [c]), median_freq=vp.median_freq(freqs, psd, [c]),
                       peak_freq=vp.peak_freq(freqs, psd, [c]))
            channel_rows.append(row)
    return channel_rows, summary_rows


def fetch_panel(sp, ext, work):
    """Resolve a relative panel source_path against PANEL_ROOT. Local dir -> the file in place;
    s3://... or an rclone remote -> pull to the work dir. Returns a local path or None."""
    if not PANEL_ROOT:                                             # allow bare local paths for old pilots
        return Path(sp) if Path(sp).exists() else None
    full = f"{PANEL_ROOT}/{sp}"
    if PANEL_ROOT.startswith("s3://"):
        dst = work / f"panel{ext}"
        subprocess.run(["aws", "s3", "cp", full, str(dst)], check=True, capture_output=True, timeout=600)
        return dst
    if ":" in PANEL_ROOT.split("/")[0]:                           # rclone remote, e.g. "bdsp:prefix"
        dst = work / f"panel{ext}"
        subprocess.run([RC, "copyto", full, str(dst)], check=True, capture_output=True, timeout=600)
        return dst
    p = Path(full)                                                # local PANEL_ROOT
    return p if p.exists() else None


def process_one(m, work):
    eid = m.eeg_id
    if (DONE / f"{eid}.done").exists():
        return "skip"
    # load branches on source_type: BIDS via S3, OccasionNoise EDF (edf_direct), MoE v7.3 mat (mat_v73)
    stype = str(getattr(m, "source_type", "bids") or "bids")
    if stype in ("edf_direct", "mat_v73"):
        from morgoth_slowing.io import panels
        sp = getattr(m, "source_path", None)
        if not sp:
            return "nopanelfile"
        local = fetch_panel(sp, ".edf" if stype == "edf_direct" else ".mat", work)
        if local is None:
            return "nopanelfile"
        if stype == "edf_direct":
            data, chs, fs, _, _ = panels.read_occasion_edf(str(local))   # OccasionNoise (~50 min)
        else:
            data, chs, fs = panels.read_moe_mat(str(local))              # MoE (one 15-s segment)
        ep = str(sp); resolve_reason = stype
    else:
        ep, resolve_reason = resolve_edf(m)
        if ep is None:
            return f"noedf:{resolve_reason}"                 # noedf / ambiguous:NofM (never guess)
        local = work / "rec.edf"
        subprocess.run([RC, "copyto", ep, str(local)], check=True, capture_output=True, timeout=600)
        data, chs, fs = load_edf_referential(str(local))     # already read-time capped to 24 h (B4)
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
    channel_rows, summary_rows = segment_master_rows(eid, m.patient_id, m.eeg_datetime, bip, fs, stages, gate)
    sm = pd.DataFrame(channel_rows); ss = pd.DataFrame(summary_rows)
    (OUT / f"eeg_id={eid}").mkdir(parents=True, exist_ok=True)
    (SUMM / f"eeg_id={eid}").mkdir(parents=True, exist_ok=True)
    sm.to_parquet(OUT / f"eeg_id={eid}" / "part.parquet", index=False)      # per (segment, channel)
    ss.to_parquet(SUMM / f"eeg_id={eid}" / "part.parquet", index=False)     # per segment
    # integrity hash (B2) of the source we actually analyzed + rich per-EEG stats for the run ledger (B5)
    edf_bytes = int(Path(local).stat().st_size); edf_sha = _sha256(local)
    n_seg = int(len(ss)); n_art = int(ss.artifact_flag.sum())
    stage_frac = {f"frac_{k}": round(v, 4) for k, v in ss.stage.value_counts(normalize=True).items()}
    (DONE / f"{eid}.done").write_text(json.dumps({
        "eeg_id": eid, "patient_id": m.patient_id, "src_type": stype, "source_edf": ep,
        "resolve_reason": resolve_reason, "sha256": edf_sha, "n_bytes": edf_bytes,
        "code_commit": COMMIT, "worker": Path(__file__).name, "n_hours": round(n_hours, 2),
        "recording_seconds": round(n_hours * 3600, 1), "n_segments": n_seg, "n_artifact": n_art,
        "frac_artifact": round(n_art / max(n_seg, 1), 4), "stage_frac": stage_frac,
        "gate": RUN_GATE, "p_slowing_coverage": round(float(ss.p_slowing.notna().mean()), 4),
        "p_focal": (float(gate[1]) if gate else None), "p_generalized": (float(gate[2]) if gate else None),
        "processed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, default=float))
    if stype == "bids":
        local.unlink(missing_ok=True)                       # remove the pulled temp EDF (not panel sources)
    return dict(eeg_id=eid, src_type=stype, n_seg=n_seg, n_art=n_art, hours=round(n_hours, 2), stages=set(stages))


def main(n=10):
    man = pd.read_parquet(MANIFEST)
    # SHARDING for the parallel AWS run: SHARD="i/N" -> worker i of N takes rows where idx % N == i.
    # ALL=1 processes the whole manifest (sharded); else the first `n` (pilot, PILOT_TASK-filtered).
    shard = os.environ.get("SHARD")
    if os.environ.get("PILOT_MIX") == "1":
        # prove all 3 source types: k BDSP (bids) + k OccasionNoise (edf_direct) + k MoE (mat_v73)
        k = n; man["_st"] = man.get("source_type", "bids").fillna("bids")
        bids = man[(man._st == "bids") & (man.bids_task == "rEEG")].head(k)
        occ = man[man.panel_set == "occasionnoise"].head(k)
        moe = man[man.panel_set == "moe"].head(k)
        picks = pd.concat([bids, occ, moe]); print(f"MIXED pilot: {len(bids)} bids + {len(occ)} OccasionNoise + {len(moe)} MoE")
    elif os.environ.get("ALL") == "1" or shard:
        picks = man.reset_index(drop=True)
        if shard:
            i, N = (int(x) for x in shard.split("/"))
            picks = picks[picks.index % N == i]
        print(f"FULL run: {len(picks)} EEGs" + (f" (shard {shard})" if shard else ""))
    else:
        task = os.environ.get("PILOT_TASK", "rEEG")      # routine EEGs = small/fast for the pilot
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
                    if r != "skip":                          # persist non-success outcome for the ledger (B5)
                        (STATUS / f"{m.eeg_id}.status").write_text(json.dumps({"eeg_id": m.eeg_id, "status": r}))
                    print(f"  {r} {m.eeg_id}")
            except Exception as e:
                (STATUS / f"{m.eeg_id}.status").write_text(json.dumps(
                    {"eeg_id": m.eeg_id, "status": f"error:{type(e).__name__}", "detail": str(e)[:200]}))
                print(f"  FAIL {m.eeg_id}: {type(e).__name__}: {e}")
            finally:
                for sub in ("in", "out"):
                    shutil.rmtree(work / sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # NOTE: the worker writes ONLY per-eeg_id outputs (segment_master + segment_summary partitions +
    # per-eeg .done). The one-row-per-EEG run ledger (recording_meta/labels) is built by a SEPARATE,
    # shard-safe pass — scripts/33_assemble_ledger.py — AFTER all shards finish. Do NOT rewrite global
    # parquets here: concurrent shards sharing OUTPUT_ROOT would clobber them (B5).
    print(f"\ndone: {ok}/{len(picks)} processed. Run scripts/33_assemble_ledger.py to build the ledger.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
