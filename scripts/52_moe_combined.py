#!/usr/bin/env python3
"""MoE — Morgoth vs a Morgoth-FREE classifier vs the expert panel, ON THE SAME AXES.

Each MoE event is a single 15 s clip (one segment), so unlike OccasionNoise there is NO intermittency /
multi-stage aggregation to exploit — the classifier sees exactly what Morgoth's clip-level head sees, which
makes this a FAIR head-to-head. Per clip we build stage-matched deviation features (the clip's own stage &
age): whole-head amount z (generalized) and localized region z -> peak / focality / asymmetry (focal).
5-fold cross-validated logistic. Ground truth = panel majority (bwestove excluded). Morgoth = gate-rerun
EEG-level p_focal / p_generalized. Experts = operating points vs leave-one-out consensus.

Writes figures/story/s0_moe_combined_{focal,generalized}.png + results/story/s0_moe_combined.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/52_moe_combined.py
"""
from __future__ import annotations
import importlib.util, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve, average_precision_score

m49 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py"))
importlib.util.spec_from_file_location("m49", "scripts/49_occasion_allstage_localized.py").loader.exec_module(m49)
m45 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m45", "scripts/45_moe_section0.py"))
importlib.util.spec_from_file_location("m45", "scripts/45_moe_section0.py").loader.exec_module(m45)
m46 = m49.m46; m43 = m49.m43
SM = "data/derived/segment_master"
FEATS = m49.FEATS; FOC_F = m49.FOC_F; LOC_REGIONS = m49.LOC_REGIONS; REG_CH = m49.REG_CH; PAIRS = m49.PAIRS
NORM = m49.NORM; ANORM = m49.ANORM
FIG = Path("figures/story"); RES = Path("results/story")
C_MORG, C_OURS = "#6a3d9a", "#e6550d"


def per_clip(args):
    eid, age = args
    f = f"{SM}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f) or not np.isfinite(age):
        return None
    d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel"] + FEATS)
    d = d[~d.artifact_flag.astype(bool)]
    if d.empty:
        return None
    st = d.stage.iloc[0]
    out = {"eeg_id": eid, "age": age}
    for ft in FEATS:                                             # generalized amount z (whole head)
        key = (st, "whole_head", ft)
        if key in NORM:
            z = m43.z_of(NORM[key], age, np.array([d[ft].mean()]))[0]
            out[f"amt_{ft}"] = -z if ft == "rel_alpha" else z
    regm = {r: d[d.channel.isin(ch)][FOC_F].mean() for r, ch in REG_CH.items() if not d[d.channel.isin(ch)].empty}
    for ft in FOC_F:                                             # focal localization
        zs = [m43.z_of(NORM[(st, r, ft)], age, np.array([regm[r][ft]]))[0]
              for r in LOC_REGIONS if r in regm and (st, r, ft) in NORM]
        if zs:
            v = np.array(zs); out[f"peak_{ft}"] = np.nanmax(v); out[f"foc_{ft}"] = np.nanmax(v) - np.nanmedian(v)
        az = []
        for L, R in PAIRS:
            key = (st, f"{L}|{R}", ft)
            if L in regm and R in regm and key in ANORM:
                mu, sd = ANORM[key]; az.append(abs((regm[L][ft] - regm[R][ft] - mu) / (sd or 1.0)))
        if az:
            out[f"asym_{ft}"] = max(az)
    return out


