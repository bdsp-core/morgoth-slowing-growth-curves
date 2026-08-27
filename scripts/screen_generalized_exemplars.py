"""Rank candidate GENERALIZED-slowing exemplars by how cleanly the displayed window shows polymorphic
diffuse slowing rather than a periodic or rhythmic pattern.

Why this exists. Figures 4 and 5 pin their six recordings (scripts/62 `PINNED_EXAMPLES`) so that re-running
cannot silently swap in different patients mid-revision. The pin bypasses the report-text screen in
scripts/62, and that screen would not have caught this case anyway: co-author review found Figure 5A showing
what reads as LRDA or lateralised periodic discharges, while its report says "occasional PERIODS of
generalized delta slowing" -- which no `\\bperiodic\\b` pattern matches. The give-away is in the SIGNAL, so
this screens the signal.

Three scores per candidate, all computed on the exact 10-second window scripts/63 would display:

  rhythmicity   max normalised autocorrelation of the whole-head mean over lags 0.25-2.0 s. A stereotyped
                waveform that repeats -- periodic discharges, rhythmic delta -- scores high; irregular
                polymorphic slowing scores low. THIS IS THE ONE THAT MATTERS for the complaint.
  narrowband    fraction of 1-20 Hz power in the single best 1 Hz bin. LRDA/GRDA is narrowband by
                definition; polymorphic slowing is broad.
  asymmetry     |left - right| mean log power. A "generalized" exemplar should be near-symmetric; a
                lateralised pattern is not.

Lower is better on all three. The script ranks and prints; choosing the pin stays a human decision, and the
chosen id goes into scripts/62 with a comment saying why.

Run: AWS_PROFILE=<profile> PYTHONPATH=src python3 scripts/screen_generalized_exemplars.py [--n 14]
"""
from __future__ import annotations
import argparse
import importlib.util
import sys
from pathlib import Path
import numpy as np
import pandas as pd

RES = Path("results/story")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SEG_STEP_S = 14.0            # 15-s window, 14-s step (README canonical facts); verified t_start_s = seg*14


def pick_window_from_cache(cache: pd.DataFrame, eid: str, domstage: str) -> float:
    """The window scripts/63 would display for a GENERALIZED example, computed from the whole-head cache.

    scripts/63.pick_segment reads segment_deviation/, which is published only for the six already-pinned
    examples -- so a candidate cannot be screened through it. For the generalized branch the rule is just
    "max whole-head amount within the dominant stage, first hour", and every column that needs is in
    figure_cache/wholehead_z.parquet. Same rule, same answer, available for any recording.
    """
    d = cache[cache.eeg_id == eid]
    if d.empty:
        raise FileNotFoundError(f"{eid} not in the whole-head cache")
    d = d[d.segment * SEG_STEP_S < 3600]
    amt = d[["z__whole_head__log_delta", "z__whole_head__log_theta", "z__whole_head__log_TAR"]].mean(axis=1)
    d = d.assign(amt=amt)
    ds = d[d.stage == domstage]
    ds = ds if len(ds) else d
    return float(ds.sort_values("amt", ascending=False).iloc[0].segment * SEG_STEP_S)


def rhythmicity(bip: np.ndarray, sr: float, win_s: float = 3.0, hop_s: float = 0.5) -> float:
    """How much the most affected part of the trace repeats itself.

    The obvious version of this -- autocorrelation of the whole-head mean over the whole window -- does NOT
    reproduce a reader's judgement, and was checked against the case that prompted the screen. The run in the
    original Figure 5A is regional (right frontal) and occupies about 4 of the 10 seconds, so averaging over
    18 channels and 10 seconds diluted it to 0.18 -- BETTER than most of the candidates, which is plainly
    wrong. A periodic or rhythmic pattern is local in space and in time, so the measure has to be too:
    autocorrelation per CHANNEL over sliding 3-second sub-windows, then the worst case over both.
    """
    lo, hi = int(0.2 * sr), int(2.0 * sr)
    n = int(win_s * sr)
    hop = max(1, int(hop_s * sr))
    best = 0.0
    for ch in bip:
        for st in range(0, max(1, len(ch) - n + 1), hop):
            seg = ch[st:st + n]
            seg = seg - seg.mean()
            if seg.size < hi + 2 or not np.any(seg):
                continue
            ac = np.correlate(seg, seg, mode="full")[seg.size - 1:]
            if ac[0] <= 0:
                continue
            ac = ac / ac[0]
            h = min(hi, ac.size - 1)
            if h > lo:
                best = max(best, float(np.max(ac[lo:h])))
    return best


