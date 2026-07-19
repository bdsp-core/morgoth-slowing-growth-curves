"""Figure S7 — the FAIR van Putten benchmark: hand-crafted qEEG indices vs LENS vs the Morgoth gate on the
CLEAN ON-100 expert panel (expert-majority labels), for FOCAL and GENERALIZED slowing.

The report-cohort benchmark (scripts/recompute_vanputten_fullcov.py, §3.5 numbers / Table S1) scores everything
against NOISY single-report labels, where LENS is label-noise-capped (~0.73) and looks no better than the
indices. That is unfair to LENS: on the CLEAN expert panel the report-label ceiling is removed and LENS jumps
to 0.92-0.95. So the fair three-way comparison is on the panel — and it is what this figure shows.

LENS scoring is the SAME production code path as Figure 2/3 (generalized = scripts/54 MIL top-5 pool; focal =
scripts/66 de-confounded combined head), so the LENS AUROCs here equal the Figure 2 numbers by construction.
van Putten arm = the BEST index per axis, recomputed on the panel: generalized = strongest whole-head slowing
ratio (DAR/TAR/DTR/low-freq/rel-delta); focal = strongest interhemispheric asymmetry (|L-R|/(L+R) over the
temporal + parasagittal regions, per band) — the r-sBSI analog. Morgoth = occasion_morgoth_preds.

Writes figures/figs/vanputten_panel_s7.png + results/vanputten_panel_s7.md
Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/vanputten_panel_s7.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (shared Tufte style)
from morgoth_slowing.viz.palette import OURS, MORGOTH, VANPUTTEN
from sklearn.metrics import roc_auc_score

m54 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py"))
importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py").loader.exec_module(m54)
m66 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py"))
importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py").loader.exec_module(m66)
m46 = m54.m49.m46

FIG = Path("figures/figs"); RES = Path("results")
GEN_RATIOS = ["DAR", "TAR", "DTR", "low_freq_rel", "rel_delta"]     # whole-head diffuse-slowing ratios
ASYM_BANDS = ["rel_delta", "rel_theta"]                             # interhemispheric asymmetry (BSI analog)


def lens_panel_scores():
    """LENS generalized (54 MIL top-5) + focal (66) on the ON-100 panel — identical to Figure 2's code path."""
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    tr = S[(S.dataset == "report") & (S.split == "train")]
    gen_head = m54.train_mil(tr, m54.AMT, "y_gen")
    S["lens_gen"] = gen_head.score(S[m54.AMT].fillna(S[m54.AMT].median()).values)
    occ = S[S.dataset == "occasion"].copy()
    gen = occ.groupby("eeg_id")["lens_gen"].apply(lambda v: np.sort(v.values)[::-1][:m54.K].mean())
    age_of = occ.groupby("eeg_id")["age"].first()
    foc = m66.focal_score([(e, float(age_of[e])) for e in occ.eeg_id.unique()])
    return {"generalized": gen, "focal": foc.reindex(gen.index)}


def _wmean(g, col):
    w = g["n_seg"].to_numpy(float); v = g[col].to_numpy(float)
    m = np.isfinite(v) & np.isfinite(w) & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan


def vanputten_panel_indices():
    """Best whole-head slowing ratio (generalized) and best interhemispheric asymmetry (focal), per recording."""
    OF = pd.read_parquet("data/derived/occasion_features.parquet")
    OF["eeg_id"] = ["ON_" + str(int(f)) for f in OF.fid]
    wh = OF[OF.region == "whole_head"]
    gen = {c: wh.groupby("eeg_id").apply(lambda g, c=c: _wmean(g, c)) for c in GEN_RATIOS}

    def region_band(region, col):
        return OF[OF.region == region].groupby("eeg_id").apply(lambda g, c=col: _wmean(g, c))
    foc = {}
    for c in ASYM_BANDS:
        Lt, Rt = region_band("L_temporal", c), region_band("R_temporal", c)
        Lp, Rp = region_band("L_parasagittal", c), region_band("R_parasagittal", c)
        at = (Lt - Rt).abs() / (Lt + Rt); ap = (Lp - Rp).abs() / (Lp + Rp)
        foc[f"asym_{c}"] = pd.concat([at, ap], axis=1).mean(axis=1)
    return gen, foc


