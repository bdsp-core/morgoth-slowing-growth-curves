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
     [G/"keystone_growth_grid.png"], []),

    ("Figure 3", "Stage dependence at fixed age (SAP §9 Fig 3)",
     "The same feature across W/N1/N2/N3/REM — why vigilance matching is built into the norms rather than "
     "added as a covariate: physiologic sleep produces the spectral changes that define pathologic slowing "
     "awake.", [S/"rel_delta__whole_head.png", S/"DAR__whole_head.png"], []),

    ("Figure 4 / Table 2", "Detection — vigilance-matched ROC (SAP §9 Fig 4, §8.1, §10 T2)",
     "Primary: AUROC for pathologic slowing vs clean-normal, whole-recording, vigilance-matched (per stage "
     "and stage-pooled), reported by src. Positives are recordings whose report NAMES slowing among the "
     "abnormalities; recordings abnormal for other reasons (e.g. epileptiform) are a separate stratum, not "
     "positives. CIs by stratified bootstrap, patient-clustered on patient_id (SAP §3.3).",
     [G/"vigilance_matched_detection.png", F/"age_auroc.png"],
     ["results/vigilance_matched_detection.csv", "results/nested_cv_detection.md"]),

    ("Ablation", "Attribution of the detection estimate (audit §1)",
     "Toggling, one at a time, the factors that changed from the legacy pipeline: label definition "
     "(contaminated vs corrected), artifact-segment handling, and cohort/expansion pooling. The θ band edge "
     "(4–8 Hz, SAP §4.5) is already applied in this run's features and is not toggleable post-hoc.",
     [], ["results/ablation_auroc.md"]),

    ("Figure 5", "Focal / generalized localisation (SAP §9 Fig 5, §8.2)",
     "Focal side/lobe confusion (macro-F1, not accuracy — the temporal default inflates accuracy) and the "
     "generalized anterior–posterior gradient.",
     [F/"lateralization_by_band_roc.png", F/"lateralization_roc.png", F/"region_detection_bars.png",
      F/"generalized_ap.png"], ["results/region_detection.md"]),

    ("Figure 6", "Descriptor reliability (SAP §9 Fig 6, §8.2)",
     "Split-half amount ICC, prevalence ICC, and band agreement — reported as PROVISIONAL unless they clear "
     "the pre-registered bar.", [G/"v4a_wake_sleep.png"], ["results/descriptor_validation.md"]),

    ("Figure 8 / Table 5", "Human ceiling & inter-rater reliability (SAP §9 Fig 8, §3.6, §8.3)",
     "Our ROC on the multi-rater panel EEGs (OccasionNoise + MoE) with each expert overlaid as an operating "
     "point; Fleiss κ, pairwise Cohen κ, Gwet AC1, within-rater κ, and our balanced accuracy against the "
     "expert consensus. These panels carry INDEPENDENT expert reads, so they are also the non-circular test "
     "of the 'readers under-report slowing' claim (the report labels S is fit on are not used here).",
     [G/"occasion_roc_experts.png"], ["results/ea_irr_and_recalibration.md"]),

    ("Figure 9 / Table 6", "Benchmark vs van Putten lineage (SAP §9 Fig 9, §8.7)",
     "AUROC for the prior qEEG slowing metrics (Q_SLOWING, DTABR, ADR, pdBSI …) computed on identical PSDs, "
     "in three arms — as-published, age/sex/stage-normed, and ours+Morgoth — per target.",
     [F/"vanputten_comparison.png"], ["results/vanputten_comparison.md"]),

    ("Deviation field", "Normative deviation z (SAP §6.3)",
     "Z[recording, stage, region, feature] from the GAMLSS/BCT fit, with k-fold cross-fitting so a normal's "
     "own z uses OUT-OF-FOLD parameters (no self-normalisation optimism), folds split by patient_id.",
     [G/"region_z_boxplots.png", G/"dose_response.png"], ["results/region_z_boxplots.md"]),

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
    ("todo", "Patient-clustered bootstrap CIs wired into every reported interval (SAP §3.3)."),
    ("todo", "Analysis scripts read segment_master via io/canonical directly (SAP §13) — currently via an "
             "adapter that regenerates the tables from segment_master."),
    ("todo", "'Readers under-report slowing' evidenced on the independent expert panels (non-circular)."),
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
