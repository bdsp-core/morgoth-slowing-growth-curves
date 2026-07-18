#!/usr/bin/env python3
"""Morgoth-free detector, v3 — add N1 (drowsiness), STAGE-MATCHED so physiologic drowsy slowing is normalized.

Extends scripts/46/47 to use WAKE + N1 segments. Because N1 carries physiologic slowing, raw pooling would
just add noise; instead every segment is turned into a STAGE-MATCHED deviation z (W segments vs the W normal,
N1 segments vs the N1 normal — grid_norm.json / grid_anorm.json), so only ABNORMAL-for-its-stage slowing
counts. Focal slowing is often most visible in drowsiness, so this is where N1 should help.

Per recording, over W+N1 non-artifact segments:
  amount (generalized): whole-head deviation z per segment -> {mean, p90, max, prevalence z>1.5}
  asymmetry (focal): |L-R region asymmetry deviation z| (temporal, parasagittal), max over pairs -> {mean,p90,max}
L2 logistic, leave-one-out. Reports W+N1 next to the W-only baselines.

Writes figures/story/s0_occasion_ours_v3_{focal,generalized}.png + results/story/s0_occasion_ours_v3.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/48_occasion_wn1_classifier.py
"""
from __future__ import annotations
import glob, importlib.util, json, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

m46 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m46", "scripts/46_occasion_wake_classifier.py"))
importlib.util.spec_from_file_location("m46", "scripts/46_occasion_wake_classifier.py").loader.exec_module(m46)
m43 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m43", "scripts/43_segment_deviation.py"))
importlib.util.spec_from_file_location("m43", "scripts/43_segment_deviation.py").loader.exec_module(m43)

SM = "data/derived/segment_master"
FEATS = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR", "rel_alpha"]
ASYM_F = ["log_delta", "rel_delta", "log_TAR", "log_DAR"]
LOBES = m43.LOBES
PAIRS = [("L_temporal", "R_temporal"), ("L_parasagittal", "R_parasagittal")]
STAGESET = ["W", "N1"]
NORM = {tuple(k.split("|")): tuple(np.array(a) if i < 5 else a for i, a in enumerate(v))
        for k, v in json.load(open("data/derived/grid_norm.json")).items()}
ANORM = {tuple(k.split("~")): tuple(v) for k, v in json.load(open("data/derived/grid_anorm.json")).items()}
FIG = Path("figures/story"); RES = Path("results/story")


