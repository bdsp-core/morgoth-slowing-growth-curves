"""Comprehensive analysis dashboard = the single source of truth for ALL paper evaluations.

Top: a curatable checklist of every evaluation task the paper needs (status ✓ done / ○ planned).
Then captioned sections: cohort & growth curves, detection, band, localization, stage-specificity,
description quality, robustness. Every figure carries a one-line legend. Self-contained HTML (PNGs
embedded) -> results/analysis_dashboard.html, published as an Artifact.

Run: PYTHONPATH=src python scripts/build_analysis_dashboard.py
"""
from __future__ import annotations
import base64
from pathlib import Path

OUT = Path("results/analysis_dashboard.html")
FIGD = Path("results/figs")
CURVE = Path("figures/curves")            # key features vs age
SCURVE = Path("figures/stage_curves")     # key features vs age, per sleep stage
GROWTH_V2 = Path("figures/growth_v2")      # redesigned central per-stage/sex curves + age topoplots

# --- curatable checklist: every evaluation the paper should include -------------------------------
CHECKLIST = [
    ("Cohort & normative curves", [
        ("done", "Table 1 — cohort characteristics (20,971 recs: 4,916 routine + 16,055 overnight)"),
        ("done", "Growth curves: central per-stage, LMS/BCT, OMOP fractional age (N3 filled, ~15k/stage)"),
        ("done", "Source-appropriate norms (wake=routine, sleep=overnight) — harmonization validated"),
        ("done", "Sex ablation: sex dispensable (ΔAUROC ≤0.002) → sexes pooled"),
        ("done", "BSI (Brain Symmetry Index) added as a feature + age×stage growth curves"),
        ("done", "Feature-extraction validation (our Python vs prior features, r 0.89–0.95)"),
        ("done", "Homologous-asymmetry (delta AND theta) norms vs age — lateralization deviation"),
    ]),
    ("Detection — whether / what", [
        ("done", "Abnormal-vs-normal AUROC, age-dependent (Morgoth)"),
        ("done", "Focal-vs-normal & generalized-vs-normal, age-dependent"),
        ("done", "Our deviation-LR vs Morgoth: agreement (r≈0.69) + distillation R²≈0.46"),
        ("done", "Report-flag agreement (Morgoth/our-LR vs clinical report flags)"),
        ("done", "ROC / PRC / calibration for abnormal detection"),
    ]),
    ("Band — δ / θ / mixed", [
        ("done", "Band agreement vs reports (0.74; default-mixed)"),
        ("todo", "Morphology/aperiodic features to sharpen band (FOOOF) — future"),
    ]),
    ("Localization", [
        ("done", "Lateralization L/R (focal-gated), overall + by band (4 curves), symmetry-augmented"),
        ("done", "Per-region one-vs-normal detection (temporal/frontal/central/parietal/occipital)"),
        ("done", "Focal lobe multi-class (honest; temporal reliable, posterior data-limited)"),
        ("done", "Generalized anterior-vs-posterior predominance (FIRDA/OIRDA)"),
        ("todo", "Region-stratified collection to lift posterior-lobe & θ-focal n"),
    ]),
    ("Sleep-stage specificity", [
        ("done", "Stage-stratified abnormal-vs-normal detection, by age (whole-head deviation)"),
        ("done", "Stage-accentuation: which stage amplifies a case's pathological slowing"),
    ]),
    ("Description quality", [
        ("done", "Report-text agreement (region/side/band), gated per-axis"),
        ("done", "Example generated reports (focal & generalized, stage-aware)"),
    ]),
    ("Robustness / validation", [
        ("done", "Flip-consistency / left-right sign audit (=0)"),
        ("done", "Artifact-rejection validation (plan + local check)"),
        ("todo", "External / second-site validation (future)"),
        ("done", "Cross-site generalization (train S0001 / test S0002): AUROC 0.74-0.85"),
    ]),
    ("Comparison with prior work & empirical findings", [
        ("done", "Head-to-head vs van Putten metrics (DAR, DTABR, BSI) on report agreement"),
        ("done", "Growth curves vs prior literature (Table T2 — John, Petersén, etc.)"),
        ("done", "Empirical: left-predominance of focal slowing, age-dependent (0.65→0.77)"),
        ("weak", "Severity-grading agreement — DONE but WEAK (ρ≈-0.04): severity metric needs work"),
        ("weak", "Prevalence vs report frequency — DONE, weak (ρ≈0.10)"),
    ]),
]