def narrowband(bip: np.ndarray, sr: float) -> float:
    """Fraction of 1-20 Hz power in the best single 1 Hz bin, on the most narrowband channel.

    Per channel for the same reason: LRDA is regional, and averaging hides it.
    """
    out = 0.0
    for ch in bip:
        x = np.asarray(ch, float) - np.mean(ch)
        f = np.fft.rfftfreq(len(x), 1 / sr)
        p = np.abs(np.fft.rfft(x)) ** 2
        band = (f >= 1) & (f <= 20)
        if not band.any() or p[band].sum() <= 0:
            continue
        best = max(p[(f >= c) & (f < c + 1)].sum() for c in np.arange(1, 20))
        out = max(out, float(best / p[band].sum()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=14, help="candidates to screen (each costs one EDF pull)")
    ap.add_argument("--band", default="marked", choices=["marked", "moderate", "mild"],
                    help="which degree slot to fill")
    args = ap.parse_args()

    m62 = _load("m62", "scripts/62_example_reports_panel.py")
    m63 = _load("m63", "scripts/63_example_eeg_traces.py")

    BANDS = {"marked": (3.0, 12.0), "moderate": (1.8, 3.0), "mild": (1.0, 1.8)}
    lo, hi = BANDS[args.band]

    ex = pd.read_parquet(RES / "s4_examples.parquet")
    pinned = set(ex.eeg_id)

    d, _S, _man, _meta, _stage = m62.candidate_frame()
    gen = d[(~d.isfoc) & d.gen & (d.slowing_gen_pathologic == True) & (d.slowing_focal != True)]  # noqa: E712
    gen = gen[(gen.peakz >= lo) & (gen.peakz < hi) & (~gen.eeg_id.isin(pinned))]
    gen = gen.sort_values("peakz", ascending=False).head(args.n)
    print(f"screening {len(gen)} exclusively-generalized candidates in the '{args.band}' band "
          f"(peak z {lo}-{hi}), excluding the six already pinned\n")

    man = pd.read_parquet("data/manifest/report_manifest_v6.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    ids = set(gen.eeg_id)
    cache = pd.read_parquet("data/derived/figure_cache/wholehead_z.parquet",
                            filters=[("eeg_id", "in", list(ids))],
                            columns=["eeg_id", "segment", "stage", "z__whole_head__log_delta",
                                     "z__whole_head__log_theta", "z__whole_head__log_TAR"])
    print(f"whole-head cache covers {cache.eeg_id.nunique()} of {len(ids)} candidates\n")
    rows = []
    for r in gen.itertuples():
        try:
            t0 = pick_window_from_cache(cache, r.eeg_id, r.domstage)
            mono, chs, fs = m63.fetch_window(man.loc[r.eeg_id], t0, r.eeg_id)
            bip = m63.bipolar(mono, chs, fs)
        except Exception as e:                                   # noqa: BLE001 - a candidate, not a producer
            print(f"  {r.eeg_id}  skipped ({type(e).__name__})")
            continue
        left = bip[[i for i, c in enumerate(m63.BIPOLAR) if c[0] in "FTCPO" and c.split("-")[0][-1] in "13579"]]
        right = bip[[i for i, c in enumerate(m63.BIPOLAR) if c.split("-")[0][-1] in "24680"]]
        rows.append(dict(eeg_id=r.eeg_id, peakz=r.peakz, stage=r.domstage, age=r.age, sex=r.sex,
                         rhythmicity=rhythmicity(bip, fs), narrowband=narrowband(bip, fs),
                         asymmetry=abs(np.log(np.mean(left ** 2) + 1e-9) - np.log(np.mean(right ** 2) + 1e-9))))
        print(f"  {r.eeg_id}  z={r.peakz:.1f}  {r.domstage}  rhythmicity={rows[-1]['rhythmicity']:.3f}  "
              f"narrowband={rows[-1]['narrowband']:.3f}  asym={rows[-1]['asymmetry']:.2f}")

    if not rows:
        print("no candidate could be screened (EDF access?)")
        return 1
    t = pd.DataFrame(rows)
    # rank on rhythmicity first -- that is the reviewer's objection -- then narrowband, then asymmetry
    t["rank"] = t.rhythmicity.rank() + 0.5 * t.narrowband.rank() + 0.25 * t.asymmetry.rank()
    t = t.sort_values("rank")

    RES.mkdir(parents=True, exist_ok=True)
    out = RES / f"generalized_exemplar_screen_{args.band}.md"
    out.write_text(
        f"# Generalized exemplar screen — '{args.band}' slot\n\n"
        "Lower is better on every column. `rhythmicity` is the max normalised autocorrelation of the "
        "whole-head mean over lags 0.25–2.0 s, i.e. how much the displayed window repeats itself; it is the "
        "score that separates a periodic or rhythmic pattern from polymorphic slowing. `narrowband` is the "
        "fraction of 1–20 Hz power in the best 1 Hz bin (LRDA/GRDA is narrowband). `asymmetry` is "
        "|left − right| mean log power.\n\n"
        + t.drop(columns=["rank"]).to_markdown(index=False, floatfmt=".3f") + "\n")
    print(f"\nwrote {out}")
    print("\nbest three:\n" + t.head(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