def per_fid(args):
    fid, age = args
    f = f"{SM}/eeg_id=ON_{fid}/part.parquet"
    if not os.path.exists(f) or not np.isfinite(age):
        return None
    d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel"] + FEATS)
    d = d[(~d.artifact_flag.astype(bool)) & (d.stage.isin(STAGESET))]
    if d.empty:
        return None
    out = {"fid": fid}
    # amount: whole-head z per segment, stage-matched
    az = {ft: [] for ft in FEATS}
    for st, ds in d.groupby("stage", observed=True):
        wh = ds.groupby("segment", observed=True)[FEATS].mean()
        for ft in FEATS:
            key = (st, "whole_head", ft)
            if key in NORM:
                z = m43.z_of(NORM[key], age, wh[ft].values)
                if ft == "rel_alpha":
                    z = -z
                az[ft].append(z[np.isfinite(z)])
    for ft in FEATS:
        v = np.concatenate(az[ft]) if az[ft] else np.array([])
        if len(v):
            out[f"amt_{ft}_mean"] = v.mean(); out[f"amt_{ft}_p90"] = np.quantile(v, .9)
            out[f"amt_{ft}_max"] = v.max(); out[f"amt_{ft}_prev"] = float((v > 1.5).mean())
    # asymmetry: |L-R region asymmetry z| per segment, stage-matched, max over region pairs
    reg = {r: d[d.channel.isin(ch)].groupby(["stage", "segment"], observed=True)[ASYM_F].mean() for r, ch in LOBES.items()}
    for ft in ASYM_F:
        allz = []
        for L, R in PAIRS:
            if L not in reg or R not in reg:
                continue
            diff = (reg[L][ft] - reg[R][ft]).dropna()
            for (st, seg), dv in diff.items():
                key = (st, f"{L}|{R}", ft)
                if key in ANORM:
                    mu, sd = ANORM[key]
                    allz.append(abs((dv - mu) / (sd or 1.0)))
        if allz:
            v = np.array(allz)
            out[f"asym_{ft}_mean"] = v.mean(); out[f"asym_{ft}_p90"] = np.quantile(v, .9); out[f"asym_{ft}_max"] = v.max()
    return out


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    F = pd.read_parquet("data/derived/occasion_features.parquet")
    age = F[(F.stage == "W") & (F.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    fids = sorted(int(x) for x in F.fid.unique())
    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = [r for r in ex.map(per_fid, [(i, float(age.get(i, np.nan))) for i in fids]) if r is not None]
    T = pd.DataFrame(rows).set_index("fid"); T["age"] = age.reindex(T.index)
    amt = [c for c in T.columns if c.startswith("amt_")] + ["age"]
    asym = [c for c in T.columns if c.startswith("asym_")] + \
           [c for c in T.columns if c.startswith("amt_") and ("log_delta" in c or "rel_delta" in c)] + ["age"]

    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    md = ["# Morgoth-free detector v3 — WAKE + N1, stage-matched deviation (OccasionNoise, N=100, LOO-CV)\n",
          "W and N1 segments, each turned into a stage-matched deviation z (physiologic drowsy slowing "
          "normalized out). Ground truth = panel majority; experts scored vs leave-one-out consensus.\n",
          "| axis | features | n pos/N | AUROC (LOO) | AP | experts | % under ROC | % under PR |",
          "|---|---|---|---|---|---|---|---|"]
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    for name, ax, cols, color in [("focal", "FN", asym, "#c8443c"), ("generalized", "GN", amt, "#2c7fb8")]:
        wide = V.dropna(subset=[f"r1.{ax}"]).pivot_table(index="fid", columns="rater", values=f"r1.{ax}")
        y = (wide.mean(axis=1) >= 0.5).astype(int)
        X = T.reindex(y.index)[cols]
        p = m46.loo_proba(X, y.values)
        auc = roc_auc_score(y, p); ap = average_precision_score(y, p)
        fpr, tpr, _ = roc_curve(y, p); prec, rec, _ = precision_recall_curve(y, p)
        pts = m46.expert_points(wide)
        pu_roc, fr = m46.under_roc(fpr, tpr, pts); pu_pr, fp = m46.under_pr(prec, rec, pts)
        md.append(f"| {name} | W+N1 stage-matched z | {int(y.sum())}/{len(y)} | {auc:.3f} | {ap:.3f} | "
                  f"{len(pts)} | **{100*pu_roc:.0f}%** | **{100*pu_pr:.0f}%** |")
        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.6))
        a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
        a0.plot(fpr, tpr, color=color, lw=2.4, label=f"ours W+N1 (AUROC {auc:.2f})")
        for r, pp in pts.items():
            a0.plot(pp["fpr"], pp["tpr"], "o", ms=6, mfc=("#888" if fr.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a0.plot([], [], "o", mfc="#888", mec="k", label=f"under ({sum(fr.values())})")
        a0.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above ({len(pts)-sum(fr.values())})")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity")
        a0.set_title(f"{name.upper()} — ROC\n{100*pu_roc:.0f}% of {len(pts)} experts under", fontsize=10)
        a0.legend(frameon=False, fontsize=7.5, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
        a1.plot(rec, prec, color=color, lw=2.4, label=f"ours W+N1 (AP {ap:.2f})")
        a1.axhline(y.mean(), ls="--", color="#bbb", lw=1, label=f"prevalence {y.mean():.2f}")
        for r, pp in pts.items():
            if np.isfinite(pp["precision"]):
                a1.plot(pp["recall"], pp["precision"], "o", ms=6, mfc=("#888" if fp.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
        a1.plot([], [], "o", mfc="#888", mec="k", label=f"under ({sum(fp.values())})")
        a1.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above ({len(fp)-sum(fp.values())})")
        a1.set_xlabel("recall"); a1.set_ylabel("precision")
        a1.set_title(f"{name.upper()} — PRC\n{100*pu_pr:.0f}% of {len(fp)} experts under", fontsize=10)
        a1.legend(frameon=False, fontsize=7.5, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"Morgoth-FREE W+N1 {name} detector vs {len(pts)} experts (OccasionNoise, LOO-CV)", fontsize=10.5)
        fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(FIG / f"s0_occasion_ours_v3_{name}.png", dpi=150); plt.close(fig)
    (RES / "s0_occasion_ours_v3.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_occasion_ours_v3_*.png + results/story/s0_occasion_ours_v3.md")


if __name__ == "__main__":
    main()
