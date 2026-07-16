#!/usr/bin/env python3
"""GATE RE-RUN worker — 1 s step, every probability kept raw, Morgoth's zeroing guard DISABLED.

Spec: docs/gate_rerun_spec.md.  THE RULE: persist every raw model output at the finest granularity the model
produces. Never collapse, never threshold, never short-circuit on the way in.

ADDITIVE BY CONSTRUCTION — the existing run is NOT thrown away and NOT touched:
    reads   data/derived/segment_master/_done/<id>.done   (to PIN the exact source EDF + sha256)
            data/derived/segment_summary/eeg_id=<id>/      (to reuse the CANONICAL segment index)
    writes  data/derived/window_gate/eeg_id=<id>/part.parquet     <- NEW
            data/derived/segment_gate/eeg_id=<id>/part.parquet    <- NEW
            data/derived/segment_gate/_done/<id>.done             <- NEW
    never opens segment_master / segment_summary / their sidecars for WRITE.
`segment_gate` is keyed on (eeg_id, segment) using the SAME segment index as segment_master, so old and new
join 1:1 and are used together.

WHAT IT PRODUCES
  window_gate  (one row per 1 s window — the finest thing the model emits)
      t_start_s, p_class0 (Others), p_class1 (Focal), p_class2 (Generalized)   <- the RAW softmax, all three
      p_abnormal                                                               <- NORMAL head, raw sigmoid
      Nothing is derived on the way in. `p_slowing = 1 - p_class0` is a VIEW, computed later.

  segment_gate (one row per EXISTING 15 s segment — joins to segment_master on (eeg_id, segment))
      p_focal_30/60/120, p_gen_30/60/120   INDEPENDENT sigmoids from the two EEG-level heads, run on a
                                           30/60/120 s window CENTRED on that segment. 30 s is the
                                           architectural floor: the head's CNN reduces length 30x
                                           (MaxPool 10 then 3), so <30 rows produces ZERO transformer
                                           tokens and the model cannot run. We never pad with means.
      guard_focal_30/..., guard_gen_30/... Morgoth's short-circuit would have zeroed this (max of that
                                           head's class column < 1/3). WE DO NOT ZERO IT — we run the model
                                           and store the real number, plus this flag, so official behaviour
                                           is reproducible in post-processing and no number is destroyed.
      c0_mean/c1_mean/c2_mean, c0_max/c1_max/c2_max   convenience aggregates of the window softmax over the
                                           segment. Safe, because the RAW per-second values are all kept.

Env: RUN_GATE_DRY=1 synthesises the window probabilities and skips EDF+model entirely — exercises the whole
slicing / alignment / schema / write path with no GPU. Used to prove the format and the join before launch.

Run: PYTHONPATH=src python scripts/32_gate_rerun_worker.py            (SHARD="i/N" to parallelise)
"""
from __future__ import annotations
import gc, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

import numpy as np, pandas as pd

sys.path.insert(0, "src")

OUTROOT = Path(os.environ.get("OUTPUT_ROOT", "data/derived"))
SRC_DONE = OUTROOT / "segment_master" / "_done"          # READ ONLY — pins the source EDF
SRC_SUMM = OUTROOT / "segment_summary"                   # READ ONLY — canonical segment index
WGATE = OUTROOT / "window_gate";  WGATE.mkdir(parents=True, exist_ok=True)
SGATE = OUTROOT / "segment_gate"; SGATE.mkdir(parents=True, exist_ok=True)
GDONE = SGATE / "_done";   GDONE.mkdir(exist_ok=True)
GSTAT = SGATE / "_status"; GSTAT.mkdir(exist_ok=True)

GATE_STEP = 1                       # SECONDS. Matches Morgoth's reference pipeline (pred_SLOWING_1sStep).
# The .done sidecars record EDF paths as "s3:bdsp-opendata-repository/..." -- the rclone remote the ORIGINAL
# run used. But that remote does not exist in the AMI's rclone config ("didn't find section in config file
# (s3)"), so the original fleet must have had rclone configured on the box BY HAND -- the same class of
# undocumented manual step as the missing manifest and the missing git pull. EDF_REMOTE lets us route the
# fetch through a remote that DOES exist (bdsp:), which points at the same S3 with the same credentials.
# The path is otherwise untouched: we still fetch the byte-identical file, and the sha256 is verified.
EDF_REMOTE = os.environ.get("EDF_REMOTE", "s3:")
PANEL_ROOT = os.environ.get("PANEL_ROOT")           # where MoE/ON panel sources live (rclone remote / s3://)


