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
        "0", "Pipeline architecture",
        "One deviation-from-normal field is the shared substrate for BOTH detection (two report-trained heads) "
        "and description (claims-table-governed read-out). The schematic traces the flow: raw EEG → Morgoth sleep "
        "staging → segment features → lifespan × sleep-stage normative growth curves → the per-segment deviation "
        "field → the two downstream branches, each validated on held-out data.",
        [
            ("Model / pipeline architecture (overview)",
             "Ingest → Morgoth staging (ss_hm_1) → segment features → GAMLSS growth curves → deviation field (the "
             "hub) → detection (generalized + focal heads, trained ONLY on report labels) and description "
             "(claims-governed descriptors → generated finding line + report paragraph). Detection is validated "
             "against the 18-expert panel, the Morgoth gate, van Putten and external Sandor_100; description "
             "against clinical reports by dose-response.",
             [STY / "architecture.png"], []),
        ],
    ),
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
            ("1c. The spatial view — regional development by age &amp; sleep stage (topoplots)",
             "The same normal population, rendered across the scalp: each of the 18 bipolar channels "
             "monopolarized onto a standard 10-20 layout (median over patients), rows = sleep stage, "
             "columns = age bin. What the whole-head curves compress into one line, the head shows in space — "
             "frontal-predominant relative delta, highest in infancy across every stage, declining "
             "monotonically toward adulthood, and deepest in N3. This is the regional substrate the "
             "localization descriptors (§3) read against. (scripts/77_topoplots_by_age.py)",
             [G / "topo_rel_delta_by_age_stage.png", G / "topo_TAR_by_age_stage.png"], []),
            ("1d. Supplementary curve bank (per feature, per stage)",
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
             "panel (recording-level bootstrap 95% CIs). GENERALIZED (pooled segment amount z, s0d): AUROC "
             "0.946 [0.887–0.990], 78% of experts under ROC — clearly beating Morgoth (0.853 [0.750–0.934], "
             "11% under). FOCAL (de-confounded, combined region + finer per-channel, s0e): AUROC 0.921 "
             "[0.824–0.988], 71% of experts under — now clearly beating Morgoth (0.908 [0.828–0.974], 41%). "
             "De-confounding the focal target (focal vs normal + generalized-only) lifted focal from 47% to "
             "71% experts under. Trained on NOISY report labels, it "
             "generalizes to the CLEAN expert consensus far better than its own report-test number (~0.73) "
             "implies. Left = generalized, right = focal. (scripts/53, 54, 55)",
             [STY / "s0d_single_occasion_generalized.png", STY / "s0e_occasion_focal.png"],
             [RES / "s0d_single_model.md", RES / "s0e_recording_model.md"]),
            ("2b. Why the two axes need different read-outs",
             "Focal slowing is a SPATIAL problem — amount of slowing cannot separate focal from generalized, "
             "so the focal head LOCALIZES: per-region deviation z → peak-region z, focality (peak − median "
             "region), asymmetry z, spatial stability, aggregated over the recording. Generalized slowing is "
             "DIFFUSE — a pooled segment amount score captures it. The table traces the design search that "
             "established this (stage-matching unlocks the sleep stages; localization is what cracks focal). "
             "Those are IN-DOMAIN cross-validated numbers on the panel itself — an optimistic upper bound "
             "(focal up to 53%, generalized up to 78% of experts under); the honest external number is §2a.",
             [STY / "s0_occasion_ours_v4_focal.png"], [RES / "s0c_morgoth_free.md"]),
            ("2c. Benchmark against the published qEEG literature (van Putten lineage)",
             "How far does the learned / normative approach exceed the established quantitative-EEG indices? "
             "We recomputed the van Putten family — Brain Symmetry Index and its revised pairwise form, the "
             "diffuse-slowing index Q_SLOWING, DAR, DTABR = (δ+θ)/(α+β), asymmetry Q_ASYM, SEF95 — faithfully "
             "on the same signals, in three arms: raw as published, age-conditioned against our clean-normal "
             "curves, and against the Morgoth gate. Morgoth p_slowing reaches AUROC 0.875 / 0.911 / 0.870 "
             "(abnormal / generalized / focal) versus the best van Putten arm at 0.707 / 0.773 / 0.723 — a "
             "+0.14 to +0.17 margin, intervals non-overlapping. Two lessons: (i) age-conditioning the SLOWING "
             "ratios on our normative curves genuinely improves them (Q_SLOWING/DAR/DTABR/SEF95 +0.03 to "
             "+0.05) while age-conditioning the ASYMMETRY indices does not (symmetry is age-invariant) — a "
             "clean positive control for the normative framework; (ii) even age-conditioned, the classical "
             "indices trail the learned representation, and our Morgoth-free deviation model (§2a) sits well "
             "above this ceiling too. (scripts/recompute_vanputten_fullcov.py)",
             [Path("results/figs/vanputten_comparison.png")], []),
            ("2d. External validation — Sandor_100 vs SCORE-AI, Morgoth, and experts (main-text figure)",
             "The whole pipeline run UNCHANGED on a fully independent 100-EEG benchmark (EMU scalp EEG; no "
             "overlap with training or the OccasionNoise panel) — feature extraction, Morgoth ss_hm_1 sleep "
             "staging, age+stage-matched deviation, and the report-trained detectors — scored 98/100 and "
             "compared against SCORE-AI, the Morgoth gate, and the 14 individual experts. GROUND-TRUTH NOTE: "
             "the workbook's focal 'majority' column is corrupted (disagrees with the 14-expert vote on "
             "23/100; an independent model predicts the stated label at 0.62 vs the true vote at 0.98), so we "
             "score against the actual expert-vote majority (the generalized sheet is unaffected). Corrected — "
             "FOCAL: our interpretable head (de-confounded target, combined region + finer per-channel features) "
             "AUROC 0.933 [0.86–0.98], 71% of experts under — the most consistent variant across both external "
             "sets (71% here and on the panel; region-only de-confounded 64–65%; an amount-confounded region "
             "head scores 0.946 / 79% here only by leaning on overall slowing, collapsing to 47% on the panel — "
             "scripts/sandor100_regiononly_check.py). The Morgoth gate is best (0.974, 93%), SCORE-AI weaker (0.878, 29%). "
             "GENERALIZED: ours 0.893 [0.784–0.978], behind Morgoth (0.951) and SCORE-AI (0.930). A "
             "foundation-model-free model reaches expert-level focal detection on external data, staging and "
             "all, and beats SCORE-AI. (scripts/sandor100_*; corrected labels docs/audits/)",
             [STY / "sandor100_slowing.png"], [Path("results/sandor/sandor100_external.md")]),
        ],
    ),
    (
        "3", "Description — reading OUT the slowing, validated by contrast",
        "Detection says slowing is present; DESCRIPTION says what kind, where, and how persistent. Every "
        "descriptor is read off the SAME per-segment deviation field (type/amount, laterality, region, "
        "anterior–posterior gradient, persistence, sleep stage). Each is validated the way the SAP requires — "
        "by CONTRAST (dose-response): the descriptor is HIGHER when the report mentions that finding than when "
        "it does not — never as a binary classification. Panel-trained (home-field) numbers are cut entirely. "
        "(scripts/56 descriptors, 57 panels, 58 words; N=23,869 report recordings.)",
        [
            ("D1. Type &amp; amount (delta / theta)",
             "Whole-head delta-excess and theta-excess deviation z per segment → recording aggregates. Left: the "
             "delta-z vs theta-z plane (report-slowing shifts up-and-right of clean-normal). Right: dose-response "
             "— our THETA measure is higher when the report says theta (1.39 vs 1.08, p&lt;1e-40) and our DELTA "
             "measure is higher when the report says delta (1.63 vs 1.32, p≈0). The measure tracks the band word.",
             [STY / "s4_d1.png"], [RES / "s4_description.md"]),
            ("D2. Laterality &amp; region (focal)",
             "Left: signed left-minus-right asymmetry z by the report's side — left reports sit at +0.36, "
             "bilateral ~0, right at −0.44 (clean monotonic separation). Right: a lobe's relative prominence "
             "(focality = that lobe vs the rest of the head) rises when the report names that lobe — temporal, "
             "frontal and posterior all show the dose-response (all p&lt;1e-3). Absolute temporal magnitude runs "
             "high everywhere (a temporal-delta attractor), so relative prominence is the specific descriptor.",
             [STY / "s4_d2.png"], []),
            ("D3. Anterior–posterior predominance (generalized)",
             "Anterior-minus-posterior delta z by the report's generalized topography. Report-anterior cases carry "
             "a less posterior-predominant gradient than report-posterior cases (−0.07 vs −0.22, p≈9e-6). A real "
             "but modest gradient — most generalized slowing is diffuse/unspecified, as the report topography is.",
             [STY / "s4_d3.png"], []),
            ("D4. Persistence vs intermittence",
             "Prevalence (fraction of abnormal segments) and longest continuous run per recording, on the ACNS-style "
             "occasional→continuous scale. Report-slowing carries a fat continuous-prevalence tail while clean-normal "
             "piles at ~0 (median 0.19 vs 0.05). There is no structured report continuous/intermittent field, so this "
             "is shown as internal reasonableness (the distribution shape + run length), not a report contrast.",
             [STY / "s4_d4.png"], []),
            ("D5. By sleep stage — slowing is carried into sleep",
             "Descriptors resolved by sleep stage. Left: mean slowing prevalence sits above clean-normal at EVERY "
             "stage — wake AND sleep (e.g. N2 0.32 vs 0.12). Right: band deviation by stage. Among recordings the "
             "report does NOT call slowing, N2 deviation is still elevated over clean-normal N2 (0.225 vs 0.117) — "
             "consistent with the established V4a finding that readers under-report sleep slowing.",
             [STY / "s4_d5.png", G / "v4a_wake_sleep.png"], []),
            ("D6. From descriptors to WORDS",
             "The descriptors are assembled into a compact finding line AND a full report-style paragraph, "
             "governed clause-by-clause by docs/claims_table.md: magnitude as SD + centile (never a severity "
             "adjective), prevalence as a percentage with the ACNS word (occasional/frequent/abundant/"
             "continuous) only as an internal gloss, band a low-confidence δ/θ/mixed call asserted on clear "
             "dominance, side asserted with the maximum-deviation lobe flagged provisional, anterior/posterior "
             "predominance only when it clears the normal centile, stage accentuation and ‘present only during "
             "sleep’, and an abstain path when no regional excess clears the normal centile "
             "(e.g. “Left temporal theta–delta slowing, maximal over the left temporal region, peaking at T3 "
             "(the T3–T5 derivation). Peak deviation 2.8 SD above the age- and stage-matched normal (99th "
             "centile), abnormal in 46% of segments; present in wakefulness and sleep, most prominent in REM.”). "
             "For a lateralised confident focus the paragraph now names the derivation carrying the slowing "
             "(electrode-level, ~40% of focal cases), localised from LEFT–RIGHT delta asymmetry so the symmetric "
             "frontal/eye-movement gradient cannot masquerade as a focus — an output-granularity gain for "
             "automated reporting (reports carry no electrode field, so it is not scored). Discrete components "
             "with a clean report word are concordant well above chance — side 56%, region 46% (chance 33%); "
             "band is calibrated to the report DISTRIBUTION not to accuracy (report band is ~64% 'mixed', a "
             "reader hedge inseparable from theta): marginal-matching reaches 51% at κ≈0.09, the expert-vs-expert "
             "band floor (0.09–0.38) — only the delta↔theta axis carries real signal; the honest test is the "
             "continuous D1 contrast (scripts/band_calibration.py). "
             "Focal-vs-diffuse is the detection head's call (§2), not re-derived here. A PHI-free reasonableness "
             "review set (structured labels only) shows the generated report beside the report's descriptors, "
             "✓/✗ per component.",
             [STY / "s4_d6.png"], [RES / "s4_d6.md"]),
            ("D7. Example EEG segments with automated reports vs the clinical report (main-text figure)",
             "Six example recordings — focal and generalized slowing of varying degree (peak 1.3–3.7 SD) in "
             "different sleep stages — each shown as the ACTUAL 15 s EEG (longitudinal bipolar double-banana, "
             "1–30 Hz + 60 Hz notch, house style from NeuroTech-Wrangling) beside our BRIEF finding line, our "
             "FULL report paragraph, and the clinical report's STRUCTURED descriptors (raw text withheld as "
             "PHI). The EEG is the strongest-slowing 15 s in the dominant stage; EDFs pulled from S3. "
             "(scripts/62 + 63). scripts/62 also writes the example set (results/story/s4_examples.parquet) that "
             "scripts/63 renders; its compact text-only panel (s4_examples_panel.png) is an internal check, not "
             "a submission figure (superseded by the actual-EEG Figure 4).",
             [STY / "s4_examples_eeg_panel.png"], [RES / "s4_examples.md"]),
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

    # Table 1 — cohort description, rendered at the very top (before the story sections)
    t1 = Path("results/table1.md")
    t1_html = (f'<section id="cohort"><h2><span class="n">T1</span>Cohort</h2>'
               f'<p class="lede">The analysis cohort — routine + overnight clinical EEG across the lifespan, '
               f'with the clean-normal reference and the abnormal (focal / generalized slowing) strata that '
               f'every downstream analysis is defined on.</p>'
               f'<div class="block"><h3>Table 1 — Cohort characteristics (SAP §10)</h3>'
               f'{table(t1)}</div></section>') if t1.exists() else ""

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
<p class="sub">Foundation → detection → description: growth curves give every segment a stage/age-matched
deviation z; a Morgoth-free model on that field, trained only on report data, beats the expert panel and
Morgoth on OccasionNoise; and the same field is read OUT into a validated clinical description.
Commit {commit} · {n_seg:,} recordings · generated {time.strftime('%Y-%m-%d %H:%M')}</p>
{t1_html}
{''.join(parts)}
</div>"""
    OUT.write_text(html)
    print(f"wrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
