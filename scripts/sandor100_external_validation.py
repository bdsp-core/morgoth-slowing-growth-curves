"""SB / Sandor_100 external validation — PHASE 2: score our detectors on the 100 recordings and compare with
SCORE-AI, the Morgoth gate, and the individual human experts (experts-under-the-curve), for FOCAL slowing
(nonepifoc) and GENERALIZED/diffuse slowing (nonepidiffuse).

Requires Phase 1 (scripts/sandor100_stage_extract.py) to have written segment_master/eeg_id=SB_NNN.
Our models (trained ONLY on report-train, applied UNCHANGED):
  generalized = segment-pooling amount head (scripts/54, top-5 pool)   [marquee 0.946 on OccasionNoise]
  focal       = recording-aggregation localization head (scripts/55)   [marquee 0.923 on OccasionNoise]
Ground truth = expert majority; SCORE-AI = S_pred, Morgoth gate = M_pred, experts = expert_* (all pre-joined
in Sandor_100/Morgoth_results/{Focal,Gen}SlowingOutput_Morgoth_ScoreAI_experts.xlsx).

Writes results/sandor/sandor100_external.md + figures/story/sandor100_{focal,generalized}.png
Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/sandor100_external_validation.py
"""
from __future__ import annotations
import os
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette
from sklearn.metrics import roc_auc_score

m53 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m53", "scripts/53_single_model_features.py"))
importlib.util.spec_from_file_location("m53", "scripts/53_single_model_features.py").loader.exec_module(m53)
m54 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py"))
importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py").loader.exec_module(m54)
m55 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py"))
importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py").loader.exec_module(m55)
m66 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py"))
importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py").loader.exec_module(m66)
m46 = m54.m49.m46
m53.SEG_CAP = 10**9                                              # use ALL segments when scoring the 100 EDFs

# SANDOR_DIR must be settable: this defaulted to one developer's Box CloudStorage mount, so the SAI-100
# external validation could not be reproduced anywhere else. The default is the historical path purely
# so the old machine keeps working; everyone else exports SANDOR_DIR.
def _resolve_sandor_dir():
    """Locate the SAI-100 source, or say exactly how to point at it.

    This used to default to one developer's Box CloudStorage mount, so every other machine died with a
    FileNotFoundError deep inside pandas naming a stranger's home directory. The data is DUA-governed and
    cannot be committed, so a default is still needed -- but it must be a path that can plausibly exist
    here, and when it does not it must fail with an instruction rather than a stack trace.
    """
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("SANDOR_DIR")
    if env:
        return env
    for c in (_P.home() / "Desktop/GithubRepos/Sandor_100_local",
              _P.home() / "Sandor_100",
              _P("data/external/Sandor_100"),
              _P("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/"
                 "ChenXiSun/Morgoth1/Datasets/Sandor_100")):    # historical, so the original machine works
        if _P(c).is_dir():
            return str(c)
    raise SystemExit(
        "SAI-100 source not found. It is DUA-governed and not committed, so set SANDOR_DIR to the "
        "directory\nholding validation_study_excel_export.xlsx and Morgoth_results/, e.g.\n"
        "  export SANDOR_DIR=~/Desktop/GithubRepos/Sandor_100_local\n"
        "or run scripts/reproduce_story.sh, which skips this step cleanly when SANDOR_DIR is unset.")


# The published, de-identified panel (scripts/export_sai100_panel.py). When present this is the source, so
# Figure 3 rebuilds from git + S3 like every other display item; the Box/DUA workbook is only the fallback
# for regenerating the export itself. See REPRODUCE.md.
PANEL = Path("data/derived/sai100_panel.parquet")


def _panel(axis: str) -> pd.DataFrame:
    """The SAI-100 panel for one axis: expert votes + SCORE-AI + gate, published or from the workbook."""
    if PANEL.exists():
        d = pd.read_parquet(PANEL)
        return d[d.axis == axis].drop(columns=["axis"]).reset_index(drop=True)
    return pd.read_excel(Path(os.environ.get("SANDOR_DIR") or _resolve_sandor_dir())
                         / "Morgoth_results" / AXIS_FILE[axis])


