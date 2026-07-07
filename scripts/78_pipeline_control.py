"""(B) PIPELINE CONTROL — is the cohort-vs-overnight difference the PIPELINE (JJ .mat vs extract.py) or
population/state? Take routine cohort recordings, pull their RAW rEEG EDFs, and recompute features with
extract.py (the SAME pipeline used for the overnight expansion). Compare, per recording, to the JJ .mat
features for the same recording.

- If extract.py reproduces the .mat (esp. rel_delta), the pipeline is consistent -> the overnight
  difference is population/state, not computation.
- rel_alpha is the key test of the alpha-band-mismatch hypothesis: if extract.py on ALERT routine EEG
  still yields high alpha (~.mat), then the overnight low-alpha is drowsiness/population, not a band bug.

Run: PYTHONPATH=src python scripts/78_pipeline_control.py [n]
"""
from __future__ import annotations
import sys, subprocess, tempfile, glob
from pathlib import Path
import numpy as np, pandas as pd
from scipy.io import loadmat

if not hasattr(np, 'trapz'): np.trapz = np.trapezoid   # numpy>=2 compat for extract.py
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.features import extract as ex, artifact as af

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
BIDS = "s3:bdsp-opendata-repository/EEG/bids/S0001"
MATDIR = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/mat_normal"
CENTRAL_IDX = [9, 10, 13, 14]                 # F3-C3,C3-P3,F4-C4,C4-P4 in the 18-channel order
FIDX = {"rel_delta": 6, "rel_alpha": 8, "DAR": 12, "TAR": 16}


def mat_central(bdsp_id):
    """JJ .mat central-channel medians over ALL segments (matches all-segment extract.py below)."""
    fs = glob.glob(f"{MATDIR}/sub-{bdsp_id}.mat") or glob.glob(f"{MATDIR}/*{bdsp_id}*.mat")
    if not fs: return None
    m = loadmat(fs[0], squeeze_me=True, struct_as_record=False)
    arr = np.stack([np.asarray(r) for r in m["res"][:, 3]])          # (n_seg, 18, 31)
    out = {}
    for name, fi in FIDX.items():
        out[name] = float(np.nanmedian(arr[:, CENTRAL_IDX, fi]))     # median over seg x central chans
    return out


def edf_central(edf_local):
    data, chs, fs = load_edf_referential(edf_local)
    data = data.astype(np.float32, copy=False)
    bip = ex.to_bipolar(ex.preprocess(data, fs), chs)                # (n_samp, 18)
    segidx = ex.segment_indices(bip.shape[0])
    mask, _ = af.usable_mask(bip, segidx, fs)
    feats = []
    for i, (s, e) in enumerate(segidx):
        if not mask[i]: continue
        fr, psd = ex.multitaper_psd(bip[s:e].T, fs)
        feats.append(ex.features_31(ex.band_powers(fr, psd)))        # (18, 31)
    if not feats: return None
    arr = np.stack(feats)                                            # (n_seg, 18, 31)
    return {name: float(np.nanmedian(arr[:, CENTRAL_IDX, fi])) for name, fi in FIDX.items()}, int(mask.sum())


def find_reeg(bdsp_id):
    # routine EEG is consistently ses-1/eeg/..._task-rEEG_eeg.edf — try it directly (fast), no recurse
    direct = f"{BIDS}/sub-{bdsp_id}/ses-1/eeg/sub-{bdsp_id}_ses-1_task-rEEG_eeg.edf"
    if subprocess.run(["rclone", "lsf", direct], capture_output=True, text=True).stdout.strip():
        return direct
    # fallback: shallow scan of ses-1 eeg dir only
    r = subprocess.run(["rclone", "lsf", f"{BIDS}/sub-{bdsp_id}/ses-1/eeg/"], capture_output=True, text=True)
    edfs = [l for l in r.stdout.splitlines() if l.endswith(".edf") and "rEEG" in l]
    return f"{BIDS}/sub-{bdsp_id}/ses-1/eeg/{edfs[0]}" if edfs else None


def main():
    import re
    lu = pd.read_parquet("data/derived/labels_unified.parquet")
    clean = set(lu[lu.clean_normal == True].bdsp_id)
    # iterate the .mat files: filename encodes the exact source recording (sub-{id}_ses-{N}_{date}.mat),
    # so we pull THAT session's rEEG -> guaranteed same recording as the JJ features.
    mats = sorted(glob.glob(f"{MATDIR}/sub-*_ses-*.mat"))
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for mp in mats:
            if len(rows) >= N: break
            mm = re.match(r"sub-(.+?)_ses-(\d+)_", Path(mp).name)
            if not mm: continue
            bdsp_id, ses = mm.group(1), mm.group(2)
            if bdsp_id not in clean or not bdsp_id.startswith("S0001"): continue
            ep = f"{BIDS}/sub-{bdsp_id}/ses-{ses}/eeg/sub-{bdsp_id}_ses-{ses}_task-rEEG_eeg.edf"
            if not subprocess.run(["rclone", "lsf", ep], capture_output=True, text=True).stdout.strip():
                continue
            mv = mat_central(bdsp_id)
            if not mv: continue
            local = f"{td}/{bdsp_id}.edf"
            if subprocess.run(["rclone", "copyto", ep, local], capture_output=True).returncode: continue
            try:
                ev, nseg = edf_central(local)
            except Exception as e:
                print(f"  FAIL {bdsp_id}: {type(e).__name__} {e}", flush=True); Path(local).unlink(missing_ok=True); continue
            Path(local).unlink(missing_ok=True)
            row = {"bdsp_id": bdsp_id, "nseg": nseg}
            for f in FIDX: row[f"mat_{f}"] = mv[f]; row[f"py_{f}"] = ev[f]
            rows.append(row)
            print(f"  ok {bdsp_id} ses-{ses}: nseg={nseg} rel_delta mat={mv['rel_delta']:.3f} py={ev['rel_delta']:.3f}"
                  f" | rel_alpha mat={mv['rel_alpha']:.3f} py={ev['rel_alpha']:.3f}", flush=True)

    d = pd.DataFrame(rows)
    d.to_parquet("data/derived/pipeline_control.parquet")
    print(f"\n=== PIPELINE CONTROL: extract.py vs JJ .mat, same {len(d)} routine rEEG recordings ===")
    print(f"{'feature':<11}{'mat median':>12}{'py median':>12}{'bias(py-mat)':>14}{'Pearson r':>12}")
    for f in FIDX:
        mt, py = d[f"mat_{f}"], d[f"py_{f}"]
        r = np.corrcoef(mt, py)[0, 1] if len(d) > 2 else np.nan
        print(f"{f:<11}{mt.median():>12.3f}{py.median():>12.3f}{(py-mt).median():>+14.3f}{r:>12.2f}")
    print("\nrel_delta bias≈0 & high r  => pipeline reproduces JJ (delta) -> overnight gap is population/state.")
    print("rel_alpha: if py≈mat (both high on alert EEG) => overnight low-alpha is drowsiness, not a band bug.")


if __name__ == "__main__":
    main()
