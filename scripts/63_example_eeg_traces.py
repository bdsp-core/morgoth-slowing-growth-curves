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
Writes figures/story/s4_examples_eeg_{focal,generalized,mild}.png
"""
from __future__ import annotations
import os, re, subprocess, tempfile, textwrap, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette
from scipy.signal import butter, filtfilt, iirnotch

from morgoth_slowing.io.edf import load_edf_referential
m31 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m31", "scripts/31_segment_master_worker.py"))
importlib.util.spec_from_file_location("m31", "scripts/31_segment_master_worker.py").loader.exec_module(m31)

FIG = Path("figures/story"); RES = Path("results/story"); DEV = "data/derived/segment_deviation"
CACHE = Path(".eeg_cache"); RC = os.environ.get("RCLONE_BIN", "/opt/homebrew/bin/rclone")
MANIFEST = "data/manifest/report_manifest_v6.parquet"
SEG_S = 10.0; PAD_S = 3.0; AMT_Z = ["z__whole_head__log_delta", "z__whole_head__log_theta", "z__whole_head__log_TAR"]

# ---- house style (NeuroTech-Wrangling), black traces + chain gaps ----
TRACE_COLOR = "#000000"; DARK = "#1f2937"; GRAY = "#6b7280"
CHAINS = [["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"], ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],   # L-temporal, R-temporal
          ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"], ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"],   # L-parasagittal, R-parasagittal
          ["Fz-Cz", "Cz-Pz"]]                                                              # midline
BIPOLAR = [ch for chain in CHAINS for ch in chain]
SPACING = 150.0; GROUP_GAP = 45.0                                                          # uV between traces / between chains


def _offsets():
    """downward y-offset per channel = row*SPACING + (#chains above)*GROUP_GAP."""
    offs, y = [], 0.0
    for chain in CHAINS:
        for ch in chain:
            offs.append(y); y += SPACING
        y += GROUP_GAP
    return np.asarray(offs)


OFFS = _offsets()
LABEL_PT = 7.0                                                                             # >= the 6 pt floor


Y_SPAN = OFFS[-1] + 1.3 * SPACING                        # data units the trace axes shows (see plot_panel)
# Inches of axes height the 18 channel labels need in order not to collide. Derived, not guessed: the
# tightest gap is one SPACING out of Y_SPAN, and a label needs a little more room than its own point size.
TRACE_H_IN = LABEL_PT * 1.15 * Y_SPAN / (SPACING * 72.0)


def check_label_spacing(fig, ax):
    """Fail loudly if the channel labels are closer together than they are tall.

    The overlap that made this figure unreadable in review round 1 is purely geometric: tick spacing in
    points versus font size in points. Measuring it is one line, so there is no reason to rely on someone
    noticing it in a rendered PNG again."""
    fig.canvas.draw()
    h_in = ax.get_window_extent().height / fig.dpi
    span = ax.get_ylim()[1] - ax.get_ylim()[0]
    gap_pt = (SPACING / span) * h_in * 72.0                    # tightest gap = within-chain spacing
    if gap_pt < LABEL_PT * 1.10:
        raise SystemExit(
            f"channel labels would overlap: {gap_pt:.1f} pt between rows vs {LABEL_PT} pt type. "
            f"Give the trace axes more height (TRACE_H_IN in main()) or lower LABEL_PT -- but not below 6.")
    return gap_pt


def bipolar(mono, names, sr):
    idx = {n: i for i, n in enumerate(names)}
    rows = [mono[idx[a]].astype(float) - mono[idx[b]].astype(float) for a, b in (p.split("-") for p in BIPOLAR)]
    data = np.asarray(rows)
    nyq = sr / 2.0
    bb, ab = butter(4, [1.0 / nyq, 30.0 / nyq], btype="band"); data = filtfilt(bb, ab, data, axis=-1)
    bn, an = iirnotch(60.0, 30, sr); data = filtfilt(bn, an, data, axis=-1)
    return data


def highlight_rows(finding):
    """Row indices of the bipolar chains that contain the electrode LENS names as the maximum.

    The figure asks the reader to check a claim against a trace, so it should say WHERE to look. The claim
    text already carries the electrode ("... (max T4)"); this turns that into a tint behind the two or three
    derivations that electrode appears in. Returns () when the finding names no electrode (generalized
    slowing), which is correct -- there is no single place to point at."""
    m = re.search(r"max ([A-Za-z]+\d*)\)", finding or "")
    if not m:
        return ()
    e = m.group(1).upper()
    return tuple(i for i, ch in enumerate(BIPOLAR) if e in ch.upper().split("-"))


def plot_panel(ax, data, sr, title, hl=()):
    n_ch, n_samp = data.shape; t = np.arange(n_samp) / sr
    for i in hl:
        ax.axhspan(-OFFS[i] - 0.42 * SPACING, -OFFS[i] + 0.42 * SPACING,
                   color="#e6550d", alpha=0.085, lw=0, zorder=0)
    for i in range(n_ch):
        ax.plot(t, (data[i] - data[i].mean()) - OFFS[i], color=TRACE_COLOR, linewidth=0.45, zorder=2)
    # Channel labels are the load-bearing text in a clinical EEG figure -- a reader has to be able to say
    # WHICH chain carries the slowing. At 5.6 pt in a 1.4 in-tall panel the within-chain rows sat closer
    # together than the glyph height, so 10 of the 18 labels overprinted their neighbour and the panel was
    # unreadable exactly where it mattered. The panel is now tall enough (see the gridspec in main()) for
    # 6.5 pt with clear separation; check_label_spacing() below fails loudly if that ever stops being true.
    ax.set_yticks(-OFFS); ax.set_yticklabels(BIPOLAR, fontsize=LABEL_PT, color=DARK)
    ax.set_xlim(0, t[-1]); ax.set_ylim(-(OFFS[-1] + 0.95 * SPACING), 0.7 * SPACING)
    ax.set_title(title, fontsize=8.5, fontweight="bold", pad=3, loc="left")
    ax.set_xlabel("Time (s)", fontsize=8); ax.margins(x=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False, labelsize=7)
    # 100 uV / 1 s scale bar, lower-right
    x0 = t[-1] - 1.1; y0 = -(OFFS[-1] + 0.72 * SPACING)
    ax.plot([x0, x0 + 1.0], [y0, y0], color=DARK, lw=1.3, clip_on=False)
    ax.plot([x0, x0], [y0, y0 + 100], color=DARK, lw=1.3, clip_on=False)
    ax.text(x0 + 0.5, y0 - 0.06 * SPACING, "1 s", ha="center", va="top", fontsize=7)
    ax.text(x0 - 0.05, y0 + 50, "100 µV", ha="right", va="center", fontsize=7)


SEG_STEP_S = 14.0                       # 15-s window, 14-s step; t_start_s == segment * 14 (verified)
_WH_CACHE = "data/derived/figure_cache/wholehead_z.parquet"


def _pairs(r):
    """The two comparisons each example shows, in order: (LENS label, LENS text, report label, report text)."""
    return [("LENS: ", r.finding,
             "Report impression: ", getattr(r, "report_impression_text", "") or "(no slowing sentence)"),
            ("LENS (detailed): ", getattr(r, "paragraph", ""),
             "Report description: ", getattr(r, "report_detail_text", "") or "(no slowing sentence)")]


def _text_lines(r, wrapw):
    """Lines of type the paired text needs: per pair, the taller of the two columns, plus the inter-pair gap."""
    n = 0.0
    for lab_l, text_l, lab_r, text_r in _pairs(r):
        ll = textwrap.wrap(lab_l + (text_l or "\u2014"), wrapw) or [""]
        lr = textwrap.wrap(lab_r + (text_r or "\u2014"), wrapw) or [""]
        n += max(len(ll), len(lr)) + 0.55
    return n


def _pick_generalized_from_cache(eid, domstage):
    """Max whole-head amount in the dominant stage, first hour -- from the cache. None if unavailable."""
    if not os.path.exists(_WH_CACHE):
        return None
    cols = ["segment", "stage"] + AMT_Z
    d = pd.read_parquet(_WH_CACHE, filters=[("eeg_id", "==", eid)], columns=cols)
    if d.empty:
        return None
    d = d[d.segment * SEG_STEP_S < 3600]
    have = [c for c in AMT_Z if c in d.columns]
    if not have or d.empty:
        return None
    d = d.assign(amt=d[have].mean(axis=1))
    ds = d[d.stage == domstage]
    ds = ds if len(ds) else d
    return float(ds.sort_values("amt", ascending=False).iloc[0].segment * SEG_STEP_S)


def pick_segment(eid, domstage, region=None):
    """Display window = where the finding is clearest. FOCAL: the segment where the CLAIMED region's slowing
    peaks (so the plotted window matches the label, not an off-region/artefact whole-head max — QC 2026-07-19).
    GENERALIZED: the max whole-head amount. Restricted to the dominant stage, first hour."""
    if region is None:
        # GENERALIZED: the rule is "max whole-head amount in the dominant stage, first hour", and every
        # column that needs is in figure_cache/wholehead_z.parquet -- which the figure-loop tier already
        # ships for every recording. So a generalized example needs NO per-recording segment_deviation
        # partition, and swapping one in costs nothing to publish. Verified equivalent: for all three
        # generalized examples that have both sources, the two paths choose the identical window
        # (t0 = 2254.0 / 2408.0 / 1036.0 s).
        t0 = _pick_generalized_from_cache(eid, domstage)
        if t0 is not None:
            return t0
    f = f"{DEV}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        # Returning None here silently changed which 10-s window got plotted: fetch_window falls back to a
        # default offset, so on an install without segment_deviation/ this figure rendered DIFFERENT traces
        # for the same patients, with no error. The figure-loop tier deliberately ships only the whole-head
        # cache (no per-region z, no t_start_s), so the six example partitions are published separately --
        # see REPRODUCE.md. Fail loudly rather than draw the wrong window.
        raise FileNotFoundError(
            f"{f} is required to choose the displayed window for {eid}. Sync the example partitions:\n"
            f"  aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/segment_deviation_examples/ "
            f"data/derived/segment_deviation/")
    d = pd.read_parquet(f); d = d[d.t_start_s < 3600]
    cols = [f"z__{region}__{ft}" for ft in ("log_delta", "log_theta", "log_TAR")] if region else AMT_Z
    have = [c for c in cols if c in d.columns] or [c for c in AMT_Z if c in d.columns]
    d = d.assign(amt=d[have].mean(axis=1))
    ds = d[d.stage == domstage]; ds = ds if len(ds) else d
    return float(ds.sort_values("amt", ascending=False).iloc[0].t_start_s)


def fetch_window(row, t0, eid):
    """Resolve+pull the EDF, return the SEG_S window (19 x n). Cached under .eeg_cache/ to avoid re-hitting S3."""
    cf = CACHE / f"{eid}_{int(round(t0))}.npz"
    if cf.exists():
        z = np.load(cf, allow_pickle=True)
        tr = tuple(z["trim"]) if "trim" in z else (0, 0)
        return z["data"], [str(x) for x in z["chs"]], float(z["fs"]), tr
    # The manifest is pre-flight-resolved (scripts/129), so resolved_path already names the exact session
    # EDF. Prefer it: rclone is otherwise required just to re-discover a path we already know, and it is an
    # undocumented dependency that anyone with plain AWS credentials should not need.
    ep = getattr(row, "resolved_path", None)
    if ep is None or (isinstance(ep, float) and np.isnan(ep)):
        ep, reason = m31.resolve_edf(row)
        if ep is None:
            raise RuntimeError(f"noedf:{reason}")
    with tempfile.TemporaryDirectory() as td:
        local = Path(td) / "rec.edf"
        uri = str(ep)
        if uri.startswith("s3:") and not uri.startswith("s3://"):   # rclone-style -> aws CLI style
            uri = "s3://" + uri[3:]
        if uri.startswith("s3://"):
            subprocess.run(["aws", "s3", "cp", uri, str(local)], check=True, capture_output=True, timeout=1800)
        else:
            subprocess.run([RC, "copyto", uri, str(local)], check=True, capture_output=True, timeout=1800)
        data, chs, fs = load_edf_referential(str(local), max_hours=max(0.1, t0 / 3600 + 0.05))
    # Take PAD_S extra seconds either side. bipolar() band-passes and notches the window it is given, and
    # filtfilt rings at the edges of a short clip: on a 10 s window the settling transient was a visible
    # exponential swing on the posterior derivations for the first second, which reads as a real waveform.
    # The pad is filtered too and then cropped away, so the displayed 10 s is interior to the filtered span.
    s = int(round(t0 * fs)); n = int(round(SEG_S * fs))
    pad = int(round(PAD_S * fs))
    lo = max(0, s - pad); hi = min(data.shape[0], s + n + pad)
    if hi - lo < n:                                             # clip shorter than the window itself
        lo, hi = max(0, data.shape[0] - n), data.shape[0]
    win = data[lo:hi].T                                         # (19, n + padding)
    trim = (s - lo, hi - (s + n))                               # samples of pad kept on each side
    CACHE.mkdir(exist_ok=True); np.savez(cf, data=win, chs=np.array(chs, dtype=object), fs=fs,
                                        trim=np.array(trim))
    return win, chs, fs, trim


def main():
    ex = pd.read_parquet(RES / "s4_examples.parquet")
    man = pd.read_parquet(MANIFEST).drop_duplicates("eeg_id").set_index("eeg_id")
    foc = [r for _, r in ex.iterrows() if r.isfoc][:3]
    gen = [r for _, r in ex.iterrows() if not r.isfoc][:3]
    # Review C146-f: as one 3x2 grid this figure was 12.9in wide and printed at 54%, which is why its report
    # text was unreadable. It cannot be narrowed -- bbox_inches="tight" grows the canvas to fit the text, so
    # shrinking the canvas or enlarging the fonts both make it worse. Split into two single-column figures
    # instead: each is page-width, so nothing is scaled down.
    # TWO panels per figure, not three. Three stacked panels plus their report text cannot fit a portrait
    # page at legible size: it gave each trace block 1.56 in for 19 channels (0.082 in/channel), which is why
    # the derivation labels collided. The earlier 3x2 grid was no better in print -- 0.164 in/channel on
    # screen, but the figure had to scale to 52% on the page, so 0.085 in/channel effective. Only reducing
    # the panel count lets the figure print at 100%: 2 panels give 0.147 in/channel, inside the 0.15-0.20
    # convention, with the report text unshrunk. The third (mildest) example of each axis moves to a
    # supplementary figure rather than being dropped.
    panels = [("focal", foc[:2], "s4_examples_eeg_focal.png",
               "Example focal slowing: 10-s EEG segments with the LENS automated report vs the clinical report"),
              ("generalized", gen[:2], "s4_examples_eeg_generalized.png",
               "Example generalized slowing: 10-s EEG segments with the LENS automated report vs the clinical report"),
              ("mild", foc[2:3] + gen[2:3], "s4_examples_eeg_mild.png",
               "Mild examples: 10-s EEG segments with the LENS automated report vs the clinical report")]
    ok = 0
    for kind_name, rows, outname, title in panels:
        if not rows:
            continue
        # Height budget, in inches, computed rather than tuned by eye. Two constraints fight each other and
        # the round-1 figure lost both:
        #   * the trace panel must be tall enough for 18 channel labels not to collide -> TRACE_H_IN, and
        #   * the whole figure must fit 190 x 240 mm WITHOUT being scaled down, because a figure the journal
        #     shrinks to fit the page shrinks its labels below the legibility floor at the same time.
        # Laying the axes out in absolute figure fractions derived from inches makes both checkable here
        # instead of after someone prints it. Pairing the LENS and report text in two columns (rather than
        # four stacked blocks) is what buys the room: it roughly halves the text height AND puts each
        # comparison side by side, which is the claim the figure is making.
        # BOTH comparisons ride with the trace, as the Figure 4/5 captions state: LENS's brief finding against
        # the report's impression, and LENS's detailed paragraph against the report's description. Carrying
        # the detailed pair is affordable now only because each figure holds two examples, not three; with
        # three, the four text blocks forced the figure to ~12 in and the journal's shrink-to-fit pulled every
        # label under 6 pt (round-1 item C146-f). So the text height is measured from the actual wrapped text
        # of the longest example in THIS figure, and the page-fit guard below re-checks the result.
        TXT_PT, WRAPW = 7.0, 55
        LH_IN = TXT_PT * 1.25 / 72.0                       # one line of type, inches
        TEXT_H = max(_text_lines(r, WRAPW) for r in rows) * LH_IN + 0.06
        GAP, TOP_M, BOT_M, TITLE_H, XAXIS_H = 0.16, 0.08, 0.08, 0.17, 0.34
        # Two examples per figure (see `panels`) is what makes room for taller traces: use it to reach the
        # clinical 0.15 in/channel convention, and never go below TRACE_H_IN, the label-collision floor.
        TRACE_H = max(TRACE_H_IN, 0.15 * len(BIPOLAR))
        n = len(rows)
        cell = TITLE_H + TRACE_H + XAXIS_H + TEXT_H
        FIG_H = n * cell + (n - 1) * GAP + TOP_M + BOT_M
        FIG_W, LEFT, RIGHT = 7.1, 0.085, 0.985
        page_scale = min(190.0, 240.0 * FIG_W / FIG_H) / (FIG_W * 25.4)
        if min(LABEL_PT, TXT_PT) * page_scale < 6.0:
            raise SystemExit(f"at {FIG_W:.2f}x{FIG_H:.2f} in the page scale is {page_scale:.2f}, so the "
                             f"{LABEL_PT} pt channel labels would print at {LABEL_PT*page_scale:.1f} pt")
        fig = plt.figure(figsize=(FIG_W, FIG_H))
        for rr, r in enumerate(rows):
            top = 1.0 - (TOP_M + rr * (cell + GAP)) / FIG_H
            axe = fig.add_axes([LEFT, top - (TITLE_H + TRACE_H) / FIG_H,
                                RIGHT - LEFT, TRACE_H / FIG_H])
            axt = fig.add_axes([LEFT, top - cell / FIG_H, RIGHT - LEFT, TEXT_H / FIG_H]); axt.axis("off")
            axt.set_zorder(-1)
            # One letter per example, so each case is citable from the text individually.
            palette.panel_letter(axe, rr, dx=-0.075, dy=1.14)
            kind = "Focal" if r.isfoc else "Generalized"
            age = int(r.age) if np.isfinite(r.age) else "?"; sex = str(r.sex)[:1].upper()
            head = f"{kind} · {r.peakz:.1f} SD · {r.domstage} · {age}{sex}"
            try:
                t0 = pick_segment(r.eeg_id, r.domstage, r.get("peak_region"))
                mono, chs, fs, trim = fetch_window(man.loc[r.eeg_id], t0, r.eeg_id)
                bip = bipolar(mono, chs, fs)
                a_, b_ = int(trim[0]), int(trim[1])
                bip = bip[:, a_: bip.shape[1] - b_] if (a_ or b_) else bip     # drop the filtered padding
                plot_panel(axe, bip, fs, f"{head}   (10 s, t≈{t0/60:.0f} min)", hl=highlight_rows(r.finding))
                check_label_spacing(fig, axe)
                ok += 1
            except FileNotFoundError:
                # A missing deviation partition means we cannot know WHICH window to plot, so the panel
                # would be silently wrong rather than merely absent. The generic handler below exists for
                # transient S3/EDF problems; provenance errors must stop the run instead of being drawn.
                raise
            except Exception as e:
                axe.axis("off"); axe.text(0.5, 0.5, f"EEG unavailable\n{type(e).__name__}", ha="center", va="center",
                                          fontsize=8, transform=axe.transAxes); axe.set_title(head, fontsize=8.5, fontweight="bold", loc="left")
                print(f"  {r.eeg_id}: {type(e).__name__}: {e}", flush=True)
            LH = LH_IN / TEXT_H                            # one line of type, as a fraction of the text axes
            y = [1.0]; C_LENS, C_REP = "#c2510a", "#3a3a3a"

            def emit_pair(lab_l, text_l, lab_r, text_r, wrapw=WRAPW):
                """One comparison per ROW, LENS on the left, the clinical report on the right.

                Round 1 read these as four stacked blocks, so the reader had to hold the LENS sentence in
                their head while scanning down to the report sentence it is being compared against. Side by
                side, the comparison the figure is making is the thing you actually see."""
                ll = textwrap.wrap(lab_l + (text_l or "\u2014"), wrapw) or [""]
                lr = textwrap.wrap(lab_r + (text_r or "\u2014"), wrapw) or [""]
                for x, lines, color in ((0.0, ll, C_LENS), (0.515, lr, C_REP)):
                    for k, ln in enumerate(lines):
                        axt.text(x, y[0] - k * LH, ln, fontsize=TXT_PT, color=color, va="top",
                                 transform=axt.transAxes, fontweight="bold" if k == 0 else "normal")
                y[0] -= max(len(ll), len(lr)) * LH + LH * 0.55
            # two paired comparisons: our brief vs the report IMPRESSION; our detailed vs the report DESCRIPTION
            for lab_l, text_l, lab_r, text_r in _pairs(r):
                emit_pair(lab_l, text_l, lab_r, text_r)
        # Title, montage and filter settings are in the figure captions in
        # docs/manuscript_draft.md (Clinical Neurophysiology wants the descriptive title in the legend), and
        # the height it used to cost is spent on the traces instead.
        fig.savefig(FIG / outname, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  wrote figures/story/{outname}")
    print(f"rendered EEG for {ok}/6 examples across {len(panels)} figures")


if __name__ == "__main__":
    main()
