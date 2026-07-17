#!/usr/bin/env python3
"""Morgoth-free detector v4 — ALL sleep stages (stage-matched) + LOCALIZED focal features.

Generalized: whole-head amount deviation z over all stages {mean, p90, max, prevalence}.
Focal: the discriminating signal is SPATIAL, so we localize then characterize. Per segment we z-score each
of 6 regions (anterior, posterior, L/R temporal, L/R parasagittal) against its own (stage, age) normal, and
build:
  peak_z        max region z                         (how abnormal the worst region is)
  focality      peak_z - median region z             (excess over background: high=focal, ~0=generalized)
  asym_z        |L-R region asymmetry z|, max pair    (a lateralized focus)
aggregated over segments as {mean, p90, max}, plus SPATIAL STABILITY = the fraction of segments whose peak
region is the modal peak region (a real focus is stable; noise wanders).

STAGESET overridable via env (default all 5). L2 logistic, leave-one-out. Experts vs LOO consensus.
Writes figures/story/s0_occasion_ours_v4_{focal,generalized}.png + results/story/s0_occasion_ours_v4.md
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/49_occasion_allstage_localized.py
"""
from __future__ import annotations
import importlib.util, json, os
from collections import Counter
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
FOC_F = ["log_delta", "rel_delta", "log_TAR"]                         # focal-slowing indicators
LOC_REGIONS = ["anterior", "posterior", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
LOBES = m43.LOBES; ANT = m43.ANT; POS = m43.POS
REG_CH = {"anterior": ANT, "posterior": POS, **LOBES}
PAIRS = [("L_temporal", "R_temporal"), ("L_parasagittal", "R_parasagittal")]
STAGESET = os.environ.get("STAGESET", "W,N1,N2,N3,REM").split(",")
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
    # ---- generalized amount: whole-head z per segment, stage-matched ----
    az = {ft: [] for ft in FEATS}
    for st, ds in d.groupby("stage", observed=True):
        wh = ds.groupby("segment", observed=True)[FEATS].mean()
        for ft in FEATS:
            key = (st, "whole_head", ft)
            if key in NORM:
                z = m43.z_of(NORM[key], age, wh[ft].values); z = -z if ft == "rel_alpha" else z
                az[ft].append(z[np.isfinite(z)])
    for ft in FEATS:
        v = np.concatenate(az[ft]) if az[ft] else np.array([])
        if len(v):
            out[f"amt_{ft}_mean"] = v.mean(); out[f"amt_{ft}_p90"] = np.quantile(v, .9)
            out[f"amt_{ft}_max"] = v.max(); out[f"amt_{ft}_prev"] = float((v > 1.5).mean())
    # ---- focal localization: region z per segment, peak / focality / asymmetry ----
    # region z: build (stage,segment) x region z for each focal feature
    peakZ = {ft: [] for ft in FOC_F}; focal = {ft: [] for ft in FOC_F}; peak_reg = []
    reg_seg = {r: d[d.channel.isin(ch)].groupby(["stage", "segment"], observed=True)[FOC_F].mean()
               for r, ch in REG_CH.items()}
    idx = None
    for r in LOC_REGIONS:
        idx = reg_seg[r].index if idx is None else idx.union(reg_seg[r].index)
    for ft in FOC_F:
        Z = {}
        for r in LOC_REGIONS:
            s = reg_seg[r][ft].reindex(idx)
            z = np.full(len(idx), np.nan)
            for st in {i[0] for i in idx}:
                key = (st, r, ft)
                if key in NORM:
                    m = np.array([i[0] == st for i in idx])
                    z[m] = m43.z_of(NORM[key], age, s.values[m])
            Z[r] = z
        M = np.vstack([Z[r] for r in LOC_REGIONS])                    # region x segment
        pk = np.nanmax(M, axis=0); med = np.nanmedian(M, axis=0)
        ok = np.isfinite(pk)
        peakZ[ft] = pk[ok]; focal[ft] = (pk - med)[ok]
        if ft == "rel_delta":
            pr = np.array(LOC_REGIONS)[np.nanargmax(np.nan_to_num(M, nan=-9), axis=0)][ok]
            peak_reg = list(pr)
        v = peakZ[ft]; fv = focal[ft]
        if len(v):
            out[f"peak_{ft}_mean"] = v.mean(); out[f"peak_{ft}_p90"] = np.quantile(v, .9); out[f"peak_{ft}_max"] = v.max()
            out[f"foc_{ft}_mean"] = fv.mean(); out[f"foc_{ft}_p90"] = np.quantile(fv, .9); out[f"foc_{ft}_max"] = fv.max()
    # asymmetry z (max over region pairs)
    for ft in FOC_F:
        allz = []
        for L, R in PAIRS:
            diff = (reg_seg[L][ft] - reg_seg[R][ft]).dropna()
            for (st, seg), dv in diff.items():
                key = (st, f"{L}|{R}", ft)
                if key in ANORM:
                    mu, sd = ANORM[key]; allz.append(abs((dv - mu) / (sd or 1.0)))
        if allz:
            v = np.array(allz); out[f"asym_{ft}_p90"] = np.quantile(v, .9); out[f"asym_{ft}_max"] = v.max()
    # spatial stability: dominance of the modal peak region
    if peak_reg:
        c = Counter(peak_reg); out["peak_region_dominance"] = c.most_common(1)[0][1] / len(peak_reg)
    return out


def evaluate(T, V, name, ax, cols, color):
    wide = V.dropna(subset=[f"r1.{ax}"]).pivot_table(index="fid", columns="rater", values=f"r1.{ax}")
    y = (wide.mean(axis=1) >= 0.5).astype(int)
    X = T.reindex(y.index)[[c for c in cols if c in T.columns]]
    p = m46.loo_proba(X, y.values)
    auc = roc_auc_score(y, p); ap = average_precision_score(y, p)
    fpr, tpr, _ = roc_curve(y, p); prec, rec, _ = precision_recall_curve(y, p)
    pts = m46.expert_points(wide)
    pu_roc, fr = m46.under_roc(fpr, tpr, pts); pu_pr, fp = m46.under_pr(prec, rec, pts)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.6))
    a0.plot([0, 1], [0, 1], "--", color="#bbb", lw=1); a0.plot(fpr, tpr, color=color, lw=2.4, label=f"ours (AUROC {auc:.2f})")
    for r, pp in pts.items():
        a0.plot(pp["fpr"], pp["tpr"], "o", ms=6, mfc=("#888" if fr.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
    a0.plot([], [], "o", mfc="#888", mec="k", label=f"under ({sum(fr.values())})"); a0.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above ({len(pts)-sum(fr.values())})")
    a0.set_xlabel("1 − specificity"); a0.set_ylabel("sensitivity"); a0.set_title(f"{name.upper()} — ROC\n{100*pu_roc:.0f}% of {len(pts)} experts under", fontsize=10)
    a0.legend(frameon=False, fontsize=7.5, loc="lower right"); a0.set_xlim(-.02, 1.02); a0.set_ylim(-.02, 1.02)
    a1.plot(rec, prec, color=color, lw=2.4, label=f"ours (AP {ap:.2f})"); a1.axhline(y.mean(), ls="--", color="#bbb", lw=1, label=f"prev {y.mean():.2f}")
    for r, pp in pts.items():
        if np.isfinite(pp["precision"]):
            a1.plot(pp["recall"], pp["precision"], "o", ms=6, mfc=("#888" if fp.get(r) else "#e41a1c"), mec="k", mew=.4, alpha=.85)
    a1.plot([], [], "o", mfc="#888", mec="k", label=f"under ({sum(fp.values())})"); a1.plot([], [], "o", mfc="#e41a1c", mec="k", label=f"above ({len(fp)-sum(fp.values())})")
    a1.set_xlabel("recall"); a1.set_ylabel("precision"); a1.set_title(f"{name.upper()} — PRC\n{100*pu_pr:.0f}% of {len(fp)} under", fontsize=10)
    a1.legend(frameon=False, fontsize=7.5, loc="upper right"); a1.set_xlim(-.02, 1.02); a1.set_ylim(-.02, 1.02)
    fig.suptitle(f"Morgoth-FREE {'+'.join(STAGESET)} {name} detector vs {len(pts)} experts (LOO-CV)", fontsize=10.5)
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(FIG / f"s0_occasion_ours_v4_{name}.png", dpi=150); plt.close(fig)
    return f"| {name} | {'+'.join(STAGESET)} | {int(y.sum())}/{len(y)} | {auc:.3f} | {ap:.3f} | {len(pts)} | **{100*pu_roc:.0f}%** | **{100*pu_pr:.0f}%** |"


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    F = pd.read_parquet("data/derived/occasion_features.parquet")
    age = F[(F.stage == "W") & (F.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    fids = sorted(int(x) for x in F.fid.unique())
    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = [r for r in ex.map(per_fid, [(i, float(age.get(i, np.nan))) for i in fids]) if r is not None]
    T = pd.DataFrame(rows).set_index("fid"); T["age"] = age.reindex(T.index)
    amt = [c for c in T.columns if c.startswith("amt_")] + ["age"]
    foc = [c for c in T.columns if c.startswith(("peak_", "foc_", "asym_", "peak_region"))] + ["age"]
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    md = ["# Morgoth-free detector v4 — all stages (stage-matched) + localized focal (OccasionNoise, LOO-CV)\n",
          f"Stages: {'+'.join(STAGESET)}. Focal uses localization: per-segment region z -> peak_z, focality "
          "(peak − median region), asymmetry z, spatial stability.\n",
          "| axis | stages | n pos/N | AUROC | AP | experts | % under ROC | % under PR |",
          "|---|---|---|---|---|---|---|---|"]
    md.append(evaluate(T, V, "focal", "FN", foc, "#c8443c"))
    md.append(evaluate(T, V, "generalized", "GN", amt, "#2c7fb8"))
    (RES / "s0_occasion_ours_v4.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s0_occasion_ours_v4_*.png + results/story/s0_occasion_ours_v4.md")


if __name__ == "__main__":
    main()
