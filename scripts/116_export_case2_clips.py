"""Export EEG clips for the generalized case-2 review (scripts/115) into the viewer.

These are recordings where Morgoth + the report say generalized slowing but our field measured nothing.
MBW reviews them by eye to decide: rhythmic morphology (GRDA/FIRDA) vs age-norm over-correction vs a genuine
model miss vs a gate false-positive. Unlike the V3 clips (centred on max relative-delta), these have NO
band-power excess by definition, so we export a LONGER clean stretch (5 min) from a low-artifact region so
intermittent rhythmic slowing is scrollable.

Reuses scripts/98's find_edf / build_bipolar. PHI-free: int16 uV, no EDF header, opaque case_id only.
Crosswalk (case_id -> bdsp_id) is read from the scratchpad, never written to the repo.

Run: RCLONE_BIN=/opt/homebrew/bin/rclone PYTHONPATH=src python scripts/116_export_case2_clips.py
"""
from __future__ import annotations
import json, subprocess, tempfile, time, importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location("m98", "scripts/98_build_review_set.py")
m98 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m98)

SC = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
          "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
CROSSWALK = SC / "case2_crosswalk.jsonl"
OUT = Path("viewer/data/signals_case2")
CLIP_SEC = 300.0            # 5 min, scrollable
prog = Path("results/case2_clip_progress.txt")


def pick_clean_clip(seg, fs):
    """Longest low-artifact window of CLIP_SEC; fall back to the recording middle."""
    N = seg.shape[1]; W = int(20 * fs)
    nwin = max(1, N // W)
    clean = np.ones(nwin, bool)
    for k in range(nwin):
        s = seg[:, k * W:(k + 1) * W]
        if s.shape[1] < W // 2 or np.max(np.abs(s)) > 500 or np.median(np.std(s, 1)) < 0.5:
            clean[k] = False
    need = int(CLIP_SEC / 20)
    best_start, best_len, cur = 0, 0, 0
    for k in range(nwin):
        cur = cur + 1 if clean[k] else 0
        if cur > best_len:
            best_len, best_start = cur, k - cur + 1
    if best_len >= need:
        t0 = best_start * 20.0
    else:
        t0 = max(0.0, (N / fs - CLIP_SEC) / 2)      # middle
    i0 = int(t0 * fs); i1 = int(min(N, i0 + CLIP_SEC * fs))
    return seg[:, i0:i1], float(t0)


def main():
    rows = [json.loads(l) for l in open(CROSSWALK)]
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [r for r in rows if not (OUT / f"{r['case_id']}.npz").exists()]
    print(f"{len(todo)} of {len(rows)} case-2 clips to export")
    work = Path(tempfile.mkdtemp()); ok = 0; t0all = time.time()
    for i, r in enumerate(todo, 1):
        cid, bid = r["case_id"], r["bdsp_id"]; site = bid[:5]
        prog.write_text(f"case-2 clips: {ok} exported / {i-1} attempted / {len(rows)} target | "
                        f"{(time.time()-t0all)/60:.1f} min | {time.strftime('%H:%M:%S')}\n")
        try:
            ep = m98.find_edf(site, bid)
            if not ep:
                print(f"  ! {cid}: no EDF"); continue
            local = work / f"{cid}.edf"
            subprocess.run([m98.RC, "copyto", ep, str(local)], check=True, capture_output=True, timeout=240)
            seg, fs = m98.build_bipolar(str(local))
            clip, t0 = pick_clean_clip(seg, fs)
            clip16 = np.clip(np.round(clip), -32768, 32767).astype(np.int16)
            np.savez_compressed(OUT / f"{cid}.npz", data=clip16, fs=np.float32(fs), t0=np.float32(t0))
            local.unlink(missing_ok=True); ok += 1
            print(f"  {i}/{len(todo)} {cid}: {clip.shape[1]/fs:.0f}s (t0={t0:.0f}s)", flush=True)
        except Exception as e:
            print(f"  ! {cid}: {type(e).__name__}", flush=True); continue
    prog.write_text(f"case-2 clips: {ok} exported / {len(rows)} target  [DONE] {time.strftime('%H:%M:%S')}\n")
    print(f"done: {ok} clips -> {OUT}")


if __name__ == "__main__":
    main()
