#!/usr/bin/env python3
"""ONE Morgoth-free model — step 2: train (v1 broadcast, v2 MIL) on report, test on report / occasion / MoE.

Segment-level, two heads (focal <- FOC features; generalized <- AMT features), trained ONLY on report-train
segments. Two label strategies:
  v1 broadcast : every segment inherits its recording's report label; L2 logistic.
  v2 MIL       : broadcast init, then iteratively relabel each POSITIVE recording's positive segments to its
                 top-k by current score (MIL-EM) — focuses positive supervision on the segments that show
                 the finding, which matters for intermittent focal slowing.
EEG-level answer = top-k mean of segment scores (k=5, the §1b winner); a single clip (MoE) = its segment score.

Evaluated on THREE held-out sets, none seen in training:
  report-test  (report labels, single scorer)
  OccasionNoise + MoE (expert-panel labels; our model vs Morgoth vs experts on the same axes, % under curve)

Writes results/story/s0d_single_model.md + figures/story/s0d_single_{occasion,moe}_{focal,generalized}.png
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/54_single_model_train_eval.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

m49 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py"))
importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py").loader.exec_module(m49)
m45 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m45", "scripts/45_moe_section0.py"))
importlib.util.spec_from_file_location("m45", "scripts/45_moe_section0.py").loader.exec_module(m45)
m46 = m49.m46
FEATS = m49.FEATS; FOC_F = m49.FOC_F
AMT = [f"amt_{ft}" for ft in FEATS] + ["age"]
FOC = [f"{p}_{ft}" for ft in FOC_F for p in ("peak", "foc", "asym")] + ["age"]
K = 5
FIG = Path("figures/story"); RES = Path("results/story")
from morgoth_slowing.viz.palette import MORGOTH, OURS, OURS_ALT
C_MORG, C_OURS = MORGOTH, OURS


class Head:
    def fit(self, X, y):
        self.sc = StandardScaler().fit(X); self.m = LogisticRegression(
            C=0.3, class_weight="balanced", max_iter=3000).fit(self.sc.transform(X), y); return self
    def score(self, X):
        return self.m.predict_proba(self.sc.transform(X))[:, 1]


def train_broadcast(Xtr, ytr):
    return Head().fit(Xtr.values, ytr.values)


def train_mil(seg, cols, ylab, k=K, iters=3):
    X = seg[cols].fillna(seg[cols].median()); eeg = seg.eeg_id.values
    yb = seg[ylab].values.astype(float)                  # broadcast init
    pos_eegs = seg.loc[seg[ylab] == 1, "eeg_id"].unique()
    idx_by_eeg = {e: np.where(eeg == e)[0] for e in pos_eegs}
    lab = yb.copy()
    h = Head().fit(X.values, lab)
    for _ in range(iters):
        s = h.score(X.values)
        lab = np.zeros(len(yb))                          # negatives (and negative EEGs) stay 0
        for e, idx in idx_by_eeg.items():
            top = idx[np.argsort(s[idx])[::-1][:min(k, len(idx))]]
            lab[top] = 1
        h = Head().fit(X.values, lab)
    return h


def expert_and_morgoth(name):
    """(vote_matrix indexed by eeg_id, morgoth_score series) for occasion or moe, per axis."""
    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    out = {}
    if name == "occasion":
        V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
        M = pd.read_parquet("data/derived/occasion_morgoth_preds.parquet")
        for ax, mx in [("focal", "FN"), ("generalized", "GN")]:
            wide = V.dropna(subset=[f"r1.{mx}"]).pivot_table(index="fid", columns="rater", values=f"r1.{mx}")
            wide.index = [f"ON_{int(i)}" for i in wide.index]
            morg = M[M.axis == mx].set_index("fid").M_pred; morg.index = [f"ON_{int(i)}" for i in morg.index]
            out[ax] = (wide, morg)
    else:
        for ax, cat, hc in [("focal", "focalslowing", "p_focal"), ("generalized", "genslowing", "p_generalized")]:
            wide = m45.build_matrix(cat); wide.index = [f"MOE_{e}" for e in wide.index]
            out[ax] = (wide, head[hc])
    return out


def panel_curve(ax, y, s, pts, color, label):
    fpr, tpr, _ = roc_curve(y, s); prec, rec, _ = precision_recall_curve(y, s)
    ur = {r: float(np.interp(p["fpr"], fpr, tpr)) >= p["tpr"] - 1e-9 for r, p in pts.items()}
    o = np.argsort(rec); rs, ps = rec[o], prec[o]
    up = {r: float(np.interp(p["recall"], rs, ps)) >= p["precision"] - 1e-9 for r, p in pts.items() if np.isfinite(p["precision"])}
    return dict(auc=roc_auc_score(y, s), ap=average_precision_score(y, s), fpr=fpr, tpr=tpr, prec=prec, rec=rec,
                ur=100*np.mean(list(ur.values())) if ur else np.nan, up=100*np.mean(list(up.values())) if up else np.nan)


def boot_ci(y, s, n=2000, seed=0):
    """Recording-level bootstrap 95% CI for AUROC — the panel recordings (one expert-majority label each)
    are the resampling unit. Resamples with replacement; skips draws with a single class."""
    y = np.asarray(y); s = np.asarray(s); rng = np.random.default_rng(seed); N = len(y); a = []
    for _ in range(n):
        idx = rng.integers(0, N, N)
        if np.unique(y[idx]).size >= 2:
            a.append(roc_auc_score(y[idx], s[idx]))
    return (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))) if a else (np.nan, np.nan)


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    tr = S[(S.dataset == "report") & (S.split == "train")]
    heads = {}
    for tag, cols, ylab in [("focal", FOC, "y_focal"), ("generalized", AMT, "y_gen")]:
        Xtr = tr[cols].fillna(tr[cols].median()); ytr = tr[ylab].astype(int)
        heads[("v1", tag)] = train_broadcast(Xtr, ytr)
        heads[("v2", tag)] = train_mil(tr, cols, ylab)
    # score every segment with both models/heads
    for (ver, tag), h in heads.items():
        cols = FOC if tag == "focal" else AMT
        S[f"{ver}_{tag}"] = h.score(S[cols].fillna(S[cols].median()).values)

    def eeg_scores(sub, scorecol):
        return sub.groupby("eeg_id")[scorecol].apply(lambda v: np.sort(v.values)[::-1][:K].mean())

    md = ["# ONE Morgoth-free model — trained on report, tested on report / occasion / MoE\n",
          "Segment-level, two heads, trained ONLY on report-train. EEG answer = top-5 mean of segment scores "
          "(a single clip = its segment). v1 = broadcast labels; v2 = MIL (top-k relabelling).\n",
          "| test set | axis | model | AUROC | AP | % experts under ROC | % under PR |",
          "|---|---|---|---|---|---|---|"]

    # ---- report-test (report labels) ----
    rt = S[(S.dataset == "report") & (S.split == "test")]
    eeg = pd.read_parquet("data/derived/single_model_eeg.parquet").set_index("eeg_id")
    for tag, ylab in [("focal", "y_focal"), ("generalized", "y_gen")]:
        for ver in ["v1", "v2"]:
            es = eeg_scores(rt, f"{ver}_{tag}"); y = eeg.loc[es.index, ylab].astype(int)
            md.append(f"| report-test | {tag} | {ver} | {roc_auc_score(y, es):.3f} | "
                      f"{average_precision_score(y, es):.3f} | – | – |")

    # ---- external panel: our model vs Morgoth vs experts (MoE cut from the story) ----
    for ds in ["occasion"]:
        em = expert_and_morgoth(ds)
        for tag in ["focal", "generalized"]:
            wide, morg = em[tag]
            sub = S[S.dataset == ds]
            keep_eeg = wide.index.intersection(sub.eeg_id.unique())
            wide = wide.loc[keep_eeg]
            y = (wide.mean(axis=1) >= 0.5).astype(int)
            pts = m46.expert_points(wide)
            fig, (a0, a1) = plt.subplots(1, 2, figsize=(11.5, 4.8)); a0.plot([0, 1], [0, 1], "--", color="#ccc", lw=1)
            best = None
            for ver, col, cc in [("Morgoth", None, C_MORG), ("ours-v1", "v1", OURS_ALT), ("ours-v2", "v2", C_OURS)]:
                if ver == "Morgoth":
                    s = morg.reindex(keep_eeg).values
                else:
                    es = eeg_scores(sub, f"{col}_{tag}").reindex(keep_eeg); s = es.values
                ok = np.isfinite(s) & np.isfinite(y.values)
                cur = panel_curve(a0, y.values[ok], s[ok], pts, cc, ver)
                lo, hi = boot_ci(y.values[ok], s[ok])
                a0.plot(cur["fpr"], cur["tpr"], color=cc, lw=2.4, label=f"{ver} (AUROC {cur['auc']:.2f} [{lo:.2f}–{hi:.2f}], {cur['ur']:.0f}% under)")
                a1.plot(cur["rec"], cur["prec"], color=cc, lw=2.4, label=f"{ver} (AP {cur['ap']:.2f}, {cur['up']:.0f}% under)")
                md.append(f"| {ds} | {tag} | {ver} | {cur['auc']:.3f} [{lo:.3f}, {hi:.3f}] | {cur['ap']:.3f} | "
                          f"{cur['ur']:.0f}% | {cur['up']:.0f}% |")
            for r, p in pts.items():
                a0.plot(p["fpr"], p["tpr"], "o", ms=4.5, mfc="#999", mec="k", mew=.3, alpha=.7)
                if np.isfinite(p["precision"]):
                    a1.plot(p["recall"], p["precision"], "o", ms=4.5, mfc="#999", mec="k", mew=.3, alpha=.7)
            a0.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
            a1.axhline(y.mean(), ls="--", color="#ccc", lw=1)
            a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity"); a0.set_title(f"{tag.upper()} — ROC", fontsize=11)
            a1.set_xlabel("recall"); a1.set_ylabel("precision"); a1.set_title(f"{tag.upper()} — PRC", fontsize=11)
            a0.legend(frameon=False, fontsize=8, loc="lower right"); a1.legend(frameon=False, fontsize=8, loc="upper right")
            for a in (a0, a1):
                a.set_xlim(-.02, 1.02); a.set_ylim(-.02, 1.02)
            fig.suptitle(f"{ds.upper()} {tag} — ONE report-trained model (MIL) vs Morgoth vs {len(pts)} experts", fontsize=10.5)
            fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(FIG / f"s0d_single_{ds}_{tag}.png", dpi=150); plt.close(fig)

    (RES / "s0d_single_model.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote results/story/s0d_single_model.md + figures/story/s0d_single_*.png")


if __name__ == "__main__":
    main()
