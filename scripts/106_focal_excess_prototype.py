"""PROTOTYPE: one slowing-amount direction, applied regionally. Focality as EXCESS, not as a classifier.

The architecture question (MBW): rather than training a "focal detector" that must reject generalized
slowing, learn a single slowing-AMOUNT direction, apply it region by region, and define focality as the
excess of one region over the background (or over its contralateral homologue). Localization then needs no
labels at all -- it is an argmax over a measurement.

  w                 : an L1 logistic direction learned ONCE on whole-head z's, normals vs any pathologic
                      slowing. "How much slowing is here."
  S_amount(r)       : w . z_r   -- the same direction applied to region r's z-scores.
  E_background(r)   : S_amount(r) - S_amount(whole_head)     "more slowing here than in the background"
  E_asymmetry(r)    : S_amount(r) - S_amount(mirror(r))      "more slowing here than on the other side"

Both excesses are invariant to how slow the brain is overall, which is exactly the property the trained
focal detector lacked: it retained absolute lobar terms, so it fired on generalized slowing (S(focal) is
elevated in generalized-only EEGs, p = 5.7e-3), and it was at chance separating exclusively-focal from
generalized recordings (0.477).

THE TEST that decides whether this architecture is better:
  can max-region EXCESS separate exclusively-focal from generalized-only recordings,
  where the trained focal detector scored 0.477 (chance)?

Run: PYTHONPATH=src python scripts/106_focal_excess_prototype.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

spec = importlib.util.spec_from_file_location("m103", "scripts/103_sparse_slowing_score.py")
m103 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m103)

FEATS = m103.FEATS                      # log_delta, log_theta, rel_delta, TAR, DAR
STAGES = m103.STAGES                    # W, N1
LOBES = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
MIRROR = {"L_temporal": "R_temporal", "R_temporal": "L_temporal",
          "L_parasagittal": "R_parasagittal", "R_parasagittal": "L_parasagittal"}
rng = np.random.default_rng(0)


def auc_ci(y, s, n=2000):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    a = roc_auc_score(y, s); bs = []
    for _ in range(n):
        j = rng.choice(len(y), len(y), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "has_focal_slow", "gen_class", "focal_side"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]].drop_duplicates("bdsp_id")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    lu = lu.merge(cp, on="bdsp_id", how="left"); lu["clean_pair"] = lu.clean_pair.fillna(False)

    d = d[(d.src == "cohort") & d.stage.isin(STAGES) & ~d.bdsp_id.isin(ex)
          & d.region.isin(["whole_head"] + LOBES)]
    ref = d[d.clean_normal == True]
    R = m103.ref_curves(ref)

    # per-region z, wide over (feature, stage)
    Zr = {}
    for reg in ["whole_head"] + LOBES:
        cols = {}
        for st in STAGES:
            for f in FEATS:
                if (reg, st, f) not in R: continue
                mu, sd = R[(reg, st, f)]
                sub = d[(d.region == reg) & (d.stage == st)].drop_duplicates("bdsp_id")
                m_ = np.interp(sub.age.values, m103.GRID, mu, left=np.nan, right=np.nan)
                s_ = np.interp(sub.age.values, m103.GRID, sd, left=np.nan, right=np.nan)
                cols[f"{f}@{st}"] = pd.Series((sub[f].values - m_) / s_, index=sub.bdsp_id.values)
        Zr[reg] = pd.DataFrame(cols)
    common = sorted(set.intersection(*[set(v.index) for v in Zr.values()]))
    feat_cols = sorted(set.intersection(*[set(v.columns) for v in Zr.values()]))
    Zr = {k: v.loc[common, feat_cols] for k, v in Zr.items()}
    L = lu.set_index("bdsp_id").reindex(common)

    # ---------- learn ONE slowing-amount direction on whole-head z's
    slow = ((L.gen_class == "pathologic") | (L.has_focal_slow == 1)) & L.clean_pair
    norm = L.clean_normal == True
    keep = (slow | norm).values
    X = Zr["whole_head"][keep]
    med = X.median(); X = X.fillna(med)
    y = slow[keep].astype(int).values
    mu, sg = X.mean(), X.std().replace(0, 1)
    Xs = ((X - mu) / sg).values
    groups = np.array(X.index)

    aucs = []
    for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=1).split(Xs, y, groups):
        m = LogisticRegression(penalty="l1", solver="liblinear", C=0.01, max_iter=3000,
                               class_weight="balanced").fit(Xs[tr], y[tr])
        aucs.append(roc_auc_score(y[te], m.decision_function(Xs[te])))
    model = LogisticRegression(penalty="l1", solver="liblinear", C=0.01, max_iter=3000,
                               class_weight="balanced").fit(Xs, y)
    w = pd.Series(model.coef_[0], index=feat_cols)
    w = w[w.abs() > 1e-8]

    out = ["# Prototype — one slowing-amount direction, applied regionally\n",
           "`w` is learned ONCE, on whole-head z's, clean-normal vs any pathologic slowing "
           f"(nested-ish 5-fold AUROC **{np.mean(aucs):.3f}**, split on patient). It is the direction of "
           "'how much slowing is here'. It is then applied region by region, unchanged.\n",
           f"**Retained ({len(w)} of {len(feat_cols)}):** " +
           ", ".join(f"`{k}` ({v:+.2f})" for k, v in w.sort_values(key=np.abs, ascending=False).items()) + "\n"]

    # ---------- apply regionally
    def amount(reg):
        Z = Zr[reg].fillna(med)
        return ((Z - mu) / sg)[w.index].mul(w, axis=1).sum(axis=1)

    A = pd.DataFrame({r: amount(r) for r in ["whole_head"] + LOBES})
    E_bg = pd.DataFrame({r: A[r] - A.whole_head for r in LOBES})
    E_as = pd.DataFrame({r: A[r] - A[MIRROR[r]] for r in LOBES})

    focal_excess_bg = E_bg.max(axis=1)
    focal_excess_as = E_as.max(axis=1)
    argmax_region = E_bg.idxmax(axis=1)

    # ---------- THE TEST: exclusively-focal vs generalized-only
    excl_focal = ((L.has_focal_slow == 1) & (L.gen_class != "pathologic") & L.clean_pair).values
    gen_only = ((L.gen_class == "pathologic") & (L.has_focal_slow != 1)).values
    m = excl_focal | gen_only
    yy = excl_focal[m].astype(int)

    out.append("\n## The decisive test: exclusively-focal vs generalized-only\n")
    out.append(f"n = {int(excl_focal.sum())} exclusively-focal vs {int(gen_only.sum())} generalized-only.\n")
    out.append("| score | what it is | AUROC [95% CI] |")
    out.append("|---|---|---|")
    for label, v, desc in [
            ("S_amount(whole_head)", A.whole_head[m].values, "global slowing amount (should be ~chance or worse)"),
            ("max lobar amount", A[LOBES].max(axis=1)[m].values, "absolute lobar deviation (what S(focal) used)"),
            ("**max background excess**", focal_excess_bg[m].values, "z_lobe − z_whole_head, invariant to global level"),
            ("**max asymmetry excess**", focal_excess_as[m].values, "z_lobe − z_contralateral, invariant to global level")]:
        a, lo, hi = auc_ci(yy, v)
        out.append(f"| {label} | {desc} | {a:.3f} [{lo:.3f}, {hi:.3f}] |")
    out.append("\nThe trained focal detector scored **0.477 (chance)** on this contrast "
               "(`results/sparse_slowing_score.md`).")

    # ---------- localization, with no labels at all
    side = L.focal_side
    lat = ((L.has_focal_slow == 1) & side.isin(["left", "right"]) & L.clean_pair).values
    pred_side = argmax_region[lat].str[0].map({"L": "left", "R": "right"})
    true_side = side[lat]
    acc = float((pred_side.values == true_side.values).mean())
    # signed asymmetry as a continuous lateralizer (left minus right, temporal chain)
    sgn = (A.L_temporal - A.R_temporal)[lat].values
    y_left = (true_side.values == "left").astype(int)
    a_lat, lo_lat, hi_lat = auc_ci(y_left, sgn)
    out.append("\n## Localization needs no labels\n")
    out.append(f"- argmax of background excess picks the reported **side** correctly in **{acc:.1%}** of "
               f"{int(lat.sum())} lateralized focal recordings (chance 50%).")
    out.append(f"- the signed temporal asymmetry (L − R) discriminates reported-left from reported-right at "
               f"**AUROC {a_lat:.3f}** [{lo_lat:.3f}, {hi_lat:.3f}] — a *measurement*, fit to nothing.")
    out.append(f"- where the argmax lands, overall: " +
               ", ".join(f"{k} {v:.0%}" for k, v in argmax_region[lat].value_counts(normalize=True).items()))

    Path("results/focal_excess_prototype.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