def kfold_proba(X, y, k=5):
    X = X.fillna(X.median()).values; y = np.asarray(y); p = np.zeros(len(y))
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=0).split(X, y):
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000).fit(sc.transform(X[tr]), y[tr])
        p[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    return p


def ucr(fpr, tpr, pts):
    return {r: float(np.interp(p["fpr"], fpr, tpr)) >= p["tpr"] - 1e-9 for r, p in pts.items()}


def ucp(prec, rec, pts):
    o = np.argsort(rec); rs, ps = np.asarray(rec)[o], np.asarray(prec)[o]
    return {r: float(np.interp(p["recall"], rs, ps)) >= p["precision"] - 1e-9 for r, p in pts.items() if np.isfinite(p["precision"])}


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id").set_index("eeg_id")
    moe_ids = [e for e in head.index if str(e).startswith("MOE_")]
    ages = {e: float(lab.age.get(e, np.nan)) for e in moe_ids}
    with ThreadPoolExecutor(max_workers=16) as ex:
        rows = [r for r in ex.map(per_clip, [(e, ages[e]) for e in moe_ids]) if r]
    T = pd.DataFrame(rows).set_index("eeg_id")
    amt = [c for c in T.columns if c.startswith("amt_")] + ["age"]
    foc = [c for c in T.columns if c.startswith(("peak_", "foc_", "asym_"))] + ["age"]

    md = ["# MoE — Morgoth vs Morgoth-FREE vs experts, same axes (single-clip; fair head-to-head)\n",
          "| axis | Morgoth AUROC | ours AUROC | experts under Morgoth (ROC/PR) | experts under OURS (ROC/PR) |",
          "|---|---|---|---|---|"]
    for name, cat, headcol, cols, color in [("focal", "focalslowing", "p_focal", foc, "#c8443c"),
                                            ("generalized", "genslowing", "p_generalized", amt, "#2c7fb8")]:
        M = m45.build_matrix(cat); M.index = [f"MOE_{e}" for e in M.index]
        keep = M.index.intersection(T.index).intersection(head.index)
        M = M.loc[keep]
        y = (M.mean(axis=1) >= 0.5).astype(int)
        pts = m46.expert_points(M)
        s_m = head.loc[keep, headcol].values
        p_o = kfold_proba(T.loc[keep, cols], y.values)
        curves = {}
        for tag, s in [("Morgoth", s_m), ("ours", p_o)]:
            fpr, tpr, _ = roc_curve(y, s); prec, rec, _ = precision_recall_curve(y, s)
            curves[tag] = dict(auc=roc_auc_score(y, s), ap=average_precision_score(y, s), fpr=fpr, tpr=tpr,
                               prec=prec, rec=rec, ur=ucr(fpr, tpr, pts), up=ucp(prec, rec, pts))
        cm, co = curves["Morgoth"], curves["ours"]
        md.append(f"| {name} | {cm['auc']:.3f} | {co['auc']:.3f} | "
                  f"{100*np.mean(list(cm['ur'].values())):.0f}% / {100*np.mean(list(cm['up'].values())):.0f}% | "
                  f"**{100*np.mean(list(co['ur'].values())):.0f}% / {100*np.mean(list(co['up'].values())):.0f}%** |")
        fig, (a0, a1) = plt.subplots(1, 2, figsize=(11.5, 4.8))
        a0.plot([0, 1], [0, 1], "--", color="#ccc", lw=1)
        a0.plot(cm["fpr"], cm["tpr"], color=C_MORG, lw=2.4, label=f"Morgoth (AUROC {cm['auc']:.2f}, {100*np.mean(list(cm['ur'].values())):.0f}% under)")
        a0.plot(co["fpr"], co["tpr"], color=C_OURS, lw=2.4, label=f"Morgoth-free (AUROC {co['auc']:.2f}, {100*np.mean(list(co['ur'].values())):.0f}% under)")
        for r, p in pts.items():
            a0.plot(p["fpr"], p["tpr"], "o", ms=4.5, mfc="#999", mec="k", mew=.3, alpha=.75)
        a0.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
        a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity"); a0.set_title(f"{name.upper()} — ROC", fontsize=11)
        a0.legend(frameon=False, fontsize=8, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
        a1.axhline(y.mean(), ls="--", color="#ccc", lw=1, label=f"prevalence {y.mean():.2f}")
        a1.plot(cm["rec"], cm["prec"], color=C_MORG, lw=2.4, label=f"Morgoth (AP {cm['ap']:.2f}, {100*np.mean(list(cm['up'].values())):.0f}% under)")
        a1.plot(co["rec"], co["prec"], color=C_OURS, lw=2.4, label=f"Morgoth-free (AP {co['ap']:.2f}, {100*np.mean(list(co['up'].values())):.0f}% under)")
        for r, p in pts.items():
            if np.isfinite(p["precision"]):
                a1.plot(p["recall"], p["precision"], "o", ms=4.5, mfc="#999", mec="k", mew=.3, alpha=.75)
        a1.set_xlabel("recall"); a1.set_ylabel("precision"); a1.set_title(f"{name.upper()} — PRC", fontsize=11)
        a1.legend(frameon=False, fontsize=8, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
        fig.suptitle(f"MoE {name} slowing — Morgoth vs a Morgoth-FREE classifier vs {len(pts)} experts "
                     f"(single 15 s clip; 5-fold CV; experts vs LOO consensus)", fontsize=10)
        fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(FIG / f"s0_moe_combined_{name}.png", dpi=150); plt.close(fig)
    (RES / "s0_moe_combined.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_moe_combined_*.png + results/story/s0_moe_combined.md")


if __name__ == "__main__":
    main()
