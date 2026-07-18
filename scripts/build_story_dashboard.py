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
        "0", "Can Morgoth detect focal &amp; generalized slowing?",
        "Validate the EEG-level detector against MULTI-RATER expert panels, where the truth is a panel vote, "
        "not one clinician's report. Focal and generalized slowing are scored as SEPARATE binary axes — they "
        "co-occur (report 25% of focal cases are also generalized; occasion raters mark both on 29/100 EEGs), "
        "matching Morgoth's two independent EEG-level sigmoids.",
        [
            ("0a. OccasionNoise — Morgoth vs a Morgoth-FREE classifier vs 18 experts",
             "One ROC+PRC per axis overlaying THREE things: Morgoth's gate probability (purple), our "
             "Morgoth-free spectral+localization classifier (orange, LOO-CV), and the 18 experts as operating "
             "points (grey) scored vs the leave-one-out consensus of the others. Headline = % of experts "
             "under each curve. On these MULTI-SEGMENT recordings the Morgoth-free classifier — which "
             "aggregates intermittency across sleep stages — actually puts MORE experts under than Morgoth "
             "(focal 53% vs 41%, generalized 39% vs 17%). See §0c for how it is built.",
             [STY / "s0_occasion_combined_focal.png", STY / "s0_occasion_combined_generalized.png"],
             [RES / "s0_occasion_combined.md"]),
            ("0b. MoE — Morgoth vs a Morgoth-FREE classifier vs 21 experts (single 15 s clips)",
             "Same three-way overlay on the MoE panel (1,761 clips; `bwestove` excluded). Crucially each MoE "
             "event is a SINGLE 15 s clip — no intermittency or multi-stage aggregation to exploit — so this "
             "is a fair head-to-head on exactly what Morgoth's clip head sees. FINDING: here Morgoth "
             "DOMINATES the single-clip spectral classifier (focal 86% of experts under vs our 24%; "
             "generalized 14% vs 0%). The Morgoth-free edge in §0a came entirely from AGGREGATING across a "
             "full recording; on one clip, the foundation model's per-clip waveform understanding wins. "
             "CAVEATS (see §0d): MoE is a curated MULTI-CATEGORY set, so its slowing 'controls' are other "
             "abnormalities (26% burst suppression), not normals — a harder slowing-vs-other-abnormal task; "
             "and these figures use a band-union label that over-counts generalized. With the canonical "
             "Experts-sheet consensus Morgoth generalized is 0.837 (not 0.734); focal (0.95) is unaffected. "
             "(scripts/45, 52)",
             [STY / "s0_moe_combined_focal.png", STY / "s0_moe_combined_generalized.png"], [RES / "s0_moe_combined.md"]),
            ("0c. Can a Morgoth-FREE classifier beat the experts? (OccasionNoise)",
             "Two detectors built ONLY from spectral/deviation features, no Morgoth, leave-one-out CV, same "
             "expert-operating-point framing. FOCAL is a SPATIAL problem — amount can't separate focal from "
             "generalized, so we LOCALIZE (per-segment region z → peak region, focality = peak−median region, "
             "asymmetry z, spatial stability) over all stages, stage-matched. Result: focal puts **53% of "
             "experts under ROC / 65% under PR — beating most of the panel AND Morgoth (41%)**, with no "
             "Morgoth. GENERALIZED reaches AUROC 0.913 (> Morgoth's 0.867) and more experts under than Morgoth "
             "(39% at W+N1 vs 17%) but not a majority — it's diffuse (no spatial trick) and near the human "
             "ceiling. Left = focal (all-stage, localized); right = generalized (W+N1). (scripts/46-49)",
             [STY / "s0_occasion_ours_v4_focal.png", STY / "s0_occasion_ours_v3_generalized.png"],
             [RES / "s0c_morgoth_free.md"]),
            ("0d. ONE report-trained Morgoth-free model, externally validated on both panels",
             "The honest single-model design: a segment-level model (two heads) trained ONLY on the "
             "single-scored REPORT data (patient-stratified split balanced over lifespan × focal/gen/both/"
             "control, ~16k training recordings), then applied UNCHANGED to OccasionNoise and MoE. Works on a "
             "lone clip (segment output) and aggregates for recordings; the axis-appropriate aggregation is "
             "used (generalized ← segment-score pooling; focal ← recording-level feature aggregation). "
             "HEADLINE on OccasionNoise: our model BEATS MORGOTH on both axes — generalized AUROC 0.946, 78% "
             "of experts under ROC (Morgoth 0.85/11%); focal 0.923, ~half the panel under (Morgoth 0.91/41%). "
             "This CORRECTS §0c's 'at the ceiling' read — that was a 100-recording artifact; with thousands of "
             "report recordings generalized is the win. MoE (corrected Experts-sheet consensus, a harder "
             "slowing-vs-other-abnormal task) stays Morgoth's on the single 15 s clips. Left = generalized, "
             "right = focal. (scripts/53, 54, 55)",
             [STY / "s0d_single_occasion_generalized.png", STY / "s0e_occasion_focal.png"],
             [RES / "s0d_single_model.md"]),
        ],
    ),
    (
        "1", "Detector performance on the report dataset, and segment → EEG recovery",
        "The big single-scorer set (report-derived focal/generalized labels, clean_pair). First the EEG-level "
        "ROC/PRC; then the core question — how to turn Morgoth's per-segment (30 s-context) focal/gen "
        "probabilities into (a) an EEG-level probability p_eeg′ and (b) a SELECTION of which segments carry "
        "focal and/or generalized slowing — done SEPARATELY BY SLEEP STAGE.",
        [
            ("1a. EEG-level ROC / PRC (report labels)",
             "ONLY Morgoth's EEG-level heads (p_focal, p_generalized, and their max = 'any slowing') vs the "
             "report flags (slowing_focal, slowing_gen_pathologic, slowing_positive) on clean_pair "
             "recordings — the single-scorer analogue of §0. No band-power comparator here (the deviation "
             "field is §2).",
             [STY / "s1a_eeg_roc_prc.png"], [RES / "s1a_eeg.md"]),
            ("1b. Recover p_eeg′ from the 30 s-context segment probabilities — by sleep stage",
             "Pool the per-segment probabilities into an EEG-level p_eeg′ by several rules — MAX, p90, "
             "top-5 mean, noisy-OR, MEAN of segments above X, FRACTION above X (X swept) — and score each two "
             "ways: Spearman ρ vs Morgoth's own EEG-level head ('recover'), and AUROC vs the report label "
             "('predict'), stratified by W/N1/N2/N3/REM. FINDING: the top-5 mean best recovers the head and "
             "predicts the report for focal (ρ up to 0.85, AUROC 0.81); generalized favours mean-of-segments-"
             ">-0.25, giving a natural segment-SELECTION threshold X≈0.25. N1/N2 recover best, N3 weakest. "
             "Left panel: AUROC vs report by stage for each rule; right: the selection threshold X. "
             "(scripts/41)",
             [STY / "s1_seg2eeg_focal.png", STY / "s1_seg2eeg_generalized.png"], [RES / "s1_seg2eeg.md"]),
        ],
    ),
    (
        "2", "Growth curves: the stage-wise normative deviation field",
        "Every feature is expressed as a DEVIATION from its age- and stage-matched normal. Each 30 s segment "
        "gets stage-appropriate deviation values, so 'abnormal' always means abnormal FOR THIS AGE AND THIS "
        "SLEEP STAGE. This is the measurement layer the description is built on.",
        [
            ("2a. Normative growth curves per sleep stage (keystone)",
             "GAMLSS/BCT centile fans per (stage × region × feature), μ/σ/skew/kurtosis smooth in log-age, fit "
             "on clean-normal only. μ df raised to 9 so the fitted median tracks the sharp early-life peak the "
             "exact fractional ages resolve. Solid = fitted median, dashed = model-free rolling median.",
             [G / "keystone_growth_grid.png"], []),
            ("2b. Per-segment deviation, by Morgoth's call × stage",
             "Whole-head deviation z (log_delta / TAR / DAR vs the segment's own age+stage normal) grouped by "
             "Morgoth's 4-way EEG-level call (neither / focal-only / gen-only / both) and sleep stage — the "
             "dose-response check that the deviation field tracks what the gate flags.",
             [G / "gated_deviation_by_stage.png"], []),
            ("2c. Supplementary curve bank (per feature, per stage)",
             "The full stage-resolved normal curves for each feature (whole head). The complete feature × "
             "region bank lives in figures/curves/.",
             [S / "rel_delta__whole_head.png", S / "TAR__whole_head.png", S / "DAR__whole_head.png"], []),
            ("2d. The per-segment deviation field (materialized)",
             "Every segment now carries a deviation z per feature × region (7 regions × 6 features), scored "
             "against ITS OWN (sleep-stage, age) normal — data/derived/segment_deviation/, joinable 1:1 to "
             "segment_gate on (eeg_id, segment). Panel: whole-head median segment-z by sleep stage, "
             "clean-normal (sits ~0, confirming per-stage calibration) vs abnormal (shifted positive). This is "
             "the measurement substrate for the description layer. (scripts/43 materialize, scripts/44 "
             "summary)",
             [STY / "s2_segment_deviation.png"], [RES / "s2_segment_deviation.md"]),
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
<h1>EEG slowing — the story, in build order</h1>
<p class="sub">A living scaffold: detect → recover per-segment → describe against growth curves.
Commit {commit} · {n_seg:,} recordings · generated {time.strftime('%Y-%m-%d %H:%M')}</p>
{''.join(parts)}
</div>"""
    OUT.write_text(html)
    print(f"wrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
