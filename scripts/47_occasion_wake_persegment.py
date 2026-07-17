#!/usr/bin/env python3
"""Morgoth-free wake detector, v2 — PER-SEGMENT intermittency features (max/p90 over wake segments).

Same goal/eval as scripts/46 (beat the OccasionNoise experts, focal & generalized, wake only, LOO-CV), but
instead of the wake MEAN it uses the per-segment wake features from segment_master ON_ partitions
(crosswalk: fid == the ON_ number; features match occasion_features at r=0.996). This captures INTERMITTENT
slowing — a focus that flickers on/off — which the mean dilutes.

Per recording (wake, non-artifact segments only):
  amount (generalized): whole-head (channel mean) of each feature -> aggregate over segments {mean, p90, max}
  asymmetry (focal): max |L-R| across homologous channel pairs, per segment -> aggregate {mean, p90, max}
Then an L2 logistic per axis, evaluated leave-one-out. Experts = operating points vs LOO consensus.

Writes figures/story/s0_occasion_ours_v2_{focal,generalized}.png + results/story/s0_occasion_ours_v2.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/47_occasion_wake_persegment.py
"""
from __future__ import annotations
import glob, importlib.util, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

m46 = importlib.util.module_from_spec(importlib.util.spec_from_file_location(
    "m46", "scripts/46_occasion_wake_classifier.py"))
importlib.util.spec_from_file_location("m46", "scripts/46_occasion_wake_classifier.py").loader.exec_module(m46)

SM = "data/derived/segment_master"
FEATS = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR", "rel_alpha"]
CHPAIRS = m46.CHPAIRS
FIG = Path("figures/story"); RES = Path("results/story")


def per_fid(args):
    fid, = args
    f = f"{SM}/eeg_id=ON_{fid}/part.parquet"
    if not os.path.exists(f):
        return None
    d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel"] + FEATS)
    d = d[(~d.artifact_flag.astype(bool)) & (d.stage == "W")]
    if d.empty:
        return None
    wh = d.groupby("segment", observed=True)[FEATS].mean()                 # whole-head per segment
    out = {"fid": fid, "n_wake_seg": len(wh)}
    for ft in FEATS:
        v = wh[ft].dropna()
        if len(v):
            out[f"amt_{ft}_mean"] = v.mean(); out[f"amt_{ft}_p90"] = v.quantile(.9); out[f"amt_{ft}_max"] = v.max()
    # asymmetry: per segment, max |L-R| across homologous channel pairs, per feature
    piv = {c: d[d.channel == c].groupby("segment", observed=True)[FEATS].mean() for c in set(sum(CHPAIRS, ()))}
    for ft in ["log_delta", "rel_delta", "log_TAR", "log_DAR"]:
        segmax = None
        for L, R in CHPAIRS:
            if L in piv and R in piv:
                a = (piv[L][ft] - piv[R][ft]).abs()
                segmax = a if segmax is None else np.fmax(segmax, a)
        if segmax is not None:
            segmax = segmax.dropna()
            if len(segmax):
                out[f"asym_{ft}_mean"] = segmax.mean(); out[f"asym_{ft}_p90"] = segmax.quantile(.9)
                out[f"asym_{ft}_max"] = segmax.max()
    return out


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    F = pd.read_parquet("data/derived/occasion_features.parquet")
    age = F[(F.stage == "W") & (F.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    fids = sorted(int(x) for x in F.fid.unique())
    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = [r for r in ex.map(per_fid, [(i,) for i in fids]) if r is not None]
    T = pd.DataFrame(rows).set_index("fid")
    T["age"] = age.reindex(T.index)
    amt_cols = [c for c in T.columns if c.startswith("amt_")] + ["age"]
    asym_cols = [c for c in T.columns if c.startswith("asym_")] + \
                [c for c in T.columns if c.startswith("amt_") and ("log_delta" in c or "rel_delta" in c)] + ["age"]

    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    md = ["# Morgoth-free wake detector v2 — per-segment intermittency (OccasionNoise, N=100, LOO-CV)\n",
          "Per-segment wake features aggregated as {mean, p90, max} over wake segments (captures intermittent "
          "slowing). Ground truth = panel majority; experts scored vs leave-one-out consensus.\n",
          "| axis | features | n pos/N | AUROC (LOO) | AP | experts | % under ROC | % under PR |",
          "|---|---|---|---|---|---|---|---|"]

    for name, ax, cols, color, desc in [("focal", "FN", asym_cols, "#c8443c", "per-seg L-R asymmetry {mean,p90,max}"),
                                        ("generalized", "GN", amt_cols, "#2c7fb8", "per-seg whole-head amount {mean,p90,max}")]:
        wide = V.dropna(subset=[f"r1.{ax}"]).pivot_table(index="fid", columns="rater", values=f"r1.{ax}")
        y = (wide.mean(axis=1) >= 0.5).astype(int)
        X = T.reindex(y.index)[cols]
        p = m46.loo_proba(X, y.values)
        auc = roc_auc_score(y, p); ap = average_precision_score(y, p)
        fpr, tpr, _ = roc_curve(y, p); prec, rec, _ = precision_recall_curve(y, p)
        pts = m46.expert_points(wide)
        pu_roc, fr = m46.under_roc(fpr, tpr, pts); pu_pr, fp = m46.under_pr(prec, rec, pts)
        md.append(f"| {name} | {desc} | {int(y.sum())}/{len(y)} | {auc:.3f} | {ap:.3f} | {len(pts)} | "
                  f"**{100*pu_roc:.0f}%** | **{100*pu_pr:.0f}%** |")

        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.6))
        a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
        a0.plot(fpr, tpr, color=color, lw=2.4, label=f"our wake v2 (AUROC {auc:.2f})")
        for r, pp in pts.items():
            a0.plot(pp["fpr"], pp["tpr"], "o", ms=6, mfc=("#888" if fr.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a0.plot([], [], "o", mfc="#888", mec="k", label=f"under curve ({sum(fr.values())})")
        a0.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above curve ({len(pts)-sum(fr.values())})")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity")
        a0.set_title(f"{name.upper()} — ROC\n{100*pu_roc:.0f}% of {len(pts)} experts under our curve", fontsize=10)
        a0.legend(frameon=False, fontsize=7.5, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
        a1.plot(rec, prec, color=color, lw=2.4, label=f"our wake v2 (AP {ap:.2f})")
        a1.axhline(y.mean(), ls="--", color="#bbb", lw=1, label=f"prevalence {y.mean():.2f}")
        for r, pp in pts.items():
            if np.isfinite(pp["precision"]):
                a1.plot(pp["recall"], pp["precision"], "o", ms=6, mfc=("#888" if fp.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a1.plot([], [], "o", mfc="#888", mec="k", label=f"under PR ({sum(fp.values())})")
        a1.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above PR ({len(fp)-sum(fp.values())})")
        a1.set_xlabel("recall"); a1.set_ylabel("precision")
        a1.set_title(f"{name.upper()} — PRC\n{100*pu_pr:.0f}% of {len(fp)} experts under our curve", fontsize=10)
        a1.legend(frameon=False, fontsize=7.5, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"Morgoth-FREE per-segment wake {name} detector vs {len(pts)} experts (OccasionNoise, LOO-CV)", fontsize=10.5)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(FIG / f"s0_occasion_ours_v2_{name}.png", dpi=150); plt.close(fig)

    (RES / "s0_occasion_ours_v2.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_occasion_ours_v2_*.png + results/story/s0_occasion_ours_v2.md")


if __name__ == "__main__":
    main()