# --- figures with captions, grouped by section ---------------------------------------------------
SECTIONS = [
    ("Figure 1 — Keystone: normative slowing growth curves, by stage & feature",
     "The foundation of the paper. Normative lifespan growth curves of the most discriminating EEG-slowing "
     "features — rel_delta, and the two strongest normal-vs-abnormal discriminators from the regression "
     "analyses, TAR (theta/alpha) and DAR (delta/alpha) — each as a percentile growth chart per sleep "
     "stage. Central (C3/C4), overnight EEG (one consistent pipeline so features are directly comparable), "
     "sexes pooled, GAMLSS/LMS BCT with age-varying skewness, ~15k recordings/stage.",
     [(GROWTH_V2 / "keystone_growth_grid.png",
       "KEYSTONE — rows = sleep stages (W/N1/N2/N3/REM), columns = features (rel_delta AUROC≈0.72, "
       "TAR≈0.82, DAR≈0.79; AUROC = normal-vs-generalized-slowing discrimination from the age/sex-adjusted "
       "deviation analysis). Solid = LMS median, dashed = model-free rolling median (they track closely), "
       "shaded = p3–p97 / p10–p90 / p25–p75. Delta-based features peak in infancy (~6mo) and decline; the "
       "ratio features (TAR/DAR) show sharper peaks and deeper mid-adult troughs — why they discriminate best.")]),
    ("Figure 2 — Vigilance-matched detection (recomputed union data)",
     "Detection of pathological slowing is vigilance-dependent, so the normative reference must be vigilance-"
     "matched. A routine EEG is recorded under active alerting (genuine W/N1); overnight 'wake' is "
     "unconstrained and often drowsy (physiologically high delta), which inflates the normal band and masks "
     "slowing. Positives = routine abnormals; negatives = held-out routine clean-normals; the age-adjusted "
     "whole-head deviation z is scored against three references (routine / overnight / union).",
     [(GROWTH_V2 / "vigilance_matched_detection.png",
       "Normal vs pathologic-generalized slowing, best whole-head feature per stage. The ROUTINE (alert) "
       "reference detects best in W (0.85) and N1 (0.88, the single best stage); the OVERNIGHT (drowsy) "
       "reference degrades detection in every stage (N1 0.88→0.79). Confirms that vigilance-matched norms — "
       "not just age/sex-matched — are needed for detection; recovers the routine-cohort 0.81 and explains "
       "why a naive union-norm score is weak.")]),
    ("Figure 3 — Dose-response: the deviation score tracks clinical severity",
     "The central validity claim: our age-adjusted deviation is not merely correlated with the expert call, "
     "it is a CALIBRATED severity measure. Scored in N1 against the routine (alert) norm.",
     [(GROWTH_V2 / "dose_response.png",
       "Median deviation z rises monotonically across report strata: clean-normal ≈ 0 (well calibrated) → "
       "abnormal with no slowing named +0.4 → abnormal with slowing named +1.4 (Spearman ρ 0.50–0.55, "
       "p≈0; Kruskal p≈0), consistently across log-delta, TAR and DAR. Note the middle stratum: recordings "
       "called abnormal WITHOUT slowing named still deviate (+0.4), the signature of slowing the reader did "
       "not name — the basis of the 'detects what reports miss' hypothesis.")]),
    ("Cohort & normative growth curves",
     "The product itself: how normal EEG features vary with age, per sleep stage, as clinical percentile "
     "growth charts. Built on 20,971 recordings (4,916 routine + 16,055 overnight) with OMOP fractional "
     "ages. GAMLSS/LMS BCT fit with age-varying skewness. Sexes are POOLED (sex changes detection AUROC "
     "by <=0.002 — see the ablation below). Norms are SOURCE-APPROPRIATE: wake from routine EEG, sleep "
     "from overnight EEG, because the two sources are not freely poolable (harmonization panel below).",
     [(GROWTH_V2 / "central_rel_delta_smooth.png",
       "NORMATIVE GROWTH CURVES — relative delta, central (C3/C4), per sleep stage (sexes pooled). Solid = "
       "GAMLSS/LMS median; dashed = model-free rolling median (sliding age-widening window) — they track "
       "closely; bands p3–p97 / p10–p90 / p25–p75. Sleep (N2/N3/REM, ~15k each) from overnight EEG, wake "
       "(W/N1) from routine EEG. N3 shows the textbook infant peak (~0.60 at 6mo–1y) → plateau → adult decline."),
      (GROWTH_V2 / "source_harmonization_rel_delta.png",
       "SOURCE HARMONIZATION — cohort (routine) vs expansion (overnight) rolling medians per stage. Adult "
       "sleep agrees (~0 offset); pediatric sleep + wake diverge (routine sleep is rare/mis-staged). This is "
       "why norms are source-appropriate rather than pooled."),
      (GROWTH_V2 / "central_rel_delta_smooth_pooled.png",
       "For contrast: NAIVE POOLED (both sources per stage). Wider, mixed bands — mixing routine alert-wake "
       "with overnight drowsy-wake, and routine mis-staged sleep with real sleep. Not used for the norm."),
      (GROWTH_V2 / "sex_sensitivity_rel_delta.png",
       "SEX ABLATION — abnormality z under sex-conditional vs sex-pooled norms lie on y=x; ΔAUROC ≤0.002 on "
       "the real TAR/DAR detector. Sex is dispensable → pooled."),
      (GROWTH_V2 / "topo_rel_delta_by_age_stage.png",
       "Regional relative-delta across the head by age bin (columns) & stage (rows), per 10-20 electrode. "
       "Frontal-predominant delta, highest in infancy across stages, declining with age; N3 highest."),
      (CURVE / "log_delta__whole_head.png", "log delta power vs age (whole head), normal percentile curve."),
      (CURVE / "log_theta__whole_head.png", "log theta power vs age (whole head) — paired with delta."),
      (CURVE / "DAR__whole_head.png", "Delta/alpha ratio (DAR) vs age (whole head)."),
      (CURVE / "TAR__whole_head.png", "Theta/alpha ratio (TAR) vs age (whole head)."),
      (CURVE / "BSI__whole_head.png", "Brain Symmetry Index (BSI) vs age (normal) — now one of our features (normal median 0.15 vs focal 0.25)."),
      (SCURVE / "rel_delta__whole_head.png", "Relative delta vs age, split by sleep stage — delta rises with sleep depth (W≈N1<N2<N3)."),
      (SCURVE / "rel_theta__whole_head.png", "Relative theta vs age, per sleep stage."),
      (SCURVE / "DAR__whole_head.png", "DAR vs age, per sleep stage."),
      (SCURVE / "BSI__whole_head.png", "BSI vs age, per sleep stage (normal).")]),
    ("Detection — age-dependent gate discrimination",
     "How well the gate separates abnormal from normal, and where it is weaker (children).",
     [(FIGD / "age_auroc.png", "Morgoth AUROC vs age: abnormal/focal/generalized each vs normal, 95% bootstrap CI. Abnormal 0.79 (peds)→0.95 (elderly); focal 0.97–0.99.")]),
    ("Localization — lateralization (focal, L vs R)",
     "Focal-gated, binary left-vs-right from signed band-matched asymmetry; symmetry-augmented (no left prior).",
     [(FIGD / "lateralization_by_band_roc.png", "L-vs-R ROC overall + by reported band (δ/θ/mixed). Band-matched signed asymmetry; antisymmetric model."),
      (FIGD / "lateralization_roc.png", "L-vs-R ROC (all focal-lateralized), single vs multi-feature.")]),
    ("Localization — region",
     "Two complementary views: per-region detectability vs normal, and the multi-class lobe confusion (honest).",
     [(FIGD / "region_detection_bars.png", "Per-region ONE-vs-NORMAL AUROC: can we see slowing in each region vs normal controls (independent of other regions)? All regions 0.66–0.75."),
      (FIGD / "region_focal_gated.png", "Focal-only multi-class lobe confusion (row-normalized). Temporal reliable (F1 0.64); posterior data-limited — hence the per-region view above."),
      (FIGD / "generalized_ap.png", "Generalized slowing: anterior (FIRDA-like) vs posterior (OIRDA-like) predominance.")]),
    ("Sleep-stage specificity",
     "Does detection hold within each sleep stage, across age? (Secondary/robustness view.)",
     [(FIGD / "age_auroc_by_stage.png", "Abnormal-vs-normal AUROC within each sleep stage, by age, using a simple WHOLE-HEAD slowing-deviation score (staged abnormals + normals). Modest by design — whole-head dilutes focal slowing, so this understates the full regional model; it confirms the stage-normalized deviation separates abnormal within every stage, rising with age.")]),
    ("Robustness & extra evaluations",
     "Cross-site generalization, stage-accentuation, and asymmetry norms (pre-fleet completeness).",
     [(FIGD / "crosssite.png", "Train on one site, test on the other: abnormal-vs-normal AUROC 0.74-0.85 (generalizes, with some site shift)."),
      (FIGD / "stage_accentuation.png", "Among abnormal recordings, which sleep stage accentuates the slowing."),
      (FIGD / "asym_norms.png", "Normal temporal homologous-asymmetry (delta & theta) vs age — norms for the lateralization deviation."),
      (FIGD / "severity_prevalence.png", "Our peak-z / prevalence vs report severity/frequency adjectives. WEAK agreement (ρ≈-0.04 / 0.10) — quantitative severity does not yet match clinical grading; a genuine gap for future work.")]),
    ("Comparison with prior methods (van Putten lineage)",
     "Head-to-head vs the standard published quantitative-slowing metrics, scored against the same report labels.",
     [(FIGD / "vanputten_comparison.png", "DAR, DTABR (Finnigan & van Putten 2013) and BSI (van Putten 2004/2007) vs our age/sex-normed deviations vs Morgoth. Raw metrics ~0.65–0.80; BSI is the best asymmetry baseline (focal 0.80). Our FULL deviation-LR (0.962 abnormal, see table) and Morgoth (0.92–0.99) dominate the single hand-crafted metrics — the value of age/sex/stage normalization + learning.")]),
]

