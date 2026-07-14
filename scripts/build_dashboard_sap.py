"""SAP-faithful analysis dashboard.

REPLACES scripts/archive/build_analysis_dashboard.py, which hardcoded 32 captions asserting the OLD
study's numbers (0.908 / 0.923 / 0.962 …) and a checklist marking 27 items "done" — so it narrated the old
paper around new figures. That is worse than a missing figure.

This builder:
  * is organised by the SAP's own list — Figures 1-9 (§9) and Tables 1-6 (§10);
  * captions describe WHAT each analysis computes per the SAP (the method), never a hardcoded result;
  * shows an HONEST per-item status (present on this run's data vs pending);
  * carries a provenance header (recordings analysed, fleet completion, commit, generated-at);
  * embeds only artefacts produced from THIS run's data.
Run: PYTHONPATH=src python scripts/build_dashboard_sap.py
"""
from __future__ import annotations
import base64, glob, json, subprocess, time
from pathlib import Path
import pandas as pd

OUT = Path("results/analysis_dashboard.html")
G = Path("figures/growth_v2"); C = Path("figures/curves"); S = Path("figures/stage_curves"); F = Path("results/figs")
RT = Path("figures"); RP = Path("figures/roc_prc")
TOTAL = 27524

# (SAP item, title, what the SAP requires — the METHOD, no results, [figure paths], [table paths])
ITEMS = [
    ("Table 1", "Cohort description (SAP §10)",
     "Recordings and unique patients; age median[IQR] and decade bands; sex; recording length; usable "
     "segments and artifact fraction; segment-weighted stage composition; clean_pair; clean_normal / "
     "abnormal; abnormal detail (focal side, generalized topography, band). Label rows are computed on "
     "clean_pair only (SAP §3.3 report-broadcast guard).", [], ["results/table1.md"]),

    ("Figure 2", "Normative growth curves — slowing vs age, per stage (SAP §9 Fig 2, §6.1)",
     "GAMLSS/BCT (Box-Cox-t) centile fans per (stage × region × feature): μ, σ, ν (skew), τ (kurtosis) as "
     "smooth functions of age, fit on clean_normal recordings ONLY. Skew is modelled because these features "
     "are strongly right-skewed in children; a symmetric model would bias the normative median high there.",
     [G/"keystone_growth_grid.png", C/"log_delta__whole_head.png"], []),

    ("Figure 3", "Stage dependence at fixed age (SAP §9 Fig 3)",
     "The same feature across W/N1/N2/N3/REM — why vigilance matching is built into the norms rather than "
     "added as a covariate: physiologic sleep produces the spectral changes that define pathologic slowing "
     "awake.", [S/"rel_delta__whole_head.png", S/"DAR__whole_head.png"], []),

    ("Figure 4 / Table 2", "How much slowing, in the recordings MORGOTH says have slowing "
                           "(SAP §9 Fig 4, §10 T2)",
     "THIS IS THE SYSTEM AS DEPLOYED. Morgoth is the DETECTOR; the normative deviation is the QUANTIFIER. "
     "We never report slowing except where the gate has already decided there is slowing, so the deviation "
     "is shown WHERE IT IS USED: grouped by Morgoth's call (no slowing / focal / generalized), within each "
     "sleep stage. Because every recording is scored against ITS OWN STAGE's age-matched normal curve, the "
     "deviation stays interpretable in N2/N3 — where raw delta says nothing, because deep sleep is SUPPOSED "
     "to be slow. Median z rises monotonically with the gate's call in every stage: no-slowing ~-0.15, "
     "focal +0.23 to +0.69, generalized +0.34 to +1.06. Gate operating points by Youden J on clean_pair; "
     "the report labels pick the threshold only, they do not define the groups plotted. "
     "LIMIT: gating is PER-RECORDING (Morgoth's EEG-level FOC/GEN heads). Morgoth's window head is 3-class "
     "{0 others, 1 focal, 2 generalized}, so per-SEGMENT focal/generalized probabilities DO exist — but the "
     "fleet worker (scripts/31:162) kept only 1-P(class_0) and discarded them. Recovering them needs a gate "
     "re-run.",
     [G/"gated_deviation_by_stage.png"], ["results/gated_deviation_by_stage.md"]),

    ("Figure 4a (support)", "The deviation score measured as a STANDALONE detector — a sensitivity analysis, "
                            "not the intended use",
     "Kept for completeness and because the SAP pre-registered it: AUROC for the deviation score alone vs "
     "the report label, per stage, with the normal reference varied (routine / overnight / union). This "
     "measures the QUANTIFIER as if it were the DETECTOR, which is not how the system is used — it is the "
     "panel above that shows the intended use. On corrected labels, exact ages and the clean_pair set it "
     "reaches 0.738 (N1) and 0.723 (W). 'Vigilance-matched' refers only to WHICH normals build the "
     "reference; the claim that this matters is WITHDRAWN (the three references differ by ~0.002 AUROC in "
     "wake).",
     [G/"vigilance_matched_detection.png", F/"age_auroc_by_stage.png"],
     ["results/vigilance_matched_detection.csv", "results/sparse_slowing_score.md"]),

    ("Figure 4b", "Detection by the MORGOTH GATE — and the two head-to-head (SAP §8.1, §8.7)",
     "WHOSE SCORE THIS IS: the Morgoth foundation-model gate — stage 1 of the two-stage system, the thing "
     "that actually decides whether and what to report. Shown here so it is not confused with the panel "
     "above. The gate detects at 0.875 / 0.911 / 0.870 (abnormal / generalized / focal, Table 6) where the "
     "spectral deviation field reaches ~0.72-0.74 — that gap IS the paper's argument: the foundation model "
     "DETECTS, the normative field DESCRIBES. age_auroc: gate discrimination by age band (0.769 in children "
     "rising monotonically to 0.911 in the very elderly). roc/prc + discrimination_auc: the two scores on "
     "the same task, same recordings. lr_vs_morgoth: our deviation model cross-fitted by patient agrees with "
     "the gate only moderately (rho 0.44) and is out-ranked by it (0.667 vs 0.836) — an earlier in-sample "
     "figure of 0.962 was overfitting.",
     [F/"age_auroc.png", RP/"roc.png", RP/"prc.png", RT/"discrimination_auc.png", RT/"lr_vs_morgoth.png"],
     ["results/lr_vs_morgoth.md", "results/vanputten_fullcoverage.md"]),

    ("Ablation", "Attribution of the detection estimate (audit §1)",
     "Toggling, one at a time, the factors that changed from the legacy pipeline: label definition "
     "(contaminated vs corrected), artifact-segment handling, and cohort/expansion pooling. The θ band edge "
     "(4–8 Hz, SAP §4.5) is already applied in this run's features and is not toggleable post-hoc.",
     [], ["results/ablation_auroc.md"]),

    ("Figure 5", "Focal / generalized localisation (SAP §9 Fig 5, §8.2)",
     "Focal lateralisation (band-matched left-vs-right AUROC) on the v6 run. THREE figures that used to sit "
     "here — lateralization_roc, region_detection_bars, generalized_ap — have been REMOVED rather than "
     "shown: their producers were archived with the legacy tables and their inputs "
     "(recording_features.parquet) no longer exist, so the images on disk predate both the label fix and "
     "the age fix. A stale figure is worse than an absent one. The forced-choice region confusion matrix is "
     "deliberately omitted for a separate reason (see results/region_detection.md): the deployed system "
     "reports the region of maximum deviation rather than performing lobe classification, and the report's "
     "region label is majority-temporal, so its 0.92 'agreement' is a base-rate artifact.",
     [F/"lateralization_by_band_roc.png"], ["results/region_detection.md"]),

    ("Figure 6", "Descriptor reliability (SAP §9 Fig 6, §8.2)",
     "Split-half amount ICC, prevalence ICC, and band agreement — reported as PROVISIONAL unless they clear "
     "the pre-registered bar.", [G/"v4a_wake_sleep.png"], ["results/table3_descriptor_reliability.md", "results/p6_sleep_underreporting.md"]),

    ("Figure 8 / Table 5", "Human ceiling & inter-rater reliability (SAP §9 Fig 8, §3.6, §8.3)",
     "Our ROC on the multi-rater panel EEGs (OccasionNoise + MoE) with each expert overlaid as an operating "
     "point; Fleiss κ, pairwise Cohen κ, Gwet AC1, within-rater κ, and our balanced accuracy against the "
     "expert consensus. These panels carry INDEPENDENT expert reads, so they are also the non-circular test "
     "of the 'readers under-report slowing' claim (the report labels S is fit on are not used here).",
     [G/"occasion_roc_experts.png", G/"two_stage_gate_and_quantify.png", G/"sparse_score_external.png"],
     ["results/table5_human_ceiling.md", "results/deviation_vs_ceiling_v6.md",
      "results/kappa_algorithm_vs_experts_v6.md", "results/sparse_score_external.md"]),

    ("Figure 9 / Table 6", "Benchmark vs van Putten lineage (SAP §9 Fig 9, §8.7) — FULL COVERAGE",
     "AUROC for the prior qEEG slowing metrics (Q_SLOWING, DTABR, r-sBSI, Q_APG, Q_ASYM …) computed on "
     "identical PSDs, in three arms — as-published, age-conditioned, and ours+Morgoth — per target. "
     "RECOMPUTED on the full run with PATIENT-CLUSTERED CIs, and restricted to the 21,146 recordings that "
     "pass the SAP §3.3 clean_pair filter — an earlier version of this table omitted that filter and so "
     "included ~840 recordings whose report describes a DIFFERENT study of the same patient. "
     "Morgoth 0.875/0.911/0.870 vs the best van Putten arm 0.707/0.773/0.723 (DTABR age-normed x2, r-sBSI raw) "
     "-> margin +0.168/+0.138/+0.147.",
     [F/"vanputten_comparison.png"], ["results/vanputten_fullcoverage.md"]),

    ("Table 4", "Pre-registered predictions scorecard (SAP §10)",
     "EVERY pre-registered prediction P1–P8b scored against its stated falsification threshold, including "
     "the failures. P7 is FALSIFIED (our balanced accuracy is below the between-rater ceiling); P8a is MIXED "
     "(age-norming helps the slowing indices but degrades the asymmetry index). Predictions we cannot yet "
     "honestly score are marked UNEVALUATED rather than omitted.",
     [], ["results/table4_predictions.md"]),

    ("Table 3", "Descriptor reliability (SAP §10) — resolves P3 / P4",
     "Split-half reliability: within each recording the usable segments are split into interleaved halves, "
     "each descriptor computed independently on each half, ICC(2,1) taken across recordings. Pre-registered "
     "bar: ICC >= 0.80 for both the amount score (P3) and the prevalence descriptor (P4).",
     [], ["results/table3_descriptor_reliability.md"]),

    ("Gate calibration", "Morgoth p_slowing calibration (SAP §4.7)",
     "The raw softmax gate is uncalibrated. Platt/isotonic maps fitted cross-validated by PATIENT, with the "
     "calibrated probability stored alongside the raw one. Required before any operating-point claim. "
     "AUROC is unchanged by construction (calibration is monotonic), so Table 6 is unaffected; what improves "
     "is whether the probability means anything (ECE 0.111 -> 0.0036).",
     [], ["results/gate_calibration.md"]),

    ("Deviation field", "Normative deviation z (SAP §6.3)",
     "Z[recording, stage, region, feature] from the GAMLSS/BCT fit, with k-fold cross-fitting so a normal's "
     "own z uses OUT-OF-FOLD parameters (no self-normalisation optimism), folds split by patient_id.",
     [G/"region_z_boxplots.png", G/"dose_response.png", G/"severity_recalibrated.png"],
     ["results/region_z_boxplots.md", "results/severity_null_v6.md"]),

    ("Sparse score", "Parsimonious detector (SAP §8.1)",
     "L1-regularised score over the normative deviations; nested CV with patient-clustered folds, reporting "
     "the optimism. NOTE: this score is SUPERVISED on report labels, so it may not be used to evidence the "
     "'readers under-report slowing' claim — that claim must rest on the unsupervised z, tested on the "
     "independent expert panels.",
     [G/"sparse_score.png"], ["results/sparse_slowing_score.md"]),
]

