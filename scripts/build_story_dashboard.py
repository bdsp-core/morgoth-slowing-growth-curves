#!/usr/bin/env python3
"""The STORY dashboard — a living scaffold for the slowing paper, in the order the argument is built.

Three sections, in narrative order:
  0. Can Morgoth DETECT focal / generalized slowing?  (validated against multi-rater expert panels)
  1. How well does the detector work on the big single-scorer REPORT dataset, and how do we turn
     per-segment (30 s-context) detections into an EEG-level probability and a segment SELECTION?
  2. GROWTH CURVES: the stage-wise normative deviation field every 30 s segment is scored against.

Each panel states its METHOD and shows the figures/tables that exist on this run; panels not yet built are
marked "to build" so the scaffold makes the remaining work explicit. Self-contained HTML (PNGs base64-inlined,
md/csv inlined) so it is a single file to open or share.

Run: PYTHONPATH=src python3 scripts/build_story_dashboard.py  ->  results/story_dashboard.html
"""
from __future__ import annotations
import base64, glob, subprocess, time
from pathlib import Path
import pandas as pd

OUT = Path("results/story_dashboard.html")
G = Path("figures/growth_v2"); STY = Path("figures/story"); RP = Path("figures/roc_prc")
C = Path("figures/curves"); S = Path("figures/stage_curves"); RES = Path("results/story")

# A section = (number, title, lede). Each block = (subtitle, method-caption, [fig paths], [table paths]).
SECTIONS = [
    (
        "1", "The normative deviation model",
        "Every feature is expressed as a DEVIATION from its age- and sleep-stage-matched normal. Growth curves "
        "are fit on clean-normal recordings, then every 15 s segment is scored against its OWN (stage, age) "
        "normal — so 'abnormal' always means abnormal FOR THIS AGE AND THIS SLEEP STAGE. This per-segment "
        "deviation field is the substrate the detector runs on (and, next, the description).",
        [
            ("1a. Normative growth curves per sleep stage (keystone)",
             "GAMLSS/BCT centile fans per (stage × region × feature): μ, σ, skew, kurtosis smooth in log-age, "
             "fit on clean-normal only. The μ spline df was raised so the fitted median tracks the sharp "
             "early-life peak the exact fractional ages resolve. Solid = fitted median; dashed = model-free "
             "rolling median — they agree across the lifespan.",
             [G / "keystone_growth_grid.png"], []),
            ("1b. The per-segment deviation field — calibrated &amp; discriminative",
             "Every segment carries a deviation z for each feature × region, scored against its own (stage, "
             "age) normal (data/derived/segment_deviation, joinable 1:1 to the segment tables). Panel: "
             "whole-head median segment-z by sleep stage — clean-normal sits ~0 (confirming per-stage "
             "calibration) while abnormal recordings are shifted up (discriminative). This is the measurement "
             "layer the rest of the story stands on.",
             [STY / "s2_segment_deviation.png"], [RES / "s2_segment_deviation.md"]),
            ("1c. Supplementary curve bank (per feature, per stage)",
             "The full stage-resolved normal curves for each feature (whole head); the complete feature × "
             "region bank lives in figures/curves/.",
             [S / "rel_delta__whole_head.png", S / "TAR__whole_head.png", S / "DAR__whole_head.png"], []),
        ],
    ),
    (
        "2", "Detection — a normative-deviation model vs experts vs Morgoth",
        "Does the deviation field DETECT slowing? We build a Morgoth-FREE classifier on it, train it ONLY on "
        "the single-scored REPORT data (never the panel), and test on the OccasionNoise expert panel — a clean "
        "slowing-vs-normal set. Focal and generalized are two independent axes, scored against the panel "
        "majority with each of the 18 experts as an operating point vs the leave-one-out consensus of the "
        "others. Headline = % of experts under our curve.",
        [
            ("2a. One report-trained model vs 18 experts vs Morgoth (OccasionNoise)",
             "A single segment-level model (two heads) trained ONLY on report data — patient-stratified split "
             "balanced over lifespan × focal/gen/both/control, ~16k recordings — applied UNCHANGED to the "
             "panel. GENERALIZED (pooled segment amount z): AUROC 0.946, 78% of experts under ROC — beats most "
             "of the panel AND Morgoth (0.85 / 11%). FOCAL (localized deviation, recording-aggregated): AUROC "
             "0.923, about half the panel under — beats Morgoth (0.91 / 41%). Both axes beat Morgoth from a "
             "model that never saw the panel. Trained on NOISY report labels, it generalizes to the CLEAN "
             "expert consensus far better (0.92–0.95) than its own report-test number (~0.73) implies. "
             "Left = generalized, right = focal. (scripts/53, 54, 55)",
             [STY / "s0d_single_occasion_generalized.png", STY / "s0e_occasion_focal.png"],
             [RES / "s0d_single_model.md"]),
            ("2b. Why the two axes need different read-outs",
             "Focal slowing is a SPATIAL problem — amount of slowing cannot separate focal from generalized, "
             "so the focal head LOCALIZES: per-region deviation z → peak-region z, focality (peak − median "
             "region), asymmetry z, spatial stability, aggregated over the recording. Generalized slowing is "
             "DIFFUSE — a pooled segment amount score captures it. The table traces the design search that "
             "established this (stage-matching unlocks the sleep stages; localization is what cracks focal). "
             "Those are IN-DOMAIN cross-validated numbers on the panel itself — an optimistic upper bound "
             "(focal up to 53%, generalized up to 78% of experts under); the honest external number is §2a.",
             [STY / "s0_occasion_ours_v4_focal.png"], [RES / "s0c_morgoth_free.md"]),
        ],
    ),
]