def fetch_panel(sp, ext, work):
    """Resolve a relative panel source_path against PANEL_ROOT (verbatim from scripts/31). Local dir -> in
    place; s3://... via aws; rclone remote via rclone. Returns a local path or None."""
    from morgoth_slowing.fleet import ingest as fi
    if not PANEL_ROOT:
        return Path(sp) if Path(sp).exists() else None
    full = f"{PANEL_ROOT}/{sp}"
    if PANEL_ROOT.startswith("s3://"):
        dst = work / f"panel{ext}"
        subprocess.run(["aws", "s3", "cp", full, str(dst)], check=True, capture_output=True, timeout=600)
        return dst
    if ":" in PANEL_ROOT.split("/")[0]:              # rclone remote, e.g. "bdsp:prefix"
        dst = work / f"panel{ext}"
        r = subprocess.run([fi.RC, "copyto", full, str(dst)], capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"panel fetch failed {full}: {(r.stderr or '').strip().splitlines()[-1:]}")
        return dst
    p = Path(full)
    return p if p.exists() else None
CONTEXTS = [30, 60, 120]            # EEG-level window lengths, in seconds (= rows at 1 s step)
MIN_ROWS = 30                       # the CNN's hard floor: <30 rows -> 0 transformer tokens
SEG_LEN_S = 15.0
DRY = os.environ.get("RUN_GATE_DRY") == "1"
GATE_MAX_HOURS = float(os.environ.get("GATE_MAX_HOURS", "12"))  # cap long recordings (1s-step OOM guard)
SCHEMA_VERSION = "gate-rerun-1"


# --------------------------------------------------------------------------- pure, testable geometry
def context_rows(center_s: float, ctx: int, n_rows: int):
    """Row range for a `ctx`-second window centred on `center_s`. None if the recording is too short.

    Prefers REAL data: if the window runs off an end it is SHIFTED to fit while keeping its full length, so
    the model sees `ctx` rows of genuine signal. Only when the whole recording is shorter does it give up and
    return None -- and then `build_seq` mean-pads, and the row is FLAGGED.
    """
    if n_rows < max(ctx, MIN_ROWS):
        return None
    lo = int(round(center_s - ctx / 2.0))
    lo = max(0, min(lo, n_rows - ctx))          # shift to fit, do not shrink
    return lo, lo + ctx


def build_seq(W, center_s, ctx):
    """-> (sequence, length_to_report, padded_flag).

    When the recording is shorter than the CNN's 30-row floor -- which is EVERY one of the 1,761 MoE clips,
    all exactly 15 s -- we reproduce Morgoth's own CSVDataset behaviour: take the real rows and MEAN-PAD up
    to 30, reporting the PRE-pad length to the model (that is what Morgoth records). The result is flagged
    `padded`, stored ALONGSIDE the raw per-second softmax, never instead of it. So every case gets the same
    columns, and a fabricated input can never be mistaken for a measured one.
    """
    T = len(W)
    r = context_rows(center_s, ctx, T)
    if r is not None:
        lo, hi = r
        return W[lo:hi], ctx, False
    real = W                                    # the whole (short) recording
    need = max(MIN_ROWS, 30)
    pad = np.tile(real.mean(axis=0, keepdims=True), (max(0, need - T), 1))
    return np.vstack([real, pad])[:need].astype(np.float32), T, True


def guard_would_fire(W: np.ndarray, lo: int, hi: int, class_idx: int) -> bool:
    """Morgoth's short-circuit: probability forced to 0, with NO forward pass, when the max of this head's
    class column is below 1/n_classes. We record what it WOULD have done; we never apply it."""
    return bool(W[lo:hi, class_idx].max() < 1.0 / W.shape[1])