def _ages() -> dict:
    """Study pseudonym -> age. Ages above 89 are binned to 90 in the published table (Safe Harbor)."""
    if PANEL.exists():
        d = pd.read_parquet(PANEL).drop_duplicates("file_name")
        return {str(k).strip(): float(v) for k, v in zip(d.file_name, d.age_years)}
    demo = pd.read_excel(Path(os.environ.get("SANDOR_DIR") or _resolve_sandor_dir())
                         / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    return {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}


AXIS_FILE = {"focal": "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx",
             "generalized": "GenSlowingOutput_Morgoth_ScoreAI_experts.xlsx"}

# No module-level SANDOR_DIR lookup. SB_DIR and MR were resolved here at import and never used again, and
# _resolve_sandor_dir() exits when the DUA source is absent -- so on a machine with only git + S3 the script
# died on import, before it could read the published panel it actually needs. It only worked where a historical
# Box path happened to exist. The two readers that do need the source (_panel/_ages fallbacks) resolve it
# themselves, and only when the published panel is missing.
SM = Path("data/derived/segment_master")
OUT = Path("results/sandor"); FIG = Path("figures/story")
AMT, FOC = m54.AMT, m54.FOC
FOC_R = [f"{c}_{s}" for c in m55.FOC0 for s in ("mean", "p90", "max", "prev")] + ["age"]
from morgoth_slowing.viz.palette import OURS, MORGOTH, SCORE_AI
K = m54.K; C_OURS, C_MORG, C_SAI = OURS, MORGOTH, SCORE_AI


def train_heads():
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    tr = S[(S.dataset == "report") & (S.split == "train")]
    gen = m54.train_mil(tr, AMT, "y_gen")                        # segment-pooling generalized (marquee)
    Rtr = m55.aggregate(S[S.dataset == "report"]); Rtr = Rtr[Rtr.split == "train"]
    foc_med = Rtr[FOC_R].median()
    foc = m54.Head().fit(Rtr[FOC_R].fillna(foc_med).values, Rtr.y_focal.astype(int).values)  # recording focal (marquee)
    amt_med = tr[AMT].median()
    return gen, foc, foc_med, amt_med


def _require_all_partitions():
    """Refuse to score a partial SAI-100 set.

    score_sandor() scores whatever SB_* partitions happen to exist, and the panel join is an inner join, so a
    machine missing two partitions silently reports n=98 under a manuscript that says n=100 -- which is exactly
    what happened when SB_060 and SB_086 were built on one machine and never published. Every labelled panel
    recording must have its feature partition, or the run stops and names what to build.
    """
    want = {f"SB_{int(k[2:]):03d}" for k in _panel("focal").file_name.astype(str).str.strip().unique()}
    have = {q.name.split("=", 1)[1] for q in SM.glob("eeg_id=SB_*") if (q / "part.parquet").exists()}
    missing = sorted(want - have)
    if missing:
        raise SystemExit(
            f"SAI-100: {len(missing)} of {len(want)} labelled recordings have no segment_master partition: "
            f"{missing}.\nScoring the rest would silently change n. Build them with\n"
            f"  SANDOR_DIR=<dir with EDF/ and validation_study_excel_export.xlsx> "
            f"python3 scripts/sandor100_stage_extract.py\n"
            f"then publish data/derived/segment_master/eeg_id=SB_*/ and segment_summary/ to S3.")


def score_sandor(gen, foc, foc_med, amt_med):
    _require_all_partitions()
    age_of = _ages()
    rows = []
    for out in sorted(SM.glob("eeg_id=SB_*")):
        eid = out.name.split("=")[1]; n = int(eid.split("_")[1]); key = f"ID{n:03d}"
        sf = m53.seg_feats(eid, age_of.get(key, np.nan))
        if sf is None or sf.empty:
            continue
        gs = gen.score(sf[AMT].fillna(amt_med).values)          # per-segment generalized score
        gen_eeg = float(np.sort(gs)[::-1][:K].mean())           # top-K pool
        sf["eeg_id"] = eid; sf["dataset"] = "sandor"; sf["split"] = "test"; sf["y_focal"] = 0; sf["y_gen"] = 0
        R = m55.aggregate(sf)
        foc_eeg = float(foc.score(R[FOC_R].fillna(foc_med).values)[0])
        rows.append({"eid": eid, "key": key, "ours_generalized": gen_eeg, "ours_focal": foc_eeg})
    df = pd.DataFrame(rows)
    # FOCAL: use the production de-confounded combined head (scripts/66) instead of the amount-confounded one
    fs = m66.focal_score(list(zip(df.eid, [age_of.get(k, np.nan) for k in df.key])))
    df["ours_focal"] = df.eid.map(fs).fillna(df.ours_focal)
    return df


def eval_axis(scores, axis, mr_file, ax):
    """axis in {focal, generalized}; merge our score with the pre-joined SCORE-AI/Morgoth/expert panel."""
    d = _panel(axis)
    d["key"] = d.file_name.astype(str).str.strip()
    m = scores.merge(d, on="key", how="inner")
    expert_cols = [c for c in d.columns if c.startswith("expert_")]
    wide = m.set_index("key")[expert_cols].apply(pd.to_numeric, errors="coerce")
    # GROUND TRUTH = the expert-vote majority, recomputed from the individual expert columns.
    #
    # NOT the `majority` column of FocalSlowingOutput_*.xlsx. That column reproduces he_con_intictepifoc --
    # the focal INTERICTAL EPILEPTIFORM consensus -- on 100/100 recordings, while the expert_* columns beside
    # it carry focal NON-epileptiform (slowing) ratings. Scoring against it would compare a slowing detector
    # to an epileptiform reference; it disagrees with the true focal-slowing majority on 23/100 (10 one way,
    # 13 the other).
    #
    # This was previously described here, and in the manuscript, as the SOURCE workbook being corrupted. That
    # was wrong and is corrected (Beniczky, 2026-08-31): validation_study_excel_export.xlsx is internally
    # consistent -- its he_con_nonepifoc agrees with the majority of the individual nonepifoc ratings on
    # 100/100. The inconsistency is in the derived FocalSlowingOutput workbook only. The recomputation below
    # agrees with the true nonepifoc majority on 100/100 (26 positives), so results are unaffected.
    y = (wide.mean(axis=1).values >= 0.5).astype(int)
    pts = m46.expert_points(wide)
    models = [("LENS", m[f"ours_{axis}"].values, C_OURS), ("Morgoth", m["M_pred"].values, C_MORG),
              ("SCORE-AI", m["S_pred"].values, C_SAI)]
    ax.plot([0, 1], [0, 1], "--", color="#ccc", lw=1); res = []
    for name, s, c in models:
        ok = np.isfinite(s) & np.isfinite(y)
        cur = m54.panel_curve(None, y[ok], s[ok], pts, c, name)
        lo, hi = m54.boot_ci(y[ok], s[ok])
        ax.plot(cur["fpr"], cur["tpr"], color=c, lw=2.4,
                label=f"{name}  {cur['auc']:.2f} [{lo:.2f}\u2013{hi:.2f}]\n"
                          f"{round(cur['ur']*len(pts)/100)}/{len(pts)} experts under")
        res.append((name, cur["auc"], lo, hi, cur["ur"], cur["ap"]))
    for r, p in pts.items():
        ax.plot(p["fpr"], p["tpr"], "o", ms=5, mfc="#999", mec="k", mew=.3, alpha=.75)
    ax.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
    palette.style_roc(ax)                      # shared with Figures 2, S3 and S7
    # At page width the two titles collide and the long legend labels overrun the y-axis, so the title wraps
    # onto two lines and the legend is sized to sit inside its own axes.
    ttl = "FOCAL slowing" if axis == "focal" else "GENERALIZED slowing"
    ax.set_title(f"{ttl}\nn={len(m)}, {int(y.sum())} positive", fontsize=palette.TITLE_PT)
    ax.legend(frameon=False, fontsize=palette.LEGEND_PT, loc="lower right", handlelength=1.0,
              borderaxespad=0.2, labelspacing=0.35, handletextpad=0.5)
    # PAIRED bootstrap of the AUROC DIFFERENCE (review comments 8/34-36). Comparative claims -- "outperforms
    # SCORE-AI on focal" -- rested on point estimates alone. Resampling recordings ONCE per replicate and
    # scoring both models on the SAME resample keeps the comparison paired, so the interval reflects the
    # difference rather than the sum of two independent uncertainties.
    ok_all = np.isfinite(y)
    for nm, s_, _c in models:
        ok_all &= np.isfinite(s_)
    yv = y[ok_all]
    sc = {nm: s_[ok_all] for nm, s_, _c in models}
    rng = np.random.default_rng(0)
    idx = [rng.choice(len(yv), len(yv), replace=True) for _ in range(4000)]
    idx = [j for j in idx if 0 < yv[j].sum() < len(j)]
    diffs = {}
    for other in ("SCORE-AI", "Morgoth"):
        d = np.array([roc_auc_score(yv[j], sc["LENS"][j]) - roc_auc_score(yv[j], sc[other][j]) for j in idx])
        lo_, hi_ = np.percentile(d, [2.5, 97.5])
        # two-sided bootstrap p: how often the difference crosses zero
        pv = 2 * min((d <= 0).mean(), (d >= 0).mean())
        diffs[other] = (float(d.mean()), float(lo_), float(hi_), float(max(pv, 1 / len(d))))
    return res, len(m), int(y.sum()), len(pts), diffs


def main():
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    n_built = len(list(SM.glob("eeg_id=SB_*")))
    print(f"scoring {n_built} built Sandor recordings ...", flush=True)
    gen, foc, foc_med, amt_med = train_heads()
    scores = score_sandor(gen, foc, foc_med, amt_med)
    print(f"scored {len(scores)} recordings", flush=True)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.1, 2.96))
    rf, nf, pf, ne, df = eval_axis(scores, "focal", "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx", a0)
    rg, ng, pg, _, dg = eval_axis(scores, "generalized", "GenSlowingOutput_Morgoth_ScoreAI_experts.xlsx", a1)
    # Title in the figure caption (Clinical Neurophysiology); panel letters so the two axes are citable.
    for k, a in enumerate((a0, a1)):
        palette.panel_letter(a, k)
    fig.tight_layout()
    fig.savefig(FIG / "sandor100_slowing.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    md = ["# SAI-100 (SCORE-AI validation set) — external validation: LENS vs SCORE-AI vs Morgoth vs experts\n",
          f"Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → the "
          f"report-trained LENS detectors) run UNCHANGED on {len(scores)}/100 external EMU EEGs. Ground truth = "
          f"expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts "
          f"are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under "
          f"the LENS ROC curve.\n",
          "| axis | model | AUROC [95% CI] | % experts under ROC | AP |", "|---|---|---|---|---|"]
    for axis, res, npos in [("focal", rf, pf), ("generalized", rg, pg)]:
        for name, au, lo, hi, ur, ap in res:
            md.append(f"| {axis} ({npos}+) | {name} | {au:.3f} [{lo:.3f}, {hi:.3f}] | {ur:.0f}% | {ap:.3f} |")
    md += ["", "## Paired AUROC differences (LENS minus comparator)", "",
           "Same 4,000 recording-level resamples for both models in each row, so the interval is on the "
           "DIFFERENCE. A comparative claim is only supported where the interval excludes 0.", "",
           "| axis | comparison | ΔAUROC [95% CI] | p | supported? |", "|---|---|---|---|---|"]
    for axis, dd in [("focal", df), ("generalized", dg)]:
        for other, (mu, lo, hi, pv) in dd.items():
            sup = "**yes**" if (lo > 0 or hi < 0) else "no (interval includes 0)"
            md.append(f"| {axis} | LENS − {other} | {mu:+.3f} [{lo:+.3f}, {hi:+.3f}] | {pv:.3g} | {sup} |")
    (OUT / "sandor100_external.md").write_text("\n".join(md) + "\n")
    print("\n".join(md)); print("\nwrote results/sandor/sandor100_external.md + figures/story/sandor100_slowing.png")


if __name__ == "__main__":
    main()
