"""Manuscript Figure 4 — six example recordings (3 focal | 3 generalized), each shown as the ACTUAL 10-second
EEG segment (double-banana longitudinal bipolar montage) with our brief + full automated report and the
clinical report's structured descriptors, laid out as a 3x2 panel.

EEG rendering follows the NeuroTech-Wrangling house style
(/Users/mwestover/GithubRepos/NeuroTech-Wrangling/manuscript-materials/make_supp_figure1_eeg.py): same BIPOLAR
montage, SPACING=150 uV, 1-30 Hz band-pass + 60 Hz notch, 100 uV / 1 s scale bar. Deviations by request:
black traces (not navy) and a gap between the four bipolar chains (visual grouping).

For each example: pick the representative 10-s segment (highest whole-head slowing deviation in the dominant
stage, within the first hour), resolve+pull its EDF from S3 (scripts/31 resolver), render, lay the reports
below. The pulled window is cached under .eeg_cache/ so re-runs (layout tweaks) do not re-hit S3.
Needs S3 access (rclone) + results/story/s4_examples.parquet (written by scripts/62).

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/63_example_eeg_traces.py
Writes figures/story/s4_examples_eeg_panel.png
"""
from __future__ import annotations
import os, subprocess, tempfile, textwrap, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch

from morgoth_slowing.io.edf import load_edf_referential
m31 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m31", "scripts/31_segment_master_worker.py"))
importlib.util.spec_from_file_location("m31", "scripts/31_segment_master_worker.py").loader.exec_module(m31)

FIG = Path("figures/story"); RES = Path("results/story"); DEV = "data/derived/segment_deviation"
CACHE = Path(".eeg_cache"); RC = os.environ.get("RCLONE_BIN", "/opt/homebrew/bin/rclone")
MANIFEST = "data/manifest/report_manifest_v6.parquet"
SEG_S = 10.0; AMT_Z = ["z__whole_head__log_delta", "z__whole_head__log_theta", "z__whole_head__log_TAR"]

# ---- house style (NeuroTech-Wrangling), black traces + chain gaps ----
TRACE_COLOR = "#000000"; DARK = "#1f2937"; GRAY = "#6b7280"
CHAINS = [["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"], ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],   # L-temporal, R-temporal
          ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"], ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"],   # L-parasagittal, R-parasagittal
          ["Fz-Cz", "Cz-Pz"]]                                                              # midline
BIPOLAR = [ch for chain in CHAINS for ch in chain]
SPACING = 150.0; GROUP_GAP = 95.0                                                          # uV between traces / between chains


def _offsets():
    """downward y-offset per channel = row*SPACING + (#chains above)*GROUP_GAP."""
    offs, y = [], 0.0
    for chain in CHAINS:
        for ch in chain:
            offs.append(y); y += SPACING
        y += GROUP_GAP
    return np.asarray(offs)


OFFS = _offsets()


def bipolar(mono, names, sr):
    idx = {n: i for i, n in enumerate(names)}
    rows = [mono[idx[a]].astype(float) - mono[idx[b]].astype(float) for a, b in (p.split("-") for p in BIPOLAR)]
    data = np.asarray(rows)
    nyq = sr / 2.0
    bb, ab = butter(4, [1.0 / nyq, 30.0 / nyq], btype="band"); data = filtfilt(bb, ab, data, axis=-1)
    bn, an = iirnotch(60.0, 30, sr); data = filtfilt(bn, an, data, axis=-1)
    return data


def plot_panel(ax, data, sr, title):
    n_ch, n_samp = data.shape; t = np.arange(n_samp) / sr
    for i in range(n_ch):
        ax.plot(t, (data[i] - data[i].mean()) - OFFS[i], color=TRACE_COLOR, linewidth=0.45, zorder=2)
    ax.set_yticks(-OFFS); ax.set_yticklabels(BIPOLAR, fontsize=5.6, color=DARK)
    ax.set_xlim(0, t[-1]); ax.set_ylim(-(OFFS[-1] + 0.6 * SPACING), 0.7 * SPACING)
    ax.set_title(title, fontsize=8.5, fontweight="bold", pad=3, loc="left")
    ax.set_xlabel("Time (s)", fontsize=7.5); ax.margins(x=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False, labelsize=6.5)
    # 100 uV / 1 s scale bar, lower-right
    x0 = t[-1] - 1.1; y0 = -(OFFS[-1] + 0.35 * SPACING)
    ax.plot([x0, x0 + 1.0], [y0, y0], color=DARK, lw=1.3, clip_on=False)
    ax.plot([x0, x0], [y0, y0 + 100], color=DARK, lw=1.3, clip_on=False)
    ax.text(x0 + 0.5, y0 - 0.16 * SPACING, "1 s", ha="center", va="top", fontsize=6.5)
    ax.text(x0 - 0.05, y0 + 50, "100 µV", ha="right", va="center", fontsize=6.5)