def img(p: Path):
    if not p.exists():
        return '<div class="todo">figure not yet computed</div>'
    b = base64.b64encode(p.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b}"><figcaption>{p.name}</figcaption></figure>'


def table(p: Path):
    if not p.exists():
        return ""
    if p.suffix == ".md":
        return f'<div class="md">{md_to_html(p.read_text())}</div>'
    try:
        return f'<pre>{pd.read_csv(p).to_markdown(index=False)}</pre>'
    except Exception:
        return f'<pre>{p.read_text()[:4000]}</pre>'


def md_to_html(t: str):
    # tiny md -> html: headers, bold, tables, paragraphs
    import re
    out, rows = [], []
    def flush():
        if not rows:
            return
        head = rows[0].strip("|").split("|")
        body = [r.strip("|").split("|") for r in rows[2:]]
        th = "".join(f"<th>{c.strip()}</th>" for c in head)
        tr = "".join("<tr>" + "".join(f"<td>{c.strip()}</td>" for c in r) + "</tr>" for r in body)
        out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>")
        rows.clear()
    for ln in t.splitlines():
        if ln.strip().startswith("|"):
            rows.append(ln); continue
        flush()
        ln = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", ln)
        ln = re.sub(r"\*(.+?)\*", r"<i>\1</i>", ln)
        if ln.startswith("# "):
            out.append(f"<h4>{ln[2:]}</h4>")
        elif ln.strip():
            out.append(f"<p>{ln}</p>")
    flush()
    return "\n".join(out)


def main():
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    n_seg = len(glob.glob("data/derived/segment_master/eeg_id=*"))
    parts = []
    for num, title, lede, blocks in SECTIONS:
        built = sum(1 for _, _, figs, tabs in blocks
                    if any(Path(f).exists() for f in figs) or any(Path(t).exists() for t in tabs))
        parts.append(f'<section><h2><span class="n">{num}</span>{title} '
                     f'<span class="prog">{built}/{len(blocks)} built</span></h2>'
                     f'<p class="lede">{lede}</p>')
        for sub, cap, figs, tabs in blocks:
            done = any(Path(f).exists() for f in figs) or any(Path(t).exists() for t in tabs)
            badge = '<span class="ok">on this run</span>' if done else '<span class="pend">to build</span>'
            parts.append(f'<div class="block"><h3>{sub} {badge}</h3><p class="cap">{cap}</p>')
            parts += [img(Path(f)) for f in figs]
            parts += [table(Path(t)) for t in tabs]
            parts.append("</div>")
        parts.append("</section>")

    html = f"""<meta charset="utf-8"><title>Slowing — story dashboard</title>
<style>
:root{{color-scheme:dark}} body{{background:#0f1113;color:#dfe3e6;font:15px/1.55 -apple-system,system-ui,sans-serif;margin:0}}
.wrap{{max-width:960px;margin:0 auto;padding:28px 22px 80px}}
h1{{font-size:24px;margin:0 0 4px}} .sub{{color:#8b949e;margin:0 0 26px}}
section{{border-top:2px solid #22262a;margin-top:30px;padding-top:8px}}
h2{{font-size:20px;display:flex;align-items:center;gap:10px}}
h2 .n{{background:#2c7fb8;color:#fff;border-radius:6px;padding:1px 10px;font-size:16px}}
h2 .prog{{margin-left:auto;font-size:12px;color:#8b949e;font-weight:400}}
.lede{{color:#adbac7;margin:2px 0 14px}}
.block{{background:#16191c;border:1px solid #22262a;border-radius:10px;padding:14px 16px;margin:14px 0}}
h3{{font-size:15px;margin:0 0 6px}} .cap{{color:#9aa4ad;font-size:13px;margin:0 0 10px}}
.ok{{background:#1c3b26;color:#7fdca0;font-size:11px;border-radius:5px;padding:1px 7px;margin-left:6px}}
.pend{{background:#3b2c1c;color:#e0b060;font-size:11px;border-radius:5px;padding:1px 7px;margin-left:6px}}
figure{{margin:10px 0}} img{{max-width:100%;border-radius:6px;background:#fff}}
figcaption{{color:#6e7681;font-size:11px;margin-top:3px}}
.todo{{color:#e0b060;background:#241d10;border:1px dashed #4a3c1c;border-radius:6px;padding:16px;text-align:center;font-size:13px}}
.md table,pre{{font-size:12.5px;overflow-x:auto;display:block}} table{{border-collapse:collapse;margin:8px 0}}
th,td{{border:1px solid #2a2f34;padding:3px 8px;text-align:left}} th{{background:#1c2024}}
h4{{margin:6px 0}} pre{{background:#0b0d0f;padding:10px;border-radius:6px}}
</style>
<div class="wrap">
<h1>EEG slowing — a normative-deviation model, benchmarked against experts and Morgoth</h1>
<p class="sub">Foundation → detection (description next): growth curves give every segment a stage/age-matched
deviation z; a Morgoth-free model on that field, trained only on report data, beats the expert panel and
Morgoth on OccasionNoise.
Commit {commit} · {n_seg:,} recordings · generated {time.strftime('%Y-%m-%d %H:%M')}</p>
{''.join(parts)}
</div>"""
    OUT.write_text(html)
    print(f"wrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