CAP_MD = [("results/v4a_wake_sleep.md",
           "★★ V4a — readers under-report slowing in SLEEP. Established on spindle-verified N2 "
           "(AUROC 0.83–0.86), the one claim of added value over the clinical report."),
          ("results/occasion_model_vs_experts.md",
           "★★ PHASE A/B — our score vs 18 experts on 100 unseen EEGs (external test set). "
           "Generalized AUROC 0.903; two pre-registered predictions FAILED (see P3, P5)."),
          ("results/nested_cv_detection.md",
           "Nested CV: the published per-stage AUROCs survive; optimism ≈ 0.000"),
          ("results/moe_band_vs_ours.md",
           "★ Band determination is near-chance (κ 0.01–0.07): our focal 'agreement' IS the always-delta baseline"),
          ("results/occasion_human_ceiling.md",
           "★ THE HUMAN CEILING — 100 EEGs, 18 experts (OccasionNoise). Slowing is the least reliable "
           "judgment experts make; an expert does not reproduce their own slowing call."),
          ("results/ea_irr_and_recalibration.md",
           "★ Expert-algorithm IRR vs expert-expert IRR, and honest (leave-one-out) recalibration of the gate"),
          ("results/moe_human_ceiling.md",
           "★ MoE — band-resolved expert agreement on slowing (κ 0.09–0.38); the ceiling for our band claim"),
          ("results/detection_pairing_sensitivity.md",
           "Detection survives the borrowed-report bug (all AUROCs within bootstrap CI)"),
          ("results/severity_prevalence_recalibrated.md",
           "Severity vs the reader's adjective — a NULL result (ρ = 0.05, n.s.)"),
          ("results/severity_axis_sweep.md",
           "168-combination sweep: no feature/statistic recovers the severity adjective"),
          ("results/table1.md", "Table 1 — Cohort characteristics (recomputed union data)"),
          ("results/vanputten_comparison.md", "Comparison vs prior methods (van Putten) — table"),
          ("results/lateralization_by_band.md", "Lateralization — band-matched detail"),
          ("results/region_detection.md", "Per-region detection (table)"),
          ("results/region_gated.md", "Region — focal lobe + generalized A/P (tables)"),
          ("results/lr_vs_morgoth.md", "Our features vs Morgoth (agreement)"),
          ("results/report_agreement.md", "Description agreement with clinical reports"),
          ("docs/literature_review.md", "Growth curves vs prior literature (Table T2)")]