# --------------------------------------------------------------------------- the EEG-level heads (SHIM)
class EEGLevelHeads:
    """Drives Morgoth's FOC/GEN EEG-level heads over arbitrary slices, via scripts/shims/eeg_level_sliding.py.

    TWO-VENV RULE (docs/fleet_dependencies.md §4): the worker venv imports NEITHER torch NOR timm — torch
    lives only in Morgoth's venv. So the checkpoints are touched in a SUBPROCESS under PILOT_VENV, exactly
    as the window head and eeg_level_wrap.py already are. (An earlier draft of this file called torch
    directly from the worker; it would have died on the fleet with a bare ImportError.)

    The shim disables Morgoth's low-signal short-circuit, so every slice gets a real forward pass and a real
    sigmoid. Nothing is thresholded, zeroed, or mean-padded.
    """

    def __init__(self, ckpt_dir, scratch):
        from morgoth_slowing.fleet import ingest as fi
        self.ckpt_dir = os.path.abspath(ckpt_dir)
        self.scratch = Path(scratch); self.scratch.mkdir(parents=True, exist_ok=True)
        self.venv = fi.VENV                       # PILOT_VENV = Morgoth's python (the one WITH torch)
        self.shim = os.path.join(os.path.abspath(fi.SHIMS), "eeg_level_sliding.py")
        self.sha = {n: _sha256(Path(self.ckpt_dir) / c)
                    for n, c in [("focal", "FOC_SLOWING_EEGlevel.pth"),
                                 ("gen", "GEN_SLOWING_EEGlevel.pth")]}

    def run_seqs(self, seqs, lens):
        """seqs: list of (L,3) arrays (already mean-padded if short). -> (S,2) raw sigmoids [focal, gen]."""
        if not len(seqs):
            return np.zeros((0, 2), np.float32)
        L = max(len(x) for x in seqs)
        X = np.zeros((len(seqs), L, 3), dtype=np.float32)
        for j, x in enumerate(seqs):
            X[j, :len(x)] = x
        np.save(self.scratch / "X.npy", X)
        np.save(self.scratch / "lens.npy", np.asarray(lens, dtype=np.int64))
        r = subprocess.run(["bash", "-lc",
            f"KMP_DUPLICATE_LIB_OK=TRUE MORGOTH2_DIR={os.environ.get('MORGOTH2_DIR','')} "
            f"{self.venv} {self.shim} --scratch {self.scratch} --ckpt-dir {self.ckpt_dir}"],
            capture_output=True, text=True)
        if r.returncode != 0:
            tail = "\n".join(r.stderr.strip().splitlines()[-5:])
            raise RuntimeError(f"eeg_level_sliding failed:\n{tail}")
        return np.load(self.scratch / "probs.npy")