def _oriented_auc(y, s):
    ok = np.isfinite(s) & np.isfinite(y)
    if ok.sum() < 3 or len(np.unique(y[ok])) < 2:
        return np.nan, s
    a = roc_auc_score(y[ok], s[ok])
    return (a, s) if a >= 0.5 else (1 - a, -s)          # auto-orient: larger index -> more abnormal


def best_index(cands: dict, y, idx):
    best, bs, ba = None, None, -1
    for name, ser in cands.items():
        s = ser.reindex(idx).to_numpy(float)
        a, so = _oriented_auc(y, s)
        if np.isfinite(a) and a > ba:
            best, bs, ba = name, so, a
    return best, bs, ba


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    lens = lens_panel_scores()
    em = m54.expert_and_morgoth("occasion")               # {axis: (wide_votes, morgoth)}, indexed ON_{fid}
    vp_gen, vp_foc = vanputten_panel_indices()
    vp_by_axis = {"generalized": vp_gen, "focal": vp_foc}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5)); md = ["# Figure S7 — van Putten vs LENS vs Morgoth on the "
        "CLEAN ON-100 expert panel (fair benchmark; expert-majority labels)\n",
        "LENS = production code path (gen: scripts/54 MIL top-5; focal: scripts/66), identical to Figure 2. "
        "van Putten = best index per axis recomputed on the panel. Recording-level bootstrap 95% CIs.\n",
        "| axis | method | AUROC [95% CI] | % experts under ROC |", "|---|---|---|---|"]
    for ax, axis in zip(axes, ["focal", "generalized"]):
        wide, morg = em[axis]
        idx = wide.index
        y_all = (wide.mean(axis=1).to_numpy() >= 0.5).astype(int)
        vp_name, vp_s, _ = best_index(vp_by_axis[axis], y_all, idx)
        raw = {"vp": vp_s, "lens": lens[axis].reindex(idx).to_numpy(float), "morg": morg.reindex(idx).to_numpy(float)}
        # evaluate ALL methods on the SAME recordings (finite for every method + label) — a fair common denominator
        common = np.isfinite(y_all)
        for s in raw.values():
            common &= np.isfinite(s)
        y = y_all[common]
        pts = m46.expert_points(wide.loc[common])
        methods = [(f"best van Putten index ({vp_name})", raw["vp"][common], VANPUTTEN),
                   ("LENS", raw["lens"][common], OURS),
                   ("Morgoth", raw["morg"][common], MORGOTH)]
        ax.plot([0, 1], [0, 1], "--", color="#ccc", lw=1)
        for name, s, c in methods:
            cur = m54.panel_curve(None, y, s, pts, c, name)
            lo, hi = m54.boot_ci(y, s)
            short = name.split(" (")[0]
            ax.plot(cur["fpr"], cur["tpr"], color=c, lw=2.4,
                    label=f"{short} (AUROC {cur['auc']:.2f} [{lo:.2f}–{hi:.2f}], {cur['ur']:.0f}% under)")
            md.append(f"| {axis} | {name} | {cur['auc']:.3f} [{lo:.3f}, {hi:.3f}] | {cur['ur']:.0f}% |")
        idx = idx[common]
        for p in pts.values():
            ax.plot(p["fpr"], p["tpr"], "o", ms=5, mfc="#999", mec="k", mew=.3, alpha=.75)
        ax.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
        ax.set_xlabel("1 − specificity"); ax.set_ylabel("sensitivity"); ax.set_xlim(-.02, 1.02); ax.set_ylim(-.02, 1.02)
        ax.set_title(f"{axis.upper()} slowing — n={len(idx)}, {int(y.sum())} pos", fontsize=11)
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("ON-100 panel (clean expert labels) — hand-crafted van Putten indices vs LENS vs Morgoth gate", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(FIG / "vanputten_panel_s7.png", dpi=150); plt.close(fig)
    (RES / "vanputten_panel_s7.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/figs/vanputten_panel_s7.png + results/vanputten_panel_s7.md")


if __name__ == "__main__":
    main()
