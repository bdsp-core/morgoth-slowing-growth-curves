"""NESTED-CV DETECTION (honest, leakage-free version of scripts/84_vigilance_matched_detection.py).

scripts/84 reports, per sleep stage, the AUROC of the BEST whole-head feature -- but the best feature is
chosen on the SAME data the AUROC is reported on. With 5 features x 5 stages that is a real (if mild)
selection optimism. This script re-estimates those numbers with nested cross-validation, splitting on
`bdsp_id` so no patient leaks between reference / selection / scoring.

Design (reuses scripts/84 exactly except for the CV wrapper):
  region = whole_head; stages W,N1,N2,N3,REM; features TAR,DAR,log_delta,log_theta,rel_delta.
  positives = routine (src=='cohort') abnormals of the target; negatives = held-out routine clean-normals;
  normal reference (age-kernel, bw=5.0) = routine clean-normals NOT used as negatives.
  targets: abnormal (is_abnormal), gen_pathologic (gen_class=='pathologic'), focal (has_focal_slow).

Nested CV (split on bdsp_id):
  OUTER  5-fold x 5 repeats = 25 outer estimates. Each fold holds out a set of bdsp_ids.
  INNER  within the outer-train bdsp_ids only, an inner K-fold chooses the best feature per stage by inner
         AUROC. The normal reference for outer scoring is built from outer-train clean-normals only.
  Then the outer-test recordings are scored with the inner-chosen feature and the outer-train reference.

Reported: nested AUROC (mean + 95% spread over the 25 outer folds), the naive select-and-report-on-same-data
AUROC (reproducing scripts/84), the optimism (naive - nested), inner-loop feature-selection stability, and a
FIXED-a-priori-feature nested variant (TAR/log_delta/DAR/DAR/TAR) that isolates the feature-selection share
of the optimism from the reference-re-estimation share.

Run: PYTHONPATH=src python3 scripts/96_nested_cv_detection.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

FEATURES = ["TAR", "DAR", "log_delta", "log_theta", "rel_delta"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
REGION = "whole_head"
BW = 5.0
N_OUTER = 5
N_REPEAT = 5
INNER_K = 3
REF_CAP = 4000                      # subsample the age-kernel reference to <= this many recordings/fold
FIXED_FEAT = {"W": "TAR", "N1": "log_delta", "N2": "DAR", "N3": "DAR", "REM": "TAR"}  # scripts/84 winners
PUBLISHED = {"W": ("TAR", 0.848), "N1": ("log_delta", 0.875), "N2": ("DAR", 0.791),
             "N3": ("DAR", 0.758), "REM": ("TAR", 0.825)}
TARGETS = ["abnormal", "gen_pathologic", "focal"]
FI = {f: i for i, f in enumerate(FEATURES)}


def normal_z_multi(vals, ages, ref_vals, ref_ages, bw=BW):
    """Age-kernel normal-referenced z for ALL features at once (weights depend only on age -> computed once
    per test row, reused across features). Matches scripts/84 normal_z per feature: per-feature the reference
    is restricted to rows with finite age and finite feature value, and needs summed kernel weight >= 5.
    vals (n,F), ages (n,), ref_vals (m,F), ref_ages (m,) -> z (n,F)."""
    n, F = vals.shape
    z = np.full((n, F), np.nan)
    ra = np.asarray(ref_ages, float)
    rv = np.asarray(ref_vals, float)
    age_ok = np.isfinite(ra)
    rv_fin = np.isfinite(rv)                      # (m,F)
    rv0 = np.where(rv_fin, rv, 0.0)
    for i in range(n):
        if not np.isfinite(ages[i]):
            continue
        wt = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2)
        wt = np.where(age_ok, wt, 0.0)
        We = wt[:, None] * rv_fin                 # (m,F) per-feature effective weights (NaN ref -> 0)
        sw = We.sum(0)                            # (F,)
        denom = np.where(sw > 0, sw, 1.0)
        mu = (We * rv0).sum(0) / denom
        var = (We * (rv0 - mu) ** 2).sum(0) / denom
        sd = np.sqrt(np.maximum(var, 1e-9))
        good = (sw >= 5) & np.isfinite(vals[i])
        z[i, good] = (vals[i, good] - mu[good]) / sd[good]
    return z


def auc_col(y, s):
    m = np.isfinite(s)
    yy, ss = y[m], s[m]
    if len(np.unique(yy)) < 2:
        return np.nan
    return roc_auc_score(yy, ss)


def load():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    w = d[(d.region == REGION) & d.age.between(0, 100)].merge(lu, on="bdsp_id", how="left")
    w = w.assign(
        _t_abnormal=w.is_abnormal == 1,
        _t_gen_pathologic=w.gen_class == "pathologic",
        _t_focal=w.has_focal_slow == 1,
        _is_cohort=w.src == "cohort",
        _is_cn=w.clean_normal == 1,
    )
    return w


def stage_pack(w):
    """Per stage: numpy arrays (bdsp, age, feature matrix) plus boolean role masks."""
    pack = {}
    for st in STAGES:
        s = w[w.stage == st]
        pack[st] = dict(
            bdsp=s.bdsp_id.values,
            age=s.age.values.astype(float),
            feat=s[FEATURES].values.astype(float),
            cohort=s._is_cohort.values,
            cn=s._is_cn.values,
            t={t: s[f"_t_{t}"].values for t in TARGETS},
        )
    return pack


# ---------- naive (reproduce scripts/84: select-and-report on the same data) ----------
def naive_table(pack):
    """One 30% held-out normal split (seed 0, as in scripts/84); per stage pick the feature with the max
    AUROC on that same data. Returns {target: {stage: (feat, auc)}}."""
    rng0 = np.random.default_rng(0)
    # routine clean-normal ids (use W stage universe == full recording set, matches scripts/84 which splits ids)
    cn_ids_all = np.unique(np.concatenate([
        pack[st]["bdsp"][pack[st]["cohort"] & pack[st]["cn"]] for st in STAGES]))
    test_neg = set(rng0.choice(cn_ids_all, int(0.3 * len(cn_ids_all)), replace=False).tolist())
    train_ref = set(cn_ids_all.tolist()) - test_neg
    out = {}
    for tgt in TARGETS:
        out[tgt] = {}
        for st in STAGES:
            p = pack[st]
            bd = p["bdsp"]
            ref_m = np.isin(bd, list(train_ref)) & p["cohort"] & p["cn"]
            neg_m = np.isin(bd, list(test_neg)) & p["cohort"] & p["cn"]
            pos_m = p["cohort"] & p["t"][tgt]
            if pos_m.sum() < 15 or neg_m.sum() < 20:
                continue
            tst = np.where(pos_m | neg_m)[0]
            y = pos_m[tst].astype(int)
            Z = normal_z_multi(p["feat"][tst], p["age"][tst], p["feat"][ref_m], p["age"][ref_m])
            aucs = {f: auc_col(y, Z[:, FI[f]]) for f in FEATURES}
            best = max((f for f in FEATURES if np.isfinite(aucs[f])), key=lambda f: aucs[f])
            out[tgt][st] = (best, aucs[best])
    return out


# ---------- inner feature selection within outer-train ids ----------
def inner_select(p, tgt, train_ids, rng):
    bd = p["bdsp"]
    is_pos = p["cohort"] & p["t"][tgt]
    is_neg = p["cohort"] & p["cn"]
    tr_ids = np.asarray(sorted(train_ids))
    if len(tr_ids) < INNER_K * 2:
        return None
    kf = KFold(n_splits=INNER_K, shuffle=True, random_state=int(rng.integers(1 << 31)))
    acc = {f: [] for f in FEATURES}
    for itr, ival in kf.split(tr_ids):
        val_ids, ref_ids = tr_ids[ival], tr_ids[itr]
        ref_m = np.isin(bd, ref_ids) & is_neg
        if ref_m.sum() > REF_CAP:
            idx = np.where(ref_m)[0]
            keep = rng.choice(idx, REF_CAP, replace=False)
            ref_m = np.zeros_like(ref_m); ref_m[keep] = True
        val_m = np.isin(bd, val_ids)
        pos_m = val_m & is_pos
        neg_m = val_m & is_neg
        if pos_m.sum() < 10 or neg_m.sum() < 10 or ref_m.sum() < 10:
            continue
        tst = np.where(pos_m | neg_m)[0]
        y = pos_m[tst].astype(int)
        Z = normal_z_multi(p["feat"][tst], p["age"][tst], p["feat"][ref_m], p["age"][ref_m])
        for f in FEATURES:
            a = auc_col(y, Z[:, FI[f]])
            if np.isfinite(a):
                acc[f].append(a)
    means = {f: (np.mean(v) if v else np.nan) for f, v in acc.items()}
    ok = [f for f in FEATURES if np.isfinite(means[f])]
    if not ok:
        return None
    return max(ok, key=lambda f: means[f])


# ---------- nested CV ----------
def nested(pack):
    ref_capped = 0
    rows = []
    for tgt in TARGETS:
        # union of positive + negative ids for this target (split on these)
        pos_ids, neg_ids = set(), set()
        for st in STAGES:
            p = pack[st]
            pos_ids |= set(p["bdsp"][p["cohort"] & p["t"][tgt]].tolist())
            neg_ids |= set(p["bdsp"][p["cohort"] & p["cn"]].tolist())
        neg_ids -= pos_ids
        all_ids = np.array(sorted(pos_ids | neg_ids))
        for rep in range(N_REPEAT):
            kf = KFold(n_splits=N_OUTER, shuffle=True, random_state=1000 + rep)
            for k, (tr, te) in enumerate(kf.split(all_ids)):
                train_ids, test_ids = set(all_ids[tr].tolist()), all_ids[te]
                rng = np.random.default_rng(7_000 + rep * N_OUTER + k)
                for st in STAGES:
                    p = pack[st]
                    bd = p["bdsp"]
                    is_pos = p["cohort"] & p["t"][tgt]
                    is_neg = p["cohort"] & p["cn"]
                    # outer reference = outer-train clean-normals (capped)
                    ref_m = np.isin(bd, list(train_ids)) & is_neg
                    if ref_m.sum() > REF_CAP:
                        ref_capped += 1
                        idx = np.where(ref_m)[0]
                        keep = rng.choice(idx, REF_CAP, replace=False)
                        ref_m = np.zeros_like(ref_m); ref_m[keep] = True
                    # outer test = pos + neg among held-out ids
                    test_m = np.isin(bd, test_ids)
                    pos_m = test_m & is_pos
                    neg_m = test_m & is_neg
                    if pos_m.sum() < 10 or neg_m.sum() < 10 or ref_m.sum() < 10:
                        continue
                    tst = np.where(pos_m | neg_m)[0]
                    y = pos_m[tst].astype(int)
                    Z = normal_z_multi(p["feat"][tst], p["age"][tst], p["feat"][ref_m], p["age"][ref_m])
                    # (a) feature chosen by inner loop
                    feat = inner_select(p, tgt, train_ids, np.random.default_rng(
                        13_000 + rep * N_OUTER + k))
                    auc_sel = auc_col(y, Z[:, FI[feat]]) if feat else np.nan
                    # (b) fixed a-priori feature
                    ff = FIXED_FEAT[st]
                    auc_fix = auc_col(y, Z[:, FI[ff]])
                    rows.append(dict(target=tgt, stage=st, rep=rep, fold=k,
                                     chosen=feat, auc_sel=auc_sel,
                                     fixed=ff, auc_fix=auc_fix,
                                     n_pos=int(pos_m.sum()), n_neg=int(neg_m.sum())))
    return pd.DataFrame(rows), ref_capped


def agg(series):
    v = series.dropna().values
    if len(v) == 0:
        return np.nan, np.nan, np.nan
    return float(np.mean(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def main():
    Path("results").mkdir(exist_ok=True)
    w = load()
    pack = stage_pack(w)
    naive = naive_table(pack)
    res, ref_capped = nested(pack)
    res.to_csv("results/nested_cv_detection.csv", index=False)

    L = []  # markdown + stdout lines
    def emit(s=""):
        L.append(s)

    emit("# Nested-CV detection: how much of scripts/84 is selection optimism?")
    emit()
    emit(f"Split on `bdsp_id`; {N_OUTER}-fold outer x {N_REPEAT} repeats = {N_OUTER*N_REPEAT} outer estimates; "
         f"inner {INNER_K}-fold chooses the whole-head feature per stage on outer-train ids only; the age-kernel "
         f"normal reference (bw={BW}) is rebuilt from outer-train clean-normals each fold. "
         f"'naive' reproduces scripts/84 (best feature picked and scored on the same 30%-held-out split, seed 0). "
         f"CI = 2.5/97.5 pct spread across the {N_OUTER*N_REPEAT} outer folds.")
    if ref_capped:
        emit()
        emit(f"NOTE: reference subsampled to {REF_CAP} recordings in {ref_capped} outer(stage,fold) instances "
             f"(only stages whose outer-train clean-normal count exceeded the cap).")
    else:
        emit()
        emit(f"(Reference cap of {REF_CAP} was never hit; every fold used all outer-train clean-normals.)")

    # ---- headline: gen_pathologic (the published target) ----
    emit()
    emit("## Primary: normal vs pathologic-generalized slowing (routine norm, whole-head)")
    emit()
    emit("| stage | published (84) | naive repro | nested (feature-select) | nested (fixed feat) | "
         "optimism = naive-nested | of which feature-selection |")
    emit("|---|---|---|---|---|---|---|")
    tgt = "gen_pathologic"
    sub = res[res.target == tgt]
    for st in STAGES:
        pf, pa = PUBLISHED[st]
        nf, na = naive[tgt].get(st, (None, np.nan))
        ss = sub[sub.stage == st]
        ms, ls, hs = agg(ss.auc_sel)
        mf, lf, hf = agg(ss.auc_fix)
        opt = na - ms
        fsel = mf - ms   # fixed-feature nested minus selected-feature nested = cost of doing selection
        emit(f"| {st} | {pf} {pa:.3f} | {nf} {na:.3f} | {ms:.3f} [{ls:.3f},{hs:.3f}] | "
             f"{FIXED_FEAT[st]} {mf:.3f} [{lf:.3f},{hf:.3f}] | {opt:+.3f} | {fsel:+.3f} |")
    npos = int(sub.n_pos.max()); nneg = int(sub.n_neg.max())
    emit()
    emit(f"per outer fold ~ {npos} pos / {nneg} held-out routine-normal neg (of ~5x that pooled).")

    # ---- selection stability (gen_pathologic) ----
    emit()
    emit("## Inner-loop feature selection stability (gen_pathologic)")
    emit()
    emit("Count of the " + str(N_OUTER * N_REPEAT) + " outer folds in which each feature was chosen by the "
         "inner loop, per stage.")
    emit()
    emit("| stage | " + " | ".join(FEATURES) + " | modal |")
    emit("|---|" + "---|" * (len(FEATURES) + 1))
    for st in STAGES:
        cc = sub[sub.stage == st].chosen.value_counts()
        cells = [str(int(cc.get(f, 0))) for f in FEATURES]
        modal = cc.idxmax() if len(cc) else "-"
        emit(f"| {st} | " + " | ".join(cells) + f" | {modal} |")

    # ---- other targets ----
    for tgt in ["abnormal", "focal"]:
        emit()
        emit(f"## {tgt}: nested vs naive (whole-head)")
        emit()
        emit("| stage | naive feat/AUROC | nested (feature-select) | nested (fixed feat) | optimism |")
        emit("|---|---|---|---|---|")
        sub = res[res.target == tgt]
        for st in STAGES:
            nf, na = naive[tgt].get(st, (None, np.nan))
            ss = sub[sub.stage == st]
            ms, ls, hs = agg(ss.auc_sel)
            mf, lf, hf = agg(ss.auc_fix)
            opt = (na - ms) if np.isfinite(na) else np.nan
            emit(f"| {st} | {nf} {na:.3f} | {ms:.3f} [{ls:.3f},{hs:.3f}] | "
                 f"{FIXED_FEAT[st]} {mf:.3f} [{lf:.3f},{hf:.3f}] | {opt:+.3f} |")

    # ---- verdict ----
    emit()
    emit("## Verdict")
    sub = res[res.target == "gen_pathologic"]
    verdict = []
    for st in STAGES:
        _, pa = PUBLISHED[st]
        ms, ls, hs = agg(sub[sub.stage == st].auc_sel)
        verdict.append((st, pa, ms, pa - ms, ls))
    worst = max(verdict, key=lambda r: r[3])
    mean_opt = float(np.mean([r[3] for r in verdict]))
    emit()
    emit(f"Mean feature-selection-inclusive optimism across stages (gen_pathologic): {mean_opt:+.3f}. "
         f"Largest single-stage shrinkage: {worst[0]} ({worst[1]:.3f} -> {worst[2]:.3f}, {worst[1]-worst[2]:+.3f}). "
         f"Published whole-head detection numbers "
         f"{'SURVIVE' if mean_opt < 0.02 else 'shrink modestly' if mean_opt < 0.04 else 'shrink materially'} "
         f"nested CV; the honest per-stage values are the 'nested (feature-select)' column above.")

    txt = "\n".join(L) + "\n"
    Path("results/nested_cv_detection.md").write_text(txt)
    print(txt)
    print("wrote results/nested_cv_detection.md + results/nested_cv_detection.csv")


if __name__ == "__main__":
    main()