def _sha256(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while (b := f.read(buf)):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------- window head (Morgoth CLI)
def run_window_heads(sin, sout, eid):
    """SLOWING (3-class) + NORMAL (binary) window heads at 1 s step. Returns (W[T,3], p_abnormal[T])."""
    from morgoth_slowing.fleet import ingest as fi
    shim = os.path.abspath(fi.SHIMS)

    def _win(ckpt, ds, outdir):
        _r = subprocess.run(["bash", "-lc",
            f"cd {fi.M2} && PYTHONPATH={shim}:${{PYTHONPATH}} PYTORCH_ENABLE_MPS_FALLBACK=1 "
            f"KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 "
            f"{fi.VENV} finetune_classification.py --abs_pos_emb --model base_patch200_200 --predict "
            f"--task_model checkpoints/{ckpt} --dataset {ds} --data_format mat --sampling_rate 0 "
            f"--already_format_channel_order no --already_average_montage no --allow_missing_channels yes "
            f"--max_length_hour no --eval_sub_dir {sin} --eval_results_dir {outdir} "
            f"--prediction_slipping_step_second {GATE_STEP} --polarity 1 --rewrite_results no "
            f"--num_workers 0 --device {fi.DEVICE}"], capture_output=True, text=True)
        if _r.returncode != 0:
            tail = "\n".join((_r.stderr or _r.stdout or "").strip().splitlines()[-6:])
            raise RuntimeError(f"window head {ds} rc={_r.returncode} venv={fi.VENV} m2={fi.M2}:\n{tail}")

    ps = f"{sout}/pred_SLOWING_1sStep"
    _win("SLOWING.pth", "SLOWING", ps)
    f = next(Path(ps).glob("*.csv"), None)
    if f is None:
        raise RuntimeError("SLOWING window head produced no CSV")
    w = pd.read_csv(f)
    need = ["class_0_prob", "class_1_prob", "class_2_prob"]
    miss = [c for c in need if c not in w.columns]
    if miss:
        raise RuntimeError(f"SLOWING CSV missing {miss} — the 3-class softmax is what this run exists for")
    W = w[need].to_numpy(np.float32)

    pn = f"{sout}/pred_NORMAL_1sStep"
    pabn = np.full(len(W), np.nan, dtype=np.float32)
    try:
        _win("NORMAL.pth", "NORMAL", pn)
        fn = next(Path(pn).glob("*.csv"), None)
        if fn is not None:
            n = pd.read_csv(fn)
            col = "class_0_prob" if "class_0_prob" in n.columns else n.columns[0]
            v = n[col].to_numpy(np.float32)[:len(W)]
            pabn[:len(v)] = v
    except Exception as e:
        print(f"    NORMAL head failed (SLOWING kept): {type(e).__name__}: {e}", flush=True)
    return W, pabn


# --------------------------------------------------------------------------- one recording
def process_one(eid, meta, heads, work):
    seg = pd.read_parquet(SRC_SUMM / f"eeg_id={eid}" / "part.parquet",
                          columns=["segment", "t_start_s"]).sort_values("segment")
    if seg.empty:
        return "noseg"

    if DRY:
        # synthesise a plausible window softmax; exercises slicing/alignment/schema with no GPU
        T = int(np.ceil(float(seg.t_start_s.max()) + SEG_LEN_S))
        rng = np.random.default_rng(abs(hash(eid)) % (2**32))
        L = rng.normal(0, 1, size=(T, 3)).astype(np.float32); L[:, 0] += 1.2
        W = np.exp(L); W /= W.sum(1, keepdims=True)
        pabn = rng.random(T).astype(np.float32)
        src_sha = meta.get("sha256")
    else:
        from morgoth_slowing.fleet import ingest as fi
        from morgoth_slowing.io import edf as _edf                       # noqa: F401
        from morgoth_slowing.features import extract as ex
        from scipy.io import savemat
        from morgoth_slowing.io.edf import load_edf_referential

        ep = meta["source_edf"]                       # PINNED. No re-resolution: the file that was used.
        stype = str(meta.get("src_type", "bids") or "bids")
        if stype in ("edf_direct", "mat_v73"):
            # PANEL case (OccasionNoise .edf / MoE .mat). source_edf is a path RELATIVE to PANEL_ROOT, not
            # an s3: object -- the same branch scripts/31 uses. Without this, panels fail "directory not
            # found" (rclone reads the relative path as a local file). MBW wants ALL cases, panels included.
            from morgoth_slowing.io import panels
            local = fetch_panel(ep, ".edf" if stype == "edf_direct" else ".mat", work)
            if local is None:
                return "nopanelfile"
            src_sha = _sha256(local)
            if stype == "edf_direct":
                data, chs, fs, _, _ = panels.read_occasion_edf(str(local))
            else:
                data, chs, fs = panels.read_moe_mat(str(local))
        else:
            if EDF_REMOTE != "s3:" and ep.startswith("s3:"):
                ep = EDF_REMOTE + ep[len("s3:"):]     # same object, a remote name the box actually has
            local = work / "rec.edf"
            # SURFACE RCLONE'S STDERR. The original worker used check=True + capture_output=True, so a failed
            # fetch raised a bare CalledProcessError with the error DISCARDED — undiagnosable on the fleet.
            r = subprocess.run([fi.RC, "copyto", ep, str(local)], capture_output=True, text=True, timeout=900)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or "").strip().splitlines()
                raise RuntimeError("rclone fetch failed for " + ep + " :: " +
                                   " | ".join(err[-3:] if err else ["(no stderr)"]))
            got = _sha256(local)
            if meta.get("sha256") and got != meta["sha256"]:
                return f"sha_mismatch:{got[:12]}!={meta['sha256'][:12]}"
            src_sha = got
            data, chs, fs = load_edf_referential(str(local))
        data = ex.cap_to_hours(data.astype(np.float32, copy=False), fs)
        _cap = int(GATE_MAX_HOURS * 3600 * fs)      # gate-specific cap: the 1s window head OOMs on 24h
        if data.shape[0] > _cap:
            data = data[:_cap]
        sin, sout = work / "in", work / "out"
        for d in (sin, sout):
            shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        savemat(str(sin / f"{eid}.mat"), {"Fs": float(fs), "channels": np.array(chs),
                "data": np.ascontiguousarray(data.T)}, do_compression=True)
        del data; gc.collect()
        W, pabn = run_window_heads(sin, sout, eid)

    T = len(W)

    # ---- window_gate: the RAW per-second softmax. Nothing derived.
    wg = pd.DataFrame({"t_start_s": np.arange(T, dtype=np.float32),
                       "p_class0": W[:, 0], "p_class1": W[:, 1], "p_class2": W[:, 2],
                       "p_abnormal": pabn[:T]})
    (WGATE / f"eeg_id={eid}").mkdir(parents=True, exist_ok=True)
    wg.to_parquet(WGATE / f"eeg_id={eid}" / "part.parquet", index=False)

    # ---- segment_gate: EEG-level heads on a window CENTRED on each EXISTING segment
    centers = seg.t_start_s.to_numpy(np.float64) + SEG_LEN_S / 2.0
    rows = {"segment": seg.segment.to_numpy(), "t_start_s": seg.t_start_s.to_numpy(np.float32)}

    # convenience aggregates of the window softmax over each segment (raw is preserved above)
    for k, cls in enumerate(["c0", "c1", "c2"]):
        mean_v = np.full(len(seg), np.nan, np.float32); max_v = np.full(len(seg), np.nan, np.float32)
        for i, ts in enumerate(seg.t_start_s.to_numpy()):
            a, b = int(ts), min(int(ts + SEG_LEN_S), T)
            if b > a:
                mean_v[i] = W[a:b, k].mean(); max_v[i] = W[a:b, k].max()
        rows[f"{cls}_mean"], rows[f"{cls}_max"] = mean_v, max_v

    for ctx in CONTEXTS:
        seqs, lens, padded, idx = [], [], [], []
        gf = np.zeros(len(seg), bool); gg = np.zeros(len(seg), bool)
        for i, c in enumerate(centers):
            sq, ln, pd_ = build_seq(W, c, ctx)      # ALWAYS produces a sequence; pd_ says if it was padded
            seqs.append(sq); lens.append(ln); padded.append(pd_); idx.append(i)
            lo, hi = (0, T) if pd_ else context_rows(c, ctx, T)
            gf[i] = guard_would_fire(W, lo, hi, 1)
            gg[i] = guard_would_fire(W, lo, hi, 2)
        pf = np.full(len(seg), np.nan, np.float32); pg = np.full(len(seg), np.nan, np.float32)
        if seqs:
            if DRY:
                rng = np.random.default_rng(ctx)
                vf, vg = rng.random(len(seqs)).astype(np.float32), rng.random(len(seqs)).astype(np.float32)
            else:
                pr = heads.run_seqs(seqs, lens); vf, vg = pr[:, 0], pr[:, 1]
            pf[idx], pg[idx] = vf, vg
        rows[f"p_focal_{ctx}"], rows[f"p_gen_{ctx}"] = pf, pg
        rows[f"guard_focal_{ctx}"], rows[f"guard_gen_{ctx}"] = gf, gg
        rows[f"padded_{ctx}"] = np.asarray(padded, bool)   # True = input was mean-padded (Morgoth-style)

    sg = pd.DataFrame(rows)
    (SGATE / f"eeg_id={eid}").mkdir(parents=True, exist_ok=True)
    sg.to_parquet(SGATE / f"eeg_id={eid}" / "part.parquet", index=False)

    # ---- recording level, on the FULL 1 s sequence (this is what the 5 s run got wrong)
    rec_padded = T < MIN_ROWS
    if DRY:
        rf = rg = float(np.random.default_rng(7).random())
    else:
        if rec_padded:                            # e.g. every MoE clip: 15 real rows, mean-padded to 30
            pad = np.tile(W.mean(axis=0, keepdims=True), (MIN_ROWS - T, 1))
            sq = np.vstack([W, pad]).astype(np.float32)
            pr = heads.run_seqs([sq], [T])
        else:
            pr = heads.run_seqs([W], [T])
        rf, rg = float(pr[0, 0]), float(pr[0, 1])
    grec_f, grec_g = guard_would_fire(W, 0, T, 1), guard_would_fire(W, 0, T, 2)

    (GDONE / f"{eid}.done").write_text(json.dumps({
        "eeg_id": eid, "schema_version": SCHEMA_VERSION,
        "gate_step_s": GATE_STEP, "contexts_s": CONTEXTS, "guard_disabled": True,
        "n_windows": int(T), "n_segments": int(len(seg)),
        "p_focal_recording": rf, "p_generalized_recording": rg,
        "guard_would_fire_focal_recording": bool(grec_f),
        "guard_would_fire_gen_recording": bool(grec_g),
        "recording_padded": bool(rec_padded),   # True = shorter than the 30-row CNN floor (all MoE clips)
        "source_edf": meta.get("source_edf"), "sha256": src_sha,
        "checkpoint_sha256": (heads.sha if heads else {}),
        "instance_type": os.environ.get("INSTANCE_TYPE"), "n_gpus": os.environ.get("N_GPUS"),
        "morgoth2_commit": os.environ.get("MORGOTH2_COMMIT"),
        "code_commit": os.environ.get("CODE_COMMIT"), "dry_run": DRY,
    }))
    return {"eeg_id": eid, "T": int(T), "n_seg": int(len(seg))}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    dones = sorted(SRC_DONE.glob("*.done"))
    ids = []
    for f in dones:
        eid = f.stem
        if (GDONE / f"{eid}.done").exists():
            continue
        if not (SRC_SUMM / f"eeg_id={eid}" / "part.parquet").exists():
            continue
        ids.append(eid)
    # ID_LIST pins an explicit set (used by the 100-EEG acceptance test to sample REPRESENTATIVE
    # recordings rather than whatever sorts first — the first 100 by name are all 15 s MoE clips).
    il = os.environ.get("ID_LIST")
    if il:
        want = [x.strip() for x in Path(il).read_text().split() if x.strip()]
        ids = [e for e in want if e in set(ids)]

    sh = os.environ.get("SHARD")
    if sh:
        i, N = (int(x) for x in sh.split("/"))
        ids = [e for k, e in enumerate(ids) if k % N == i]
    if n:
        ids = ids[:n]
    print(f"gate re-run: {len(ids):,} recordings | step {GATE_STEP}s | contexts {CONTEXTS} | "
          f"guard DISABLED | dry={DRY}", flush=True)

    heads = None if DRY else EEGLevelHeads(
        os.environ.get("CKPT_DIR", os.path.join(os.environ.get("MORGOTH2_DIR", "../morgoth2"),
                                                "checkpoints")),
        scratch=Path(tempfile.mkdtemp(prefix="eeglvl_")))
    work = Path(tempfile.mkdtemp()); ok = 0
    try:
        for k, eid in enumerate(ids):
            meta = json.loads((SRC_DONE / f"{eid}.done").read_text())
            try:
                r = process_one(eid, meta, heads, work)
                if isinstance(r, dict):
                    ok += 1
                    if (k + 1) % 25 == 0 or k < 3:
                        print(f"  [{k+1}/{len(ids)}] {eid}: {r['T']:,} windows, {r['n_seg']:,} segments",
                              flush=True)
                else:
                    (GSTAT / f"{eid}.status").write_text(json.dumps({"eeg_id": eid, "status": r}))
                    print(f"  {r} {eid}", flush=True)
            except Exception as e:
                (GSTAT / f"{eid}.status").write_text(json.dumps(
                    {"eeg_id": eid, "status": f"error:{type(e).__name__}", "detail": str(e)[:300]}))
                print(f"  FAIL {eid}: {type(e).__name__}: {e}", flush=True)
            finally:
                for sub in ("in", "out"):
                    shutil.rmtree(work / sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\ndone: {ok}/{len(ids)}")


if __name__ == "__main__":
    main()
