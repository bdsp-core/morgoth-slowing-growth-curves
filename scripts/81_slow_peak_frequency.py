#!/usr/bin/env python3
"""Give the slowing an actual frequency, not just a band (review item C146-c).

Shafi, on Figure 4 panel (1,2): the clinical report says "3-5 Hz" while LENS says "theta-delta". A band word
throws away the number a clinician actually wrote down. This adds the missing measurement and checks it
against what the reports say.

Two halves:

  ground truth   Reported slowing frequency, parsed only from clauses that mention slowing -- an EEG report
                 is full of Hz values, but almost all of them describe the posterior dominant rhythm, so
                 parsing the whole report would validate against the wrong number.

  measurement    Slow-band dominant frequency: argmax of the multitaper PSD restricted to SLOW_BAND. The
                 stored peak_freq is over 1-45 Hz and therefore tracks the alpha rhythm in any record that
                 has one, which is why it cannot answer this. Computed here from the raw EDF for a sample of
                 recordings; rolling it out to the whole cohort is a feature-extraction (fleet) job.

Writes results/story/slow_peak_frequency.md + data/derived/slow_peak_freq_sample.parquet
Run: AWS_PROFILE=<profile> PYTHONPATH=src python3 scripts/81_slow_peak_frequency.py [--n 400]
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from morgoth_slowing.features import extract as ex, artifact as af, vanputten as vp
from morgoth_slowing.io.edf import load_edf_referential

SLOW_BAND = (1.0, 8.0)          # delta + theta; above this the alpha rhythm dominates the argmax
SEG_LEN_S = 15.0
MAX_SEG = 40                    # usable segments per recording is plenty for a frequency summary
RES = Path("results/story")
MANIFEST = "data/manifest/report_manifest_v6.parquet"

# Hz inside a clause that also mentions slowing. Ranges ("3-5 Hz") collapse to their midpoint.
HZ = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*hz|(\d+(?:\.\d+)?)\s*hz")


def reported_slow_hz(text: str) -> float | None:
    """Midpoint Hz from the first slowing clause carrying a plausible slow-band value."""
    for clause in re.split(r"[.;\n]", (text or "").lower()):
        if "slow" not in clause:
            continue
        m = HZ.search(clause)
        if not m:
            continue
        lo, hi, single = m.groups()
        v = (float(lo) + float(hi)) / 2 if lo else float(single)
        if SLOW_BAND[0] - 0.5 <= v <= SLOW_BAND[1] + 0.5:
            return v
    return None


def measure(edf_uri: str) -> tuple[float, float, float] | None:
    """(detrended slow peak, slow band median, full-band peak) over USABLE segments of one recording.

    Mirrors scripts/31 exactly: same loader, same preprocess+montage, same segment_indices stepping, and --
    critically -- the same artifact filter. An earlier version of this script did none of that and measured
    electrode drift, returning 1.0 Hz for every recording.
    """
    with tempfile.TemporaryDirectory() as td:
        local = Path(td) / "rec.edf"
        uri = ("s3://" + edf_uri[3:]) if edf_uri.startswith("s3:") and not edf_uri.startswith("s3://") else edf_uri
        try:
            subprocess.run(["aws", "s3", "cp", uri, str(local)], check=True, capture_output=True, timeout=900)
            data, chs, fs = load_edf_referential(str(local))
        except Exception:
            return None
    if data is None or not len(data):
        return None
    bip = ex.to_bipolar(ex.preprocess(data, fs), chs)
    peaks, meds, fulls = [], [], []
    for i, (s_, e_) in enumerate(ex.segment_indices(bip.shape[0])):
        if len(peaks) >= MAX_SEG:
            break
        seg = bip[s_:e_]
        ok, _ = af.segment_usable(seg, fs)
        if not ok:
            continue
        freqs, psd = ex.multitaper_psd(seg.T, fs)
        if not np.isfinite(psd).all():
            continue
        pk, md = vp.slow_freq(freqs, psd)
        if np.isfinite(pk):
            peaks.append(pk)
        if np.isfinite(md):
            meds.append(md)
        m = (freqs >= 1.0) & (freqs <= 45.0)
        fulls.append(float(freqs[m][int(np.argmax(psd[:, m].mean(axis=0)))]))
    if not peaks:
        return None
    return (float(np.median(peaks)), float(np.median(meds)) if meds else float("nan"),
            float(np.median(fulls)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400, help="recordings to measure")
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)

    man = pd.read_parquet(MANIFEST, columns=["eeg_id", "report_text", "report_impression",
                                             "resolved_path", "clean_pair"])
    man = man[man.clean_pair == True]                                            # noqa: E712
    txt = man.report_text.fillna("") + " " + man.report_impression.fillna("")
    man = man.assign(reported_hz=[reported_slow_hz(t) for t in txt])
    gt = man.dropna(subset=["reported_hz", "resolved_path"])
    print(f"recordings with a reported slowing frequency: {len(gt):,}")
    print(f"  reported Hz: median {gt.reported_hz.median():.1f}, "
          f"IQR {gt.reported_hz.quantile(.25):.1f}-{gt.reported_hz.quantile(.75):.1f}")

    samp = gt.sample(min(a.n, len(gt)), random_state=0)
    rows = []
    for k, r in enumerate(samp.itertuples(), 1):
        got = measure(str(r.resolved_path))
        if got:
            rows.append(dict(eeg_id=r.eeg_id, reported_hz=float(r.reported_hz),
                             slow_detrended_hz=got[0], slow_median_hz=got[1], full_peak_hz=got[2]))
        if k % 25 == 0:
            print(f"   {k}/{len(samp)} ({len(rows)} measured)", flush=True)
    d = pd.DataFrame(rows)
    if d.empty:
        print("no recordings measured")
        return
    d.to_parquet("data/derived/slow_peak_freq_sample.parquet")

    from scipy.stats import spearmanr
    lines = ["# Slow-band frequency vs the frequency the report states (C146-c)", "",
             f"Measured on **{len(d):,}** recordings that state a slowing frequency in a slowing clause "
             f"(cohort-wide, {len(gt):,} such recordings exist).", "",
             "| estimator | Spearman rho | p | median \\|error\\| |", "|---|---|---|---|"]
    best = None
    for col, name in [("slow_median_hz", "**slow-band median frequency (1-8 Hz)**"),
                      ("slow_detrended_hz", "slow-band 1/f-detrended peak"),
                      ("full_peak_hz", "full-band peak (1-45 Hz), the stored `peak_freq`")]:
        sub = d.dropna(subset=[col])
        if len(sub) < 10:
            lines.append(f"| {name} | insufficient | — | — |"); continue
        rho, pv = spearmanr(sub.reported_hz, sub[col])
        mae = float(np.abs(sub[col] - sub.reported_hz).median())
        lines.append(f"| {name} | {rho:.3f} | {pv:.2g} | {mae:.2f} Hz |")
        print(f"  {name:52s} rho={rho:+.3f} (p={pv:.2g})  median |err| {mae:.2f} Hz")
        if best is None or abs(rho) > abs(best[1]):
            best = (name, rho, mae)
    lines += ["", f"Reported frequency: median {d.reported_hz.median():.2f} Hz "
                  f"(IQR {d.reported_hz.quantile(.25):.2f}-{d.reported_hz.quantile(.75):.2f}); "
                  f"measured slow-band median {d.slow_median_hz.median():.2f} Hz "
                  f"(IQR {d.slow_median_hz.quantile(.25):.2f}-{d.slow_median_hz.quantile(.75):.2f}).", "",
              "A raw PSD argmax inside the slow band is NOT usable and is excluded: EEG power falls off as "
              "roughly 1/f^a, so the largest value in any low band is its lowest bin. Measured that way every "
              "recording returns 1.0 Hz exactly and the correlation with the reported frequency is nil "
              "(rho = -0.10). Both estimators above are constructed not to be dominated by that aperiodic "
              "background.", "",
              "The full-band peak is reported to show that the stored `peak_freq` cannot substitute: over "
              "1-45 Hz the argmax lands on the posterior dominant rhythm whenever the record has one."]
    (RES / "slow_peak_frequency.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {RES/'slow_peak_frequency.md'}")


if __name__ == "__main__":
    main()
