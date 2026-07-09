"""Build the V3 blinded-review set: a stratified 100-case sample of auto-generated
slowing descriptions + pre-exported EEG clips for the offline viewer (viewer/app.py).

Two stages (both idempotent / resumable):

  SELECT  Assemble 100 cases stratified as focal / generalized / normal-control, spanning
          a range of deviation magnitudes (peak_z), from cleanly-paired recordings that
          carry one of our generated sentences.  Assign opaque case_ids (case_001..case_100)
          in randomized order.  Writes:
            - data/derived/review_set.jsonl        (COMMITTED, PHI-free: case_id, sentence,
                                                     stratum, deviation_z, gated_in)
            - <scratchpad>/case_crosswalk.jsonl     (PRIVATE, NOT committed: case_id -> bdsp_id,
                                                     site, edf S3 path, sentence, stratum)

  FETCH   For up to --limit cases without a signal yet, rclone the BIDS EDF, build the 18ch
          longitudinal-bipolar (double-banana) montage, pick a ~4 min clip centred on the
          most-deviant (highest whole-head relative-delta) 20 s window, decimate to 200 Hz,
          and store as viewer/data/signals/<case_id>.npz  (int16 uV, NO PHI, NO EDF header).
          The raw EDF is deleted immediately after extraction.

PHI: nothing written under data/ or viewer/ carries a patient id, a date, an EDF header, or
raw report text.  The only case_id -> bdsp_id link lives in the scratchpad crosswalk.

Usage:
  python scripts/98_build_review_set.py --select            # (re)build the case lists only
  python scripts/98_build_review_set.py --fetch --limit 8   # export 8 clips (resumable)
  python scripts/98_build_review_set.py --select --fetch --limit 100   # everything

Env overrides: RCLONE_BIN, RCLONE_REMOTE (default s3:), BDSP_EEG_REPO, REVIEW_SCRATCH.
"""
from __future__ import annotations
import os, re, sys, json, glob, time, argparse, tempfile, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

DER = Path("data/derived")
VIEWER_SIG = Path("viewer/data/signals")
RC = os.environ.get("RCLONE_BIN", "rclone")
REMOTE = os.environ.get("RCLONE_REMOTE", "s3:")
REPO = os.environ.get("BDSP_EEG_REPO", "bdsp-opendata-repository/EEG")
SCRATCH = Path(os.environ.get(
    "REVIEW_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad"))
CROSSWALK = SCRATCH / "case_crosswalk.jsonl"

SEED = 98
TARGET_FS = 200.0
CLIP_SEC = 240.0          # ~4 min clip stored per case
N_FOCAL, N_GEN, N_NORMAL = 35, 30, 35

# grond / render_eeg montage constants (double-banana longitudinal bipolar)
BIPOLAR = ['Fp1-F7', 'F7-T3', 'T3-T5', 'T5-O1', 'Fp2-F8', 'F8-T4', 'T4-T6', 'T6-O2',
           'Fp1-F3', 'F3-C3', 'C3-P3', 'P3-O1', 'Fp2-F4', 'F4-C4', 'C4-P4', 'P4-O2',
           'Fz-Cz', 'Cz-Pz']
MONO = ['FP1', 'F3', 'C3', 'P3', 'F7', 'T3', 'T5', 'O1', 'FZ', 'CZ', 'PZ',
        'FP2', 'F4', 'C4', 'P4', 'F8', 'T4', 'T6', 'O2']


def _norm(ch: str) -> str:
    u = ch.upper().replace("EEG", "").replace("POL", "").split("-")[0].strip()
    return re.sub(r"[^A-Z0-9]", "", u)