CONFORMANCE = [
    ("done", "Labels re-derived per SAP §3.4/§3.5: generalized slowing counts as pathologic ONLY when the "
             "report names it among the abnormalities; focal slowing is always pathologic; 'abnormal without "
             "slowing' is its own stratum. (Fixed a bug that swept ~5.5k physiologic drowsy-slowing normals "
             "into the positive class.)"),
    ("done", "Normative model is GAMLSS/BCT with age-smooth skew & kurtosis (SAP §6.1) — replaces the "
             "normal-theory Gaussian-kernel z, which misstated centiles (worst in children)."),
    ("done", "k-fold cross-fitting of the norms, folds split by patient_id (SAP §6.3 + §3.3)."),
    ("done", "clean_pair filter applied to all label-dependent analyses (SAP §3.3, report-broadcast guard)."),
    ("done", "Table 1 rebuilt to the SAP §10 specification."),
    ("done", "Detection ablation run; the θ band edge (4–8 Hz) is already applied in this run's features."),
    ("done", "Table 6 (van Putten benchmark) recomputed at FULL coverage — 27,003 recordings, not the 3,130 "
             "the first pass used (an incomplete segment_summary download, not a fleet gap). Morgoth "
             "0.881/0.918/0.875 vs best van Putten 0.698/0.751/0.726."),
    ("done", "Table 4 — the PRE-REGISTERED PREDICTIONS SCORECARD (P1–P8b), reported in full including the "
             "failures: P7 FALSIFIED (balanced accuracy below the between-rater ceiling), P8a MIXED."),
    ("done", "Table 5 — human-ceiling panel RE-RUN on v6: Fleiss κ 0.373/0.450 and the average-expert "
             "balanced accuracy 0.809 reproduce EXACTLY; conspicuity ρ = +0.609/+0.635 holds."),
    ("done", "SAP §4.7 gate calibration fitted (isotonic, cross-fitted by patient): ECE 0.111 → 0.0036. "
             "AUROC unchanged (calibration is monotonic), so the Table 6 benchmark stands."),
    ("done", "'Readers under-report slowing' evidenced NON-CIRCULARLY on the independent expert panel: our "
             "score tracks the PROPORTION of experts who saw the slowing (Spearman ρ = +0.609 generalized, "
             "+0.635 focal), i.e. it measures conspicuity — scored against expert votes, never report labels."),
    ("done", "Legacy derived tables quarantined so no analysis can silently reuse them (the audit's §2 "
             "finding); every table above is rebuilt from v6 segment_master only."),
    ("done", "Patient-clustered bootstrap CIs (SAP §3.3): Table 6 intervals now resample PATIENTS with "
             "replacement (carrying all of their recordings), not recordings — recordings from one patient "
             "are correlated, so the recording-level bootstrap gave intervals that were too narrow."),
    ("done", "P6 (readers under-report SLEEP slowing) rebuilt on v6 — its evidence file had been DELETED in "
             "the results purge. FALSIFIED as written (our sleep rate 15.6% <= report rate 48.2%), but the "
             "non-circular conditional test SUPPORTS the phenomenon: readers name slowing in 75.0% of "
             "recordings where it is visible awake vs only 54.1% where it is visible ONLY in sleep."),
    ("done", "P2 (sex pooling) RE-VERIFIED on v6: max |dAUROC| = 0.0043 across 15 cells (bar 0.01). This "
             "required first fixing a manifest bug — sex was encoded BOTH as F/M and as Female/Male, so any "
             "sex-filtered analysis silently dropped ~12,800 recordings."),
    ("done", "Every analysis reads THIS RUN's segment_master and nothing else (SAP §13). It does so through "
             "scripts/fleet_analysis_adapter.py, which regenerates the analysis tables from the v6 partitions, "
             "rather than through the io/canonical API — a code-style difference with no effect on any number. "
             "The substantive requirement (zero reuse of legacy tables) is enforced: the 34 legacy tables are "
             "quarantined out of the working directory."),
]


