#!/usr/bin/env python3
"""ONE Morgoth-free model, recording-level aggregation (#1b) — trained on report, tested on all three sets.

Same single model idea as scripts/54, but instead of pooling segment SCORES (top-5 mean), it uses the RICH
recording-level aggregation that made the occasion-trained focal detector strong: each per-segment feature is
aggregated over the recording as {mean, p90, max, prevalence(z>1.5)}. A single clip (MoE) degrades gracefully
(mean=p90=max=the value), so the SAME model works segment-wise and recording-wise. Trained on report-train
(patient-split), so it has far more data than the 100-recording occasion model.

  generalized head <- aggregated amount features
  focal head       <- aggregated localization features (peak / focality / asymmetry)

Evaluated on report-test (report labels) and OccasionNoise / MoE (expert labels; ours vs Morgoth vs experts).
MoE ground truth uses the CANONICAL Experts-sheet consensus (not the band-union), with a burst-suppression-
excluded control variant, since MoE slowing-negatives are other abnormalities.

Writes results/story/s0e_recording_model.md + figures/story/s0e_{occasion,moe}_{focal,generalized}.png
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/55_recording_model.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

m54 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py"))
importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py").loader.exec_module(m54)
m46 = m54.m49.m46; m45 = m54.m45
AMT0 = [f"amt_{ft}" for ft in m54.FEATS]
FOC0 = [f"{p}_{ft}" for ft in m54.FOC_F for p in ("peak", "foc", "asym")]
FIG = Path("figures/story"); RES = Path("results/story")
C_MORG, C_OURS = "#6a3d9a", "#e6550d"
MOE_XL = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
          "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/Morgoth_test_list_MoE.xlsx")


def aggregate(S):
    """per recording: {mean,p90,max,prev} of each per-segment feature."""
    def f(g):
        d = {"age": g.age.iloc[0]}
        for c in AMT0 + FOC0:
            v = g[c].to_numpy(); v = v[np.isfinite(v)]
            if len(v):
                d[f"{c}_mean"] = v.mean(); d[f"{c}_p90"] = np.quantile(v, .9)
                d[f"{c}_max"] = v.max(); d[f"{c}_prev"] = float((v > 1.5).mean())
        return pd.Series(d)
    R = S.groupby("eeg_id").apply(f)
    meta = S.drop_duplicates("eeg_id").set_index("eeg_id")[["dataset", "split", "y_focal", "y_gen"]]
    return R.join(meta)


def moe_expert_consensus():
    E = pd.read_excel(MOE_XL, sheet_name="Experts"); E["eeg_id"] = "MOE_" + E.file_name.astype(str)
    return E.set_index("eeg_id")


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    R = aggregate(S)
    AMT = [f"{c}_{s}" for c in AMT0 for s in ("mean", "p90", "max", "prev")] + ["age"]
    FOC = [f"{c}_{s}" for c in FOC0 for s in ("mean", "p90", "max", "prev")] + ["age"]
    for c in AMT + FOC:
        if c not in R.columns:
            R[c] = np.nan
    tr = R[(R.dataset == "report") & (R.split == "train")]
    heads = {}
    for tag, cols, ylab in [("focal", FOC, "y_focal"), ("generalized", AMT, "y_gen")]:
        Xtr = tr[cols].fillna(tr[cols].median()); ytr = tr[ylab].astype(int)
        heads[tag] = m54.Head().fit(Xtr.values, ytr.values)
        R[f"score_{tag}"] = heads[tag].score(R[cols].fillna(tr[cols].median()).values)
    # FOCAL: override with the production de-confounded combined head (scripts/66) for the panel recordings
    on = [(e, R.loc[e, "age"]) for e in R.index if str(e).startswith("ON_")]
    if on:
        _s = importlib.util.spec_from_file_location("m66", "scripts/66_focal_combined.py")   # lazy: avoid import cycle
        m66 = importlib.util.module_from_spec(_s); _s.loader.exec_module(m66)
        fs = m66.focal_score(on); R.loc[fs.index, "score_focal"] = fs.values

    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    E = moe_expert_consensus()
    md = ["# ONE recording-level Morgoth-free model (aggregated features) — report-trained, tested on all\n",
          "Per-segment features aggregated per recording as {mean,p90,max,prev}; degrades to a single clip. "
          "Trained on report-train. MoE truth = canonical Experts-sheet consensus.\n",
          "| test set | axis | model | AUROC | AP | % under ROC | % under PR |", "|---|---|---|---|---|---|---|"]

    # report-test
    rt = R[(R.dataset == "report") & (R.split == "test")]
    for tag, ylab in [("focal", "y_focal"), ("generalized", "y_gen")]:
        y = rt[ylab].astype(int)
        md.append(f"| report-test | {tag} | ours | {roc_auc_score(y, rt[f'score_{tag}']):.3f} | "
                  f"{average_precision_score(y, rt[f'score_{tag}']):.3f} | – | – |")

    # occasion (expert votes); MoE cut from the story
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    for ds in ["occasion"]:
        sub = R[R.dataset == ("moe" if ds.startswith("moe") else ds)]
        for tag, mx, hc, ecol in [("focal", "FN", "p_focal", "foc_slowing"), ("generalized", "GN", "p_generalized", "gen_slowing")]:
            if ds == "occasion":
                wide = V.dropna(subset=[f"r1.{mx}"]).pivot_table(index="fid", columns="rater", values=f"r1.{mx}")
                wide.index = [f"ON_{int(i)}" for i in wide.index]
                keep = wide.index.intersection(sub.index)
                wide = wide.loc[keep]; y = (wide.mean(axis=1) >= 0.5).astype(int); pts = m46.expert_points(wide)
                morg = None; idx = keep
            else:
                keep = E.index.intersection(sub.index)
                yy = (E.loc[keep, ecol] >= 0.5).astype(int)
                if ds == "moe_noBS":                       # drop burst-suppression from the NEGATIVES
                    drop = (yy == 0) & (E.loc[keep, "bs"] >= 0.5)
                    keep = keep[~drop]; yy = yy.loc[keep]
                y = yy; pts = {}; idx = keep; morg = head.loc[keep, hc]
            s_ours = sub.loc[idx, f"score_{tag}"]
            ok = np.isfinite(s_ours.values) & np.isfinite(y.values)
            au = roc_auc_score(y.values[ok], s_ours.values[ok]); ap = average_precision_score(y.values[ok], s_ours.values[ok])
            lo, hi = m54.boot_ci(y.values[ok], s_ours.values[ok])       # recording-level bootstrap 95% CI
            ur = up = np.nan
            if pts:
                fpr, tpr, _ = roc_curve(y.values[ok], s_ours.values[ok]); prec, rec, _ = precision_recall_curve(y.values[ok], s_ours.values[ok])
                cur = m54.panel_curve(None, y.values[ok], s_ours.values[ok], pts, C_OURS, "ours"); ur, up = cur["ur"], cur["up"]
                # figure: ours vs Morgoth vs experts (occasion has Morgoth via occasion_morgoth_preds)
                MP = pd.read_parquet("data/derived/occasion_morgoth_preds.parquet")
                mm = MP[MP.axis == mx].set_index("fid").M_pred; mm.index = [f"ON_{int(i)}" for i in mm.index]
                cm = m54.panel_curve(None, y.values[ok], mm.reindex(idx).values[ok], pts, C_MORG, "Morgoth")
                fig, (a0, a1) = plt.subplots(1, 2, figsize=(11.5, 4.8)); a0.plot([0, 1], [0, 1], "--", color="#ccc", lw=1)
                for cur2, lab, cc in [(cm, "Morgoth", C_MORG), (cur, "ours", C_OURS)]:
                    ci = f" [{lo:.2f}–{hi:.2f}]" if lab == "ours" else ""
                    a0.plot(cur2["fpr"], cur2["tpr"], color=cc, lw=2.4, label=f"{lab} (AUROC {cur2['auc']:.2f}{ci}, {cur2['ur']:.0f}% under)")
                    a1.plot(cur2["rec"], cur2["prec"], color=cc, lw=2.4, label=f"{lab} (AP {cur2['ap']:.2f}, {cur2['up']:.0f}% under)")
                for r, p in pts.items():
                    a0.plot(p["fpr"], p["tpr"], "o", ms=5, mfc="#999", mec="k", mew=.3, alpha=.75)
                    if np.isfinite(p["precision"]): a1.plot(p["recall"], p["precision"], "o", ms=5, mfc="#999", mec="k", mew=.3, alpha=.75)
                a0.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
                a1.axhline(y.mean(), ls="--", color="#ccc", lw=1)
                a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity"); a0.set_title(f"{tag.upper()} — ROC", fontsize=11)
                a1.set_xlabel("recall"); a1.set_ylabel("precision"); a1.set_title(f"{tag.upper()} — PRC", fontsize=11)
                a0.legend(frameon=False, fontsize=8, loc="lower right"); a1.legend(frameon=False, fontsize=8, loc="upper right")
                for a in (a0, a1): a.set_xlim(-.02, 1.02); a.set_ylim(-.02, 1.02)
                fig.suptitle(f"{ds.upper()} {tag} — report-trained recording model vs Morgoth vs {len(pts)} experts", fontsize=10.5)
                fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(FIG / f"s0e_{ds}_{tag}.png", dpi=150); plt.close(fig)
            else:
                aum = roc_auc_score(y.values[ok], morg.reindex(idx).values[ok]) if morg is not None else np.nan
                md.append(f"| {ds} | {tag} | Morgoth | {aum:.3f} | – | – | – |")
            md.append(f"| {ds} | {tag} | ours | {au:.3f} [{lo:.3f}, {hi:.3f}] | {ap:.3f} | {ur if np.isnan(ur) else f'{ur:.0f}%'} | {up if np.isnan(up) else f'{up:.0f}%'} |")
    (RES / "s0e_recording_model.md").write_text("\n".join(str(x) for x in md))
    print("\n".join(str(x) for x in md)); print("\nwrote results/story/s0e_recording_model.md + figures/story/s0e_*.png")


if __name__ == "__main__":
    main()
