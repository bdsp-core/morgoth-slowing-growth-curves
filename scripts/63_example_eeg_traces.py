"""Manuscript figure — the 6 example recordings from scripts/62, now each with the ACTUAL 15-second EEG
segment (double-banana longitudinal bipolar montage) beside our brief + full reports and the clinical
report's structured descriptors.

The EEG trace rendering is copied VERBATIM from the NeuroTech-Wrangling house style
(/Users/mwestover/GithubRepos/NeuroTech-Wrangling/manuscript-materials/make_supp_figure1_eeg.py):
same BIPOLAR montage order, SPACING=150 µV, 1–30 Hz band-pass + 60 Hz notch, navy traces, scale bar —
so the display matches the group's optimized layout. Do not reinvent it.

For each example: pick the representative 15-s segment (highest whole-head slowing deviation in the
recording's dominant stage, within the first hour), resolve+pull its EDF from S3 (scripts/31 resolver),
render the trace, and lay the reports alongside. Needs S3 access (rclone) + results/story/s4_examples.parquet
(written by scripts/62).

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
RC = os.environ.get("RCLONE_BIN", "/opt/homebrew/bin/rclone")
MANIFEST = "data/manifest/report_manifest_v6.parquet"
FS = 200.0; SEG_S = 15.0; AMT_Z = ["z__whole_head__log_delta", "z__whole_head__log_theta", "z__whole_head__log_TAR"]

# ---- NeuroTech-Wrangling house style (copied verbatim) ----
TRACE_COLOR = "#1a1a80"; DARK = "#1f2937"; GRAY = "#6b7280"
BIPOLAR = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",
           "Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2", "Fz-Cz", "Cz-Pz"]
SPACING = 150.0


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
        ax.plot(t, (data[i] - data[i].mean()) - i * SPACING, color=TRACE_COLOR, linewidth=0.5, zorder=2)
    ax.set_yticks([-i * SPACING for i in range(n_ch)]); ax.set_yticklabels(BIPOLAR, fontsize=6.5, color=DARK)
    ax.set_xlim(0, t[-1]); ax.set_ylim(-(n_ch - 0.5) * SPACING, 0.7 * SPACING)
    ax.set_title(title, fontsize=9, fontweight="bold", pad=4); ax.set_xlabel("Time (s)", fontsize=8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False, labelsize=7)
    # 1 s / 100 µV scale bar, lower-right
    x0 = t[-1] - 1.15; y0 = -(n_ch - 0.4) * SPACING
    ax.plot([x0, x0 + 1.0], [y0, y0], color=DARK, lw=1.4, clip_on=False)
    ax.plot([x0, x0], [y0, y0 + 100], color=DARK, lw=1.4, clip_on=False)
    ax.text(x0 + 0.5, y0 - 0.14 * SPACING, "1 s", ha="center", va="top", fontsize=7)
    ax.text(x0 - 0.06, y0 + 50, "100 µV", ha="right", va="center", fontsize=7)


def pick_segment(eid, domstage):
    """t_start_s of the strongest whole-head slowing segment in the dominant stage, within the first hour."""
    f = f"{DEV}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        return None
    d = pd.read_parquet(f)
    d = d[d.t_start_s < 3600]                                    # keep the S3 read small
    have = [c for c in AMT_Z if c in d.columns]
    d = d.assign(amt=d[have].mean(axis=1))
    ds = d[d.stage == domstage]
    ds = ds if len(ds) else d
    return float(ds.sort_values("amt", ascending=False).iloc[0].t_start_s)


def fetch_window(row, t0):
    """Resolve + pull the EDF, load referential up to just past t0, return the 15-s window (19 x n)."""
    ep, reason = m31.resolve_edf(row)
    if ep is None:
        raise RuntimeError(f"noedf:{reason}")
    with tempfile.TemporaryDirectory() as td:
        local = Path(td) / "rec.edf"
        subprocess.run([RC, "copyto", ep, str(local)], check=True, capture_output=True, timeout=1800)
        data, chs, fs = load_edf_referential(str(local), max_hours=max(0.1, t0 / 3600 + 0.05))
    s = int(round(t0 * fs)); n = int(round(SEG_S * fs))
    s = min(s, data.shape[0] - n)
    return data[s:s + n].T, chs, fs                             # (19, n)


def main():
    ex = pd.read_parquet(RES / "s4_examples.parquet")
    man = pd.read_parquet(MANIFEST).drop_duplicates("eeg_id").set_index("eeg_id")
    n = len(ex); fig = plt.figure(figsize=(15, 3.4 * n + 0.4))
    gs = fig.add_gridspec(n, 2, width_ratios=[1.45, 1], wspace=0.05, hspace=0.42)
    ok = 0
    for i, r in ex.iterrows():
        axe = fig.add_subplot(gs[i, 0]); axt = fig.add_subplot(gs[i, 1]); axt.axis("off")
        kind = "Focal" if r.isfoc else "Generalized"
        age = int(r.age) if np.isfinite(r.age) else "?"; sex = str(r.sex)[:1].upper()
        header = f"Case {i+1}.  {kind} · peak {r.peakz:.1f} SD · prominent in {r.domstage} · {age}{sex}"
        try:
            t0 = pick_segment(r.eeg_id, r.domstage)
            mono, chs, fs = fetch_window(man.loc[r.eeg_id], t0)
            plot_panel(axe, bipolar(mono, chs, fs), fs, f"{header}  (15 s, {r.domstage}, t≈{t0/60:.0f} min)")
            ok += 1
        except Exception as e:
            axe.axis("off"); axe.text(0.5, 0.5, f"EEG unavailable\n{type(e).__name__}", ha="center", va="center",
                                      fontsize=9, transform=axe.transAxes); axe.set_title(header, fontsize=9, fontweight="bold")
            print(f"  {r.eeg_id}: {type(e).__name__}: {e}", flush=True)
        # reports
        y = [0.98]; LH = 0.075

        def emit(text, color, wrapw=64, gap=0.03):
            for ln in (textwrap.wrap(text, wrapw) or [""]):
                axt.text(0.0, y[0], ln, fontsize=8.2, color=color, va="top", transform=axt.transAxes); y[0] -= LH
            y[0] -= gap
        emit("Ours (brief): " + r.finding, "#127a3d")
        emit("Ours (full): " + r.paragraph, "#12608a")
        emit("Clinical report: " + r.report_struct, "#a5561f")
    fig.suptitle("Example EEG segments with automated slowing reports vs the clinical report "
                 "(longitudinal bipolar; 1–30 Hz, 60 Hz notch)", fontsize=12.5, y=0.997)
    fig.savefig(FIG / "s4_examples_eeg_panel.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    print(f"rendered EEG for {ok}/{n} examples -> figures/story/s4_examples_eeg_panel.png")


if __name__ == "__main__":
    main()
