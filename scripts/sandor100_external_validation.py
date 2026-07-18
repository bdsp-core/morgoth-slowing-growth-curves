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
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100")
MR = SB_DIR / "Morgoth_results"
SM = Path("data/derived/segment_master")
OUT = Path("results/sandor"); FIG = Path("figures/story")
AMT, FOC = m54.AMT, m54.FOC
FOC_R = [f"{c}_{s}" for c in m55.FOC0 for s in ("mean", "p90", "max", "prev")] + ["age"]
K = m54.K; C_OURS, C_MORG, C_SAI = "#e6550d", "#6a3d9a", "#2c7fb8"


def train_heads():
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    tr = S[(S.dataset == "report") & (S.split == "train")]
    gen = m54.train_mil(tr, AMT, "y_gen")                        # segment-pooling generalized (marquee)
    Rtr = m55.aggregate(S[S.dataset == "report"]); Rtr = Rtr[Rtr.split == "train"]
    foc_med = Rtr[FOC_R].median()
    foc = m54.Head().fit(Rtr[FOC_R].fillna(foc_med).values, Rtr.y_focal.astype(int).values)  # recording focal (marquee)
    amt_med = tr[AMT].median()
    return gen, foc, foc_med, amt_med


def score_sandor(gen, foc, foc_med, amt_med):
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age_of = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
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
    """axis in {focal, generalized}; merge our score with the pre-joined SCORE-AI/Morgoth/expert file."""
    d = pd.read_excel(MR / mr_file)
    d["key"] = d.file_name.astype(str).str.strip()
    m = scores.merge(d, on="key", how="inner")
    expert_cols = [c for c in d.columns if c.startswith("expert_")]
    wide = m.set_index("key")[expert_cols].apply(pd.to_numeric, errors="coerce")
    # GROUND TRUTH = the actual expert-vote majority. The workbook's `majority` column is CORRUPTED for the
    # focal sheet (disagrees with the 14-expert vote on 23/100; an independent model predicts the vote at
    # 0.976 vs the stated column at 0.62). Verified 2026-07-18; the generalized sheet is unaffected.
    y = (wide.mean(axis=1).values >= 0.5).astype(int)
    pts = m46.expert_points(wide)
    models = [("ours", m[f"ours_{axis}"].values, C_OURS), ("Morgoth", m["M_pred"].values, C_MORG),
              ("SCORE-AI", m["S_pred"].values, C_SAI)]
    ax.plot([0, 1], [0, 1], "--", color="#ccc", lw=1); res = []
    for name, s, c in models:
        ok = np.isfinite(s) & np.isfinite(y)
        cur = m54.panel_curve(None, y[ok], s[ok], pts, c, name)
        lo, hi = m54.boot_ci(y[ok], s[ok])
        ax.plot(cur["fpr"], cur["tpr"], color=c, lw=2.4,
                label=f"{name} (AUROC {cur['auc']:.2f} [{lo:.2f}–{hi:.2f}], {cur['ur']:.0f}% under)")
        res.append((name, cur["auc"], lo, hi, cur["ur"], cur["ap"]))
    for r, p in pts.items():
        ax.plot(p["fpr"], p["tpr"], "o", ms=5, mfc="#999", mec="k", mew=.3, alpha=.75)
    ax.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
    ax.set_xlabel("1 − specificity"); ax.set_ylabel("sensitivity"); ax.set_xlim(-.02, 1.02); ax.set_ylim(-.02, 1.02)
    ttl = "FOCAL slowing (nonepifoc)" if axis == "focal" else "GENERALIZED slowing (nonepidiffuse)"
    ax.set_title(f"{ttl} — n={len(m)}, {int(y.sum())} pos", fontsize=10.5)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    return res, len(m), int(y.sum()), len(pts)


def main():
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    n_built = len(list(SM.glob("eeg_id=SB_*")))
    print(f"scoring {n_built} built Sandor recordings ...", flush=True)
    gen, foc, foc_med, amt_med = train_heads()
    scores = score_sandor(gen, foc, foc_med, amt_med)
    print(f"scored {len(scores)} recordings", flush=True)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(12, 5))
    rf, nf, pf, ne = eval_axis(scores, "focal", "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx", a0)
    rg, ng, pg, _ = eval_axis(scores, "generalized", "GenSlowingOutput_Morgoth_ScoreAI_experts.xlsx", a1)
    fig.suptitle(f"Sandor_100 external validation — our models vs SCORE-AI vs Morgoth vs {ne} experts", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(FIG / "sandor100_slowing.png", dpi=150); plt.close(fig)

    md = ["# SB / Sandor_100 — external validation: our models vs SCORE-AI vs Morgoth vs experts\n",
          f"Full pipeline (extraction → **Morgoth ss_hm_1 sleep staging** → age+stage-matched deviation → our "
          f"report-trained detectors) run UNCHANGED on {len(scores)}/100 external EMU EEGs. Ground truth = "
          f"expert majority; SCORE-AI (`S_pred`) and the Morgoth gate (`M_pred`) and the individual experts "
          f"are pre-joined in Sandor_100/Morgoth_results/. Recording-level bootstrap 95% CIs; % experts under "
          f"our ROC curve.\n",
          "| axis | model | AUROC [95% CI] | % experts under ROC | AP |", "|---|---|---|---|---|"]
    for axis, res, npos in [("focal", rf, pf), ("generalized", rg, pg)]:
        for name, au, lo, hi, ur, ap in res:
            md.append(f"| {axis} ({npos}+) | {name} | {au:.3f} [{lo:.3f}, {hi:.3f}] | {ur:.0f}% | {ap:.3f} |")
    (OUT / "sandor100_external.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote results/sandor/sandor100_external.md + figures/story/sandor100_slowing.png")


if __name__ == "__main__":
    main()
