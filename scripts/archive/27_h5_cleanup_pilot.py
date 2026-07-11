"""Local pilot: EDF -> morgoth-H5 source-data cleanup (docs/source_data_cleanup_plan.md).

Pulls a handful of real scalp EDFs from the BDSP open-data repo (via rclone remote
`bdsp:`), runs classify -> channel-usefulness -> convert -> QC (Gates A & B) on each,
and prints a summary table proving the conversion is lossless and reports space saved.

Nothing is deleted; source EDFs are pulled into a local scratch dir and left intact.

Usage:
    PYTHONPATH=src .venv/bin/python scripts/27_h5_cleanup_pilot.py [--n 5] [--max-dur 900]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from morgoth_slowing.io import h5_convert as hc

RCLONE = os.path.expanduser("~/.local/bin/rclone")
REMOTE_BASE = "bdsp:bdsp-opendata-repository/EEG/bids/S0001"

# a spread of different subjects (first session EDF each) — modest sizes for a pilot
PILOT_SUBJECTS = [
    "sub-S0001111189302",   # ~36 MiB cEEG, 30ch
    "sub-S0001111189591",   # ~64 MiB rEEG
    "sub-S0001111189188",   # ~87 MiB EEG
    "sub-S0001111189925",   # ~159 MiB EEG
    "sub-S0001111189719",   # ~202 MiB EEG
]


def _rclone(args):
    return subprocess.run([RCLONE] + args, capture_output=True, text=True)


def first_edf_relpath(subject):
    r = _rclone(["lsf", "--files-only", f"{REMOTE_BASE}/{subject}/", "-R"])
    for line in r.stdout.splitlines():
        if line.endswith("eeg.edf"):
            return line.strip()
    return None


def pull(subject, relpath, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    local = os.path.join(dest_dir, f"{subject}__{os.path.basename(relpath)}")
    if not os.path.exists(local):
        r = _rclone(["copyto", f"{REMOTE_BASE}/{subject}/{relpath}", local])
        if r.returncode != 0:
            print(f"  rclone failed for {subject}: {r.stderr[:200]}", file=sys.stderr)
            return None
    return local


def fmt_mib(nbytes):
    return f"{nbytes / (1024 * 1024):.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5, help="number of EDFs")
    ap.add_argument("--max-dur", type=float, default=0.0,
                    help="cap each recording to this many seconds (0 = full record; "
                         "QC stays exact on whatever span is converted)")
    ap.add_argument("--scratch", default=os.path.join(
        os.path.dirname(__file__), "..", "data", "raw", "h5_pilot"))
    args = ap.parse_args()
    max_dur = args.max_dur if args.max_dur and args.max_dur > 0 else None

    scratch = os.path.abspath(args.scratch)
    edf_dir = os.path.join(scratch, "edf")
    h5_dir = os.path.join(scratch, "h5")
    os.makedirs(h5_dir, exist_ok=True)

    rows = []
    subjects = PILOT_SUBJECTS[: args.n]
    for subj in subjects:
        print(f"\n=== {subj} ===")
        rel = first_edf_relpath(subj)
        if rel is None:
            print("  no EDF found; skipping")
            continue
        edf = pull(subj, rel, edf_dir)
        if edf is None:
            continue
        edf_bytes = os.path.getsize(edf)
        print(f"  pulled {os.path.basename(edf)} ({fmt_mib(edf_bytes)} MiB)")

        raw = hc.read_raw(edf, max_duration=max_dur)
        cls = hc.classify_file(raw)
        print(f"  classify: {cls['classification']} "
              f"(1020={cls['n_1020']}, contacts={cls['n_contact']}, "
              f"nch={cls['n_channels']}, dur={raw.n_times / raw.info['sfreq']:.0f}s "
              f"@ {raw.info['sfreq']:.0f}Hz)")

        if cls["classification"] != "scalp":
            print(f"  -> not scalp; SKIP (left intact)")
            rows.append({"file": subj, "cls": cls["classification"], "skip": True})
            continue

        decisions = hc.channel_usefulness(raw)
        kept = {n: d for n, d in decisions.items() if d["keep"]}
        dropped = {n: d for n, d in decisions.items() if not d["keep"]}

        h5 = os.path.join(h5_dir, os.path.basename(edf).replace(".edf", ".h5"))
        summ = hc.edf_to_h5(edf, h5, max_duration=max_dur, raw=raw,
                            decisions=decisions, classification=cls["classification"])

        qc_a = hc.qc_reconstruction(edf, h5, max_duration=max_dur, raw=raw)
        qc_b = hc.qc_stats(edf, h5, max_duration=max_dur, raw=raw)

        h5_bytes = os.path.getsize(h5)
        # size comparison is on the *converted span*; with a full-record convert this is
        # a true full-EDF vs H5 (channel-prune + compression) measure.
        span_frac = raw.n_times / max(1, _full_n_times(edf))
        edf_span_bytes = edf_bytes * span_frac
        pct_saved = 100.0 * (1 - h5_bytes / edf_span_bytes) if edf_span_bytes else 0.0

        drop_reasons = ", ".join(f"{d['orig_label']}[{d['reason']}]"
                                 for d in dropped.values()) or "(none)"
        print(f"  channels: in={summ['n_in']} kept={summ['n_kept']} dropped={summ['n_dropped']}")
        print(f"  dropped: {drop_reasons}")
        print(f"  QC-A recon: max|Δ|={qc_a['max_abs_diff_uv']:.3e} µV  "
              f"maxMSE={qc_a['max_mse_uv2']:.3e} µV²  -> {'PASS' if qc_a['ok'] else 'FAIL'}")
        print(f"  QC-B stats: worst_stat_rel={qc_b['worst_stat_rel']:.2e} "
              f"worst_band_rel={qc_b['worst_band_rel']:.2e} -> {'PASS' if qc_b['ok'] else 'FAIL'}")
        print(f"  size: EDF(span)={fmt_mib(edf_span_bytes)} MiB  H5={fmt_mib(h5_bytes)} MiB "
              f"-> {pct_saved:.1f}% saved")

        rows.append({
            "file": subj, "cls": cls["classification"], "skip": False,
            "n_in": summ["n_in"], "n_kept": summ["n_kept"], "n_drop": summ["n_dropped"],
            "maxdiff": qc_a["max_abs_diff_uv"], "maxmse": qc_a["max_mse_uv2"],
            "qc_a": qc_a["ok"], "qc_b": qc_b["ok"],
            "edf_mib": edf_span_bytes / (1024 * 1024),
            "h5_mib": h5_bytes / (1024 * 1024), "pct_saved": pct_saved,
            "dropped": {d["orig_label"]: d["reason"] for d in dropped.values()},
        })

    _print_table(rows)


def _full_n_times(edf):
    import mne
    raw = mne.io.read_raw_edf(edf, preload=False, verbose="ERROR")
    return raw.n_times


def _print_table(rows):
    print("\n" + "=" * 110)
    print("PILOT SUMMARY (size compared on the converted span; QC exact on that span)")
    print("=" * 110)
    hdr = (f"{'file':<22}{'cls':<7}{'in':>4}{'kept':>5}{'drop':>5}"
           f"{'max|Δ|µV':>12}{'maxMSE':>11}{'A':>3}{'B':>3}"
           f"{'EDF MiB':>9}{'H5 MiB':>8}{'%saved':>8}")
    print(hdr)
    print("-" * 110)
    conv = [r for r in rows if not r.get("skip")]
    for r in rows:
        if r.get("skip"):
            print(f"{r['file']:<22}{r['cls']:<7}  (skipped: not scalp)")
            continue
        print(f"{r['file']:<22}{r['cls']:<7}{r['n_in']:>4}{r['n_kept']:>5}{r['n_drop']:>5}"
              f"{r['maxdiff']:>12.2e}{r['maxmse']:>11.1e}"
              f"{('Y' if r['qc_a'] else 'N'):>3}{('Y' if r['qc_b'] else 'N'):>3}"
              f"{r['edf_mib']:>9.1f}{r['h5_mib']:>8.1f}{r['pct_saved']:>7.1f}%")
    if conv:
        print("-" * 110)
        n = len(conv)
        print(f"{'MEAN':<22}{'':<7}"
              f"{sum(r['n_in'] for r in conv) / n:>4.0f}"
              f"{sum(r['n_kept'] for r in conv) / n:>5.0f}"
              f"{sum(r['n_drop'] for r in conv) / n:>5.0f}"
              f"{'':>12}{'':>11}"
              f"{('Y' if all(r['qc_a'] for r in conv) else 'N'):>3}"
              f"{('Y' if all(r['qc_b'] for r in conv) else 'N'):>3}"
              f"{sum(r['edf_mib'] for r in conv) / n:>9.1f}"
              f"{sum(r['h5_mib'] for r in conv) / n:>8.1f}"
              f"{sum(r['pct_saved'] for r in conv) / n:>7.1f}%")
    print("=" * 110)


if __name__ == "__main__":
    main()