def img(p: Path, cap: str) -> str:
    if not p.exists():
        return f'<figure><div class="missing">[missing: {p.name}]</div><figcaption>{cap}</figcaption></figure>'
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b64}"><figcaption>{cap}</figcaption></figure>'


def checklist_html():
    rows = []
    for group, items in CHECKLIST:
        rows.append(f'<div class="ck-group"><h3>{group}</h3>')
        for st, txt in items:
            mark = {"done":"✓","weak":"◐"}.get(st,"○")
            rows.append(f'<div class="ck {st}"><span class="mk">{mark}</span>{txt}</div>')
        rows.append("</div>")
    return "".join(rows)


def section_html(md_path, title):
    p = Path(md_path)
    return f"<h2>{title}</h2><pre>{p.read_text()}</pre>" if p.exists() else ""


def main():
    secs = ""
    for title, note, figs in SECTIONS:
        secs += f'<h2>{title}</h2><div class="note">{note}</div>' + "".join(img(p, c) for p, c in figs)
    tables = "".join(section_html(m, t) for m, t in CAP_MD)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"""<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Morgoth slowing — evaluations</title>
<style>
 :root{{--bg:#0e1420;--panel:#161f2f;--line:#233047;--ink:#e8eef7;--dim:#8798b3;--accent:#35e0c4;--todo:#f5a623}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 ui-sans-serif,-apple-system,system-ui,sans-serif}}
 .wrap{{max-width:860px;margin:0 auto;padding:22px 16px 60px}}
 h1{{font-size:1.25rem;margin:0 0 4px}} .sub{{color:var(--dim);font-size:.85rem;margin-bottom:18px}}
 h2{{font-size:.95rem;text-transform:uppercase;letter-spacing:.05em;color:var(--accent);margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}}
 h3{{font-size:.85rem;margin:12px 0 6px;color:var(--ink)}}
 figure{{margin:0 0 18px}} img{{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}}
 figcaption{{color:var(--dim);font-size:.8rem;margin-top:6px}}
 .missing{{color:var(--todo);font-size:.8rem;padding:20px;border:1px dashed var(--line);border-radius:10px}}
 pre{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;overflow:auto;font-size:.76rem;white-space:pre-wrap}}
 .note{{color:var(--dim);font-size:.9rem;margin:2px 0 12px}}
 .checklist{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;columns:2;column-gap:26px}}
 @media(max-width:640px){{.checklist{{columns:1}}}}
 .ck-group{{break-inside:avoid;margin-bottom:12px}} .ck-group h3{{color:var(--accent);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}}
 .ck{{font-size:.82rem;padding:2px 0;display:flex;gap:8px}} .ck .mk{{font-weight:700}}
 .ck.done .mk{{color:var(--accent)}} .ck.todo .mk{{color:var(--todo)}} .ck.todo{{color:var(--dim)}} .ck.weak .mk{{color:var(--todo)}}
</style>
<div class="wrap">
  <h1>Morgoth slowing — evaluation inventory</h1>
  <div class="sub">Every evaluation the paper needs, with status + captioned results. Curate the checklist:
    <b>✓ = done (shown below)</b>; <b>○ = not yet done / pending</b>. Companion to the ingestion burndown.</div>
  <h2>Paper evaluations — checklist (curate this)</h2>
  <div class="checklist">{checklist_html()}</div>
  {secs}
  <h2>Tables &amp; detail</h2>
  {tables}
</div>
""")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