# ----------------------------------------------------------------------------- SELECT
def _bin_sample(df: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Sample n rows spread across quintiles of peak_z (a range of deviation magnitudes)."""
    d = df[df.peak_z.notna()].copy()
    if len(d) <= n:
        return d
    d["_bin"] = pd.qcut(d.peak_z, q=min(5, len(d)), labels=False, duplicates="drop")
    per = max(1, n // (d["_bin"].nunique()))
    picks = []
    for _, g in d.groupby("_bin"):
        picks.append(g.sample(min(per, len(g)), random_state=int(rng.integers(1 << 30))))
    out = pd.concat(picks)
    if len(out) < n:                      # top up from the remainder
        rest = d.drop(out.index)
        out = pd.concat([out, rest.sample(min(n - len(out), len(rest)),
                                          random_state=int(rng.integers(1 << 30)))])
    return out.drop(columns="_bin").head(n)


def select() -> pd.DataFrame:
    lab = pd.read_parquet(DER / "labels_unified.parquet")
    pair = pd.read_parquet(DER / "report_pairing.parquet")[["bdsp_id", "clean_pair"]]
    fr = pd.read_parquet(DER / "final_report.parquet")[["bdsp_id", "report", "gated_in"]]
    sc = pd.read_parquet(DER / "scores_v2.parquet")[["bdsp_id", "peak_z"]]
    df = (lab.merge(pair, on="bdsp_id", how="left")
             .merge(fr, on="bdsp_id", how="left")
             .merge(sc, on="bdsp_id", how="left"))
    df = df[(df.clean_pair == True) & df.report.notna()]        # noqa: E712

    rng = np.random.default_rng(SEED)
    focal = _bin_sample(df[(df.has_focal_slow == 1) & (df.gated_in == True)], N_FOCAL, rng)   # noqa: E712
    gen = _bin_sample(df[(df.has_gen_slow == 1) & (df.gated_in == True)], N_GEN, rng)         # noqa: E712
    norm = df[(df.clean_normal == 1) & (df.gated_in == False)].sample(                        # noqa: E712
        N_NORMAL, random_state=SEED)
    focal["stratum"], gen["stratum"], norm["stratum"] = "focal", "generalized", "normal_control"

    sel = pd.concat([focal, gen, norm])[["bdsp_id", "stratum", "peak_z", "report"]]
    sel = sel.sample(frac=1.0, random_state=SEED).reset_index(drop=True)   # randomize order
    sel["case_id"] = [f"case_{i:03d}" for i in range(1, len(sel) + 1)]
    sel["site"] = sel.bdsp_id.str.slice(0, 5)
    return sel


def write_lists(sel: pd.DataFrame):
    DER.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # committed, PHI-free
    with open(DER / "review_set.jsonl", "w") as fh:
        for _, r in sel.iterrows():
            fh.write(json.dumps({
                "case_id": r.case_id,
                "generated_sentence": r.report,
                "stratum": r.stratum,
                "deviation_z": None if pd.isna(r.peak_z) else round(float(r.peak_z), 2),
                "gated_in": r.stratum != "normal_control",
            }) + "\n")
    # private crosswalk (scratchpad only)
    with open(CROSSWALK, "w") as fh:
        for _, r in sel.iterrows():
            fh.write(json.dumps({
                "case_id": r.case_id, "bdsp_id": r.bdsp_id, "site": r.site,
                "stratum": r.stratum, "generated_sentence": r.report,
            }) + "\n")
    print(f"[select] {len(sel)} cases -> {DER/'review_set.jsonl'} (PHI-free)")
    print(f"[select] crosswalk -> {CROSSWALK} (PRIVATE, not committed)")
    print("[select] strata:", sel.stratum.value_counts().to_dict())


# ----------------------------------------------------------------------------- FETCH
def find_edf(site: str, bdsp_id: str) -> str | None:
    base = f"{REMOTE}{REPO}/bids/{site}/sub-{bdsp_id}/"
    out = subprocess.run([RC, "lsf", "-R", "--include", "*.edf", base],
                         capture_output=True, text=True)
    edfs = [l for l in out.stdout.splitlines() if l.endswith(".edf")]
    return base + edfs[0] if edfs else None


def build_bipolar(edf_local: str):
    import mne
    from scipy.signal import resample_poly
    raw = mne.io.read_raw_edf(edf_local, preload=True, verbose="ERROR")
    raw.rename_channels({c: _norm(c) for c in raw.ch_names})
    fs = float(raw.info["sfreq"])
    idx = {c: i for i, c in enumerate(raw.ch_names)}
    data = raw.get_data(units="uV")
    mono = {n: (data[idx[n]] if n in idx else np.zeros(data.shape[1])) for n in MONO}
    seg = np.zeros((18, data.shape[1]))
    for r, bc in enumerate(BIPOLAR):
        a, b = bc.upper().split('-')
        seg[r] = mono[a] - mono[b]
    if abs(fs - TARGET_FS) > 1e-6:
        from math import gcd
        up, down = int(TARGET_FS), int(round(fs))
        g = gcd(up, down)
        seg = resample_poly(seg, up // g, down // g, axis=1)
        fs = TARGET_FS
    return seg, fs


def pick_clip(seg: np.ndarray, fs: float):
    """Centre a CLIP_SEC clip on the 20 s window of maximal whole-head relative delta
    (0.5-4 Hz / 1-25 Hz), excluding windows with gross (>500 uV) artifact."""
    from scipy.signal import welch
    N = seg.shape[1]
    W = int(20 * fs)
    nwin = max(1, N // W)
    scores = np.full(nwin, -1.0)
    for k in range(nwin):
        s = seg[:, k * W:(k + 1) * W]
        if s.shape[1] < W // 2 or np.max(np.abs(s)) > 500:
            continue
        f, P = welch(s, fs, nperseg=int(2 * fs), axis=1)
        dpow = P[:, (f >= 1) & (f < 4)].sum(1)
        tot = P[:, (f >= 1) & (f < 25)].sum(1) + 1e-9
        scores[k] = float(np.mean(dpow / tot))
    best = int(np.argmax(scores)) if np.any(scores >= 0) else nwin // 2
    center = (best + 0.5) * 20.0
    t0 = min(max(0.0, center - CLIP_SEC / 2), max(0.0, N / fs - CLIP_SEC))
    i0, i1 = int(t0 * fs), int(min(N, (t0 + CLIP_SEC) * fs))
    return seg[:, i0:i1], float(t0)


def fetch(limit: int):
    if not CROSSWALK.exists():
        sys.exit("no crosswalk; run with --select first")
    rows = [json.loads(l) for l in open(CROSSWALK)]
    VIEWER_SIG.mkdir(parents=True, exist_ok=True)
    todo = [r for r in rows if not (VIEWER_SIG / f"{r['case_id']}.npz").exists()][:limit]
    print(f"[fetch] {len(todo)} of {len(rows)} cases need a signal (limit {limit})")
    work = Path(tempfile.mkdtemp())
    ok = 0
    for i, r in enumerate(todo, 1):
        cid, bid, site = r["case_id"], r["bdsp_id"], r["site"]
        t = time.time()
        try:
            ep = find_edf(site, bid)
            if not ep:
                print(f"  ! {cid}: no EDF on S3"); continue
            local = work / f"{cid}.edf"
            subprocess.run([RC, "copyto", ep, str(local)], check=True, capture_output=True)
            seg, fs = build_bipolar(str(local))
            clip, t0 = pick_clip(seg, fs)
            clip16 = np.clip(np.round(clip), -32768, 32767).astype(np.int16)
            np.savez_compressed(VIEWER_SIG / f"{cid}.npz",
                                data=clip16, fs=np.float32(fs), t0=np.float32(t0))
            local.unlink(missing_ok=True)
            ok += 1
            print(f"  {i}/{len(todo)} {cid}: {clip.shape[1]/fs:.0f}s @200Hz "
                  f"(t0={t0:.0f}s, {time.time()-t:.0f}s)")
        except subprocess.CalledProcessError as e:
            print(f"  ! {cid}: rclone failed ({e.returncode})")
        except Exception as e:                                     # noqa: BLE001
            print(f"  ! {cid}: {type(e).__name__}: {e}")
    print(f"[fetch] wrote {ok} signals -> {VIEWER_SIG}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", action="store_true", help="(re)build case lists")
    ap.add_argument("--fetch", action="store_true", help="export EEG clips (resumable)")
    ap.add_argument("--limit", type=int, default=8, help="max clips to fetch this run")
    a = ap.parse_args()
    if not (a.select or a.fetch):
        ap.error("pass --select and/or --fetch")
    if a.select:
        write_lists(select())
    if a.fetch:
        fetch(a.limit)


if __name__ == "__main__":
    main()