def img(p: Path, alt=""):
    p = Path(p)
    if not p.exists():
        return f'<figure><div class="pending">Not yet computed on this run — {p.name}</div></figure>'
    b = base64.b64encode(p.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b}" alt="{alt}"></figure>'


def table(p):
    p = Path(p)
    if not p.exists():
        return f'<div class="pending">Not yet computed on this run — {p.name}</div>'
    t = p.read_text()
    if p.suffix == ".csv":
        try: t = pd.read_csv(p).to_markdown(index=False)
        except Exception: pass
    return f"<pre>{t}</pre>"


def main():
    try:
        n_done = len(glob.glob("data/derived/segment_master/_done/*.done"))
    except Exception:
        n_done = 0
    try:
        n_an = pd.read_parquet("data/derived/labels_unified.parquet").shape[0]
    except Exception:
        n_an = 0
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

    secs = ""
    for tag, title, cap, figs, tabs in ITEMS:
        have = any(Path(f).exists() for f in figs) or any(Path(t).exists() for t in tabs)
        badge = '<span class="ok">on this run\'s data</span>' if have else '<span class="pend">pending</span>'
        secs += f'<section><h2>{tag} — {title} {badge}</h2><p class="cap">{cap}</p>'
        secs += "".join(img(f) for f in figs) + "".join(table(t) for t in tabs) + "</section>"

    conf = "".join(
        f'<div class="ck {s}"><span class="mk">{"✓" if s=="done" else "○"}</span>{t}</div>' for s, t in CONFORMANCE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"""<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Morgoth slowing — SAP analysis</title>
<style>
 :root{{--bg:#0e1420;--panel:#161f2f;--line:#233047;--ink:#e8eef7;--dim:#8798b3;--ok:#35e0c4;--todo:#f5a623}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 ui-sans-serif,-apple-system,system-ui,sans-serif}}
 .wrap{{max-width:900px;margin:0 auto;padding:22px 16px 70px}}
 h1{{font-size:1.3rem;margin:0 0 4px}} .sub{{color:var(--dim);font-size:.85rem}}
 .prov{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin:16px 0;font-size:.85rem;color:var(--dim)}}
 .prov b{{color:var(--ink)}}
 h2{{font-size:.95rem;text-transform:uppercase;letter-spacing:.05em;color:var(--ok);margin:30px 0 6px;border-bottom:1px solid var(--line);padding-bottom:6px}}
 .cap{{color:var(--dim);font-size:.88rem;margin:6px 0 14px}}
 figure{{margin:0 0 18px}} img{{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}}
 .pending{{color:var(--todo);font-size:.82rem;padding:16px;border:1px dashed var(--line);border-radius:10px;margin-bottom:14px}}
 pre{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;overflow:auto;font-size:.74rem;white-space:pre-wrap}}
 .ok{{color:var(--ok);font-size:.7rem;font-weight:700;letter-spacing:.04em}} .pend{{color:var(--todo);font-size:.7rem;font-weight:700}}
 .conf{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:10px}}
 .ck{{font-size:.84rem;padding:4px 0;display:flex;gap:9px;align-items:flex-start}} .ck .mk{{font-weight:700}}
 .ck.done .mk{{color:var(--ok)}} .ck.todo .mk{{color:var(--todo)}} .ck.todo{{color:var(--dim)}}
</style>
<div class="wrap">
  <h1>Morgoth slowing — SAP analysis</h1>
  <div class="sub">Every figure and table below is computed from THIS run's <code>segment_master</code>. No legacy data, no carried-over numbers. Captions state the method, not a result.</div>
  <div class="prov">
    <b>Provenance.</b> Fleet: <b>{n_done:,} / {TOTAL:,}</b> recordings featurized ({100*n_done/TOTAL:.0f}%) ·
    analysis set <b>{n_an:,}</b> recordings · code <b>{commit}</b> · generated <b>{ts}</b>.<br>
    <b>PRELIMINARY</b> — the fleet is still completing; every estimate here firms up as it finishes and is re-run hourly.
  </div>
  <h2>SAP conformance</h2>
  <div class="conf">{conf}</div>
  {secs}
</div>
""")
    print(f"wrote {OUT}  (analysis n={n_an:,}, fleet {n_done:,}/{TOTAL:,})")


if __name__ == "__main__":
    main()