def pick_segment(eid, domstage):
    f = f"{DEV}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        return None
    d = pd.read_parquet(f); d = d[d.t_start_s < 3600]
    have = [c for c in AMT_Z if c in d.columns]; d = d.assign(amt=d[have].mean(axis=1))
    ds = d[d.stage == domstage]; ds = ds if len(ds) else d
    return float(ds.sort_values("amt", ascending=False).iloc[0].t_start_s)


def fetch_window(row, t0, eid):
    """Resolve+pull the EDF, return the SEG_S window (19 x n). Cached under .eeg_cache/ to avoid re-hitting S3."""
    cf = CACHE / f"{eid}_{int(round(t0))}.npz"
    if cf.exists():
        z = np.load(cf, allow_pickle=True); return z["data"], [str(x) for x in z["chs"]], float(z["fs"])
    ep, reason = m31.resolve_edf(row)
    if ep is None:
        raise RuntimeError(f"noedf:{reason}")
    with tempfile.TemporaryDirectory() as td:
        local = Path(td) / "rec.edf"
        subprocess.run([RC, "copyto", ep, str(local)], check=True, capture_output=True, timeout=1800)
        data, chs, fs = load_edf_referential(str(local), max_hours=max(0.1, t0 / 3600 + 0.05))
    s = int(round(t0 * fs)); n = int(round(SEG_S * fs)); s = min(s, data.shape[0] - n)
    win = data[s:s + n].T                                       # (19, n)
    CACHE.mkdir(exist_ok=True); np.savez(cf, data=win, chs=np.array(chs, dtype=object), fs=fs)
    return win, chs, fs


def main():
    ex = pd.read_parquet(RES / "s4_examples.parquet")
    man = pd.read_parquet(MANIFEST).drop_duplicates("eeg_id").set_index("eeg_id")
    foc = [r for _, r in ex.iterrows() if r.isfoc][:3]
    gen = [r for _, r in ex.iterrows() if not r.isfoc][:3]
    cols = [foc, gen]                                            # left column = focal, right column = generalized

    fig = plt.figure(figsize=(13.2, 17.4))
    outer = fig.add_gridspec(3, 2, wspace=0.14, hspace=0.30, left=0.05, right=0.985, top=0.955, bottom=0.02)
    ok = 0
    for c, colrows in enumerate(cols):
        for rr, r in enumerate(colrows):
            inner = outer[rr, c].subgridspec(2, 1, height_ratios=[2.5, 1.9], hspace=0.28)
            axe = fig.add_subplot(inner[0]); axt = fig.add_subplot(inner[1]); axt.axis("off")
            kind = "Focal" if r.isfoc else "Generalized"
            age = int(r.age) if np.isfinite(r.age) else "?"; sex = str(r.sex)[:1].upper()
            head = f"{kind} · {r.peakz:.1f} SD · {r.domstage} · {age}{sex}"
            try:
                t0 = pick_segment(r.eeg_id, r.domstage)
                mono, chs, fs = fetch_window(man.loc[r.eeg_id], t0, r.eeg_id)
                plot_panel(axe, bipolar(mono, chs, fs), fs, f"{head}   (10 s, t≈{t0/60:.0f} min)")
                ok += 1
            except Exception as e:
                axe.axis("off"); axe.text(0.5, 0.5, f"EEG unavailable\n{type(e).__name__}", ha="center", va="center",
                                          fontsize=8, transform=axe.transAxes); axe.set_title(head, fontsize=8.5, fontweight="bold", loc="left")
                print(f"  {r.eeg_id}: {type(e).__name__}: {e}", flush=True)
            y = [0.99]; LH = 0.093; C_LENS, C_REP = "#c2510a", "#3a3a3a"

            def emit(lab, text, color, wrapw=94):
                for k, ln in enumerate(textwrap.wrap(lab + (text or "—"), wrapw) or [""]):
                    axt.text(0.0, y[0], ln, fontsize=6.0, color=color, va="top", transform=axt.transAxes,
                             fontweight="bold" if k == 0 else "normal"); y[0] -= LH
                y[0] -= 0.02
            # two paired comparisons: our brief vs the report IMPRESSION; our detailed vs the report DESCRIPTION
            emit("LENS (brief): ", r.finding, C_LENS)
            emit("Report impression: ", getattr(r, "report_impression_text", "") or "(no slowing sentence)", C_REP)
            emit("LENS (detailed): ", r.paragraph, C_LENS)
            emit("Report description: ", getattr(r, "report_detail_text", "") or "(no slowing sentence)", C_REP)
    fig.suptitle("Figure 4.  Example 10-s EEG segments (longitudinal bipolar; 1–30 Hz + 60 Hz notch) with the "
                 "LENS automated report vs the clinical report.\nEach example pairs LENS's brief finding with the "
                 "report's impression, and LENS's detailed description with the report's description.  "
                 "Left column: focal.  Right: generalized.",
                 fontsize=10, y=0.995)
    fig.savefig(FIG / "s4_examples_eeg_panel.png", dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print(f"rendered EEG for {ok}/6 examples -> figures/story/s4_examples_eeg_panel.png")


if __name__ == "__main__":
    main()
