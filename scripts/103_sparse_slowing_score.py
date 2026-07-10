"""The sparse slowing score S — a small, interpretable weighted combination of normative deviations.

MBW's design (docs/report_architecture.md), which the project had drifted away from: fit an L1-regularised
logistic model, keep only the features it retains, and report the **linear predictor** (the weighted sum of
z-scores) rather than the probability. The probability saturates near 0/1 and destroys grading; the logit is
unbounded, linear in the z's, and monotone in evidence.

TWO NAMED OBJECTS, AND A RULE
  z  - deviation from the age- and stage-matched clinician-normal distribution. UNSUPERVISED, fit to nothing
       but the normal population. This is a MEASUREMENT. It is what supports V4a ("we see slowing the reader
       does not name") and the regional box plots.
  S  - a sparse linear combination of those z's, coefficients fit to predict the expert/report call.
       SUPERVISED. This is detection and interpretability.
  RULE: S may never be used to argue that we see what experts miss. A score trained on expert labels
        inherits their blind spots by construction; that argument stays z's job.

WHAT IS NOT MODELLED: the BAND (delta vs theta vs mixed). Experts agree with each other on band at
kappa 0.09-0.38 (results/moe_band_vs_ours.md). An L1 model fit to a target with that little reliable signal
selects noise. We report the ceiling and decline the axis.

METHOD
  * candidates: z of {log_delta, log_theta, rel_delta, TAR, DAR} x {whole_head, L/R temporal,
    L/R parasagittal, midline} x {W, N1}, PLUS homologous asymmetries (|z_L - z_R|) for the temporal and
    parasagittal chains -- the previous keep-list omitted asymmetry entirely, yet Phase A shows asymmetry is
    what carries focal detection (absolute max-lobe 0.59-0.63 vs asymmetry 0.74-0.83).
  * correlation clustering (|r| >= 0.9) -> one interpretable representative per cluster, because log_delta /
    rel_delta / DAR / TAR all track slowing and raw importances split credit arbitrarily.
  * NESTED CV, split on bdsp_id: the normal reference, the correlation clusters, the C grid and the L1
    selection are all re-derived inside each outer-training fold. Nothing about the test fold informs them.
  * stability selection: bootstrap L1 fits within each outer-train; a feature is KEPT if selected in
    >= STAB_MIN of fits, averaged over folds.
  * the final frozen model is fit on ALL in-cohort data, restricted to the stable features, and written to
    data/derived/sparse_score_coefs.json.

EXTERNAL CONFIRMATION is a single run against the 18-expert panel, with coefficients frozen beforehand.
DISCLOSURE: OccasionNoise has already been examined with hand-picked scores (scripts/94), so this is a
confirmatory check, not a first look. It is reported as such.

Run: PYTHONPATH=src python scripts/103_sparse_slowing_score.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATS = ["log_delta", "log_theta", "rel_delta", "TAR", "DAR"]
ABS_REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal", "midline"]
PAIRS = {"temporal": ("L_temporal", "R_temporal"), "parasagittal": ("L_parasagittal", "R_parasagittal")}
STAGES = ["W", "N1"]
GRID = np.arange(0, 101, 2.0)
BW = 5.0
CGRID = [0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]
KMAX = 8                 # target size for the clinically readable model
N_BOOT = 30
STAB_MIN = 0.60
CORR_MAX = 0.80          # tighter: at 0.90 the representatives stayed collinear and L1 produced
                         # sign-flipped suppressor coefficients (a slowing feature with a NEGATIVE weight)
OUT_FIG = "figures/growth_v2/sparse_score.png"
rng = np.random.default_rng(0)


# ---------------------------------------------------------------- z, from a reference population
def ref_curves(ref: pd.DataFrame):
    """(region, stage, feature) -> (mu(grid), sd(grid)) from clean-normals only."""
    R = {}
    for (rg, st), g in ref.groupby(["region", "stage"], observed=True):
        a = g.age.values
        if len(a) < 50: continue
        W = np.exp(-0.5 * ((GRID[:, None] - a[None, :]) / BW) ** 2)     # (grid, n)
        sw = W.sum(1)
        ok = sw >= 20
        for f in FEATS:
            v = g[f].values
            mu = np.full(len(GRID), np.nan); sd = np.full(len(GRID), np.nan)
            mu[ok] = (W[ok] @ v) / sw[ok]
            var = (W[ok] @ (v ** 2)) / sw[ok] - mu[ok] ** 2
            sd[ok] = np.sqrt(np.clip(var, 1e-9, None))
            R[(rg, st, f)] = (mu, sd)
    return R


def z_table(d: pd.DataFrame, R: dict) -> pd.DataFrame:
    """Wide per-recording table of z columns: 'feat@region@stage' plus '|asym|@chain@feat@stage'."""
    cols = {}
    for (rg, st, f), (mu, sd) in R.items():
        if rg not in ABS_REGIONS + [r for p in PAIRS.values() for r in p]:
            continue
        sub = d[(d.region == rg) & (d.stage == st)]
        if len(sub) == 0: continue
        m = np.interp(sub.age.values, GRID, mu, left=np.nan, right=np.nan)
        s = np.interp(sub.age.values, GRID, sd, left=np.nan, right=np.nan)
        z = (sub[f].values - m) / s
        cols.setdefault((rg, st, f), pd.Series(z, index=sub.bdsp_id.values))
    ids = sorted({i for s in cols.values() for i in s.index})
    X = pd.DataFrame(index=pd.Index(ids, name="bdsp_id"))
    for (rg, st, f), s in cols.items():
        if rg in ABS_REGIONS:
            X[f"{f}@{rg}@{st}"] = s.reindex(X.index)
    for chain, (L, Rr) in PAIRS.items():
        for f in FEATS:
            for st in STAGES:
                a = cols.get((L, st, f)); b = cols.get((Rr, st, f))
                if a is None or b is None: continue
                X[f"|asym|@{chain}@{f}@{st}"] = (a.reindex(X.index) - b.reindex(X.index)).abs()
    return X


# ---------------------------------------------------------------- selection machinery
def corr_representatives(X: pd.DataFrame, y: np.ndarray):
    """Collapse |r| >= CORR_MAX clusters to the member with the best univariate AUROC."""
    Xf = X.fillna(X.median())
    C = np.abs(np.corrcoef(Xf.values.T))
    C = np.nan_to_num(C)
    auc = {}
    for i, c in enumerate(X.columns):
        v = Xf.iloc[:, i].values
        auc[c] = max(roc_auc_score(y, v), roc_auc_score(y, -v))
    keep, used = [], set()
    for c in sorted(X.columns, key=lambda c: -auc[c]):
        i = X.columns.get_loc(c)
        if i in used: continue
        cluster = np.where(C[i] >= CORR_MAX)[0]
        used.update(cluster.tolist())
        keep.append(c)
    return keep


def l1_fit(X, y, C):
    return LogisticRegression(penalty="l1", solver="liblinear", C=C, max_iter=3000,
                              class_weight="balanced").fit(X, y)


def stability(X, y, C, n=N_BOOT):
    hits = np.zeros(X.shape[1])
    for _ in range(n):
        idx = rng.choice(len(y), len(y), replace=True)
        if len(np.unique(y[idx])) < 2: continue
        m = l1_fit(X[idx], y[idx], C)
        hits += (np.abs(m.coef_[0]) > 1e-8)
    return hits / n


def pick_C(X, y, groups):
    """1-SE rule: the MOST regularised C whose inner-CV AUROC is within one standard error of the best.

    Choosing C to maximise AUROC always prefers weak regularisation and returns a dense model. Parsimony is
    the point of the exercise, so we buy sparsity at the cost of at most one standard error of AUROC.
    """
    sgk = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=0)
    means, ses = {}, {}
    for C in CGRID:
        aucs = []
        for tr, te in sgk.split(X, y, groups):
            if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2: continue
            m = l1_fit(X[tr], y[tr], C)
            aucs.append(roc_auc_score(y[te], m.decision_function(X[te])))
        if aucs:
            means[C] = float(np.mean(aucs)); ses[C] = float(np.std(aucs) / max(np.sqrt(len(aucs)), 1))
    if not means:
        return CGRID[0]
    bestC = max(means, key=means.get)
    thresh = means[bestC] - ses[bestC]
    ok = [C for C in CGRID if means.get(C, -1) >= thresh]
    return min(ok) if ok else bestC          # smallest C == strongest L1 penalty


def parsimony_curve(Xtr, ytr, Xte, yte):
    """Nested test AUROC and model size at every C — 'how few features actually suffice?'"""
    rows = []
    for C in CGRID:
        m = l1_fit(Xtr, ytr, C)
        k = int((np.abs(m.coef_[0]) > 1e-8).sum())
        rows.append((C, k, roc_auc_score(yte, m.decision_function(Xte))))
    return rows


# ---------------------------------------------------------------- main
def load():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]]
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    d = d[(d.src == "cohort") & d.stage.isin(STAGES) & ~d.bdsp_id.isin(ex)]
    lu = lu.merge(cp, on="bdsp_id", how="left"); lu["clean_pair"] = lu.clean_pair.fillna(False)
    return d, lu


def run_target(d, lu, name, pos_mask, neg_mask=None):
    """Nested CV for one target. Returns dict of results + the stable feature set.

    `neg_mask` defaults to clean-normals. For the FOCAL-SPECIFIC target the negatives also include
    generalized-slowing recordings, because focal-vs-clean-normal is learnable as "generally slow" and does
    not transfer to a panel that must separate focal from generalized (see results/sparse_score_external.md).
    """
    ids_pos = set(lu[pos_mask & (lu.clean_pair == True)].bdsp_id)     # labels from report text -> clean_pair
    if neg_mask is None:
        ids_neg = set(lu[lu.clean_normal == True].bdsp_id)
    else:
        ids_neg = set(lu[neg_mask].bdsp_id) - ids_pos
    ids = sorted(ids_pos | ids_neg)
    dd = d[d.bdsp_id.isin(ids)]
    y_map = {i: int(i in ids_pos) for i in ids}

    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=7)
    ylab = np.array([y_map[i] for i in ids]); groups = np.array(ids)
    fold_auc, fold_stab, fold_cols, fold_C, curves = [], [], [], [], []

    for tr, te in outer.split(np.zeros(len(ids)), ylab, groups):
        tr_ids, te_ids = set(np.array(ids)[tr]), set(np.array(ids)[te])
        ref = dd[dd.bdsp_id.isin(tr_ids & ids_neg & set(lu[lu.clean_normal == True].bdsp_id))]  # TRAIN normals
        R = ref_curves(ref)
        X = z_table(dd, R)
        Xtr = X.loc[X.index.isin(tr_ids)]; Xte = X.loc[X.index.isin(te_ids)]
        ytr = np.array([y_map[i] for i in Xtr.index]); yte = np.array([y_map[i] for i in Xte.index])
        med = Xtr.median()
        Xtr = Xtr.fillna(med); Xte = Xte.fillna(med)
        reps = corr_representatives(Xtr, ytr)                          # clusters from TRAIN only
        Xtr, Xte = Xtr[reps], Xte[reps]
        mu, sg = Xtr.mean(), Xtr.std().replace(0, 1)
        Xtr_s, Xte_s = ((Xtr - mu) / sg).values, ((Xte - mu) / sg).values
        C = pick_C(Xtr_s, ytr, np.array(Xtr.index))
        st = stability(Xtr_s, ytr, C)
        m = l1_fit(Xtr_s, ytr, C)
        fold_auc.append(roc_auc_score(yte, m.decision_function(Xte_s)))   # LINEAR PREDICTOR, not p
        fold_stab.append(pd.Series(st, index=reps)); fold_cols.append(reps); fold_C.append(C)
        curves.append(parsimony_curve(Xtr_s, ytr, Xte_s, yte))

    cur = pd.DataFrame([r for f in curves for r in f], columns=["C", "k", "auc"])
    cur = cur.groupby("C").agg(k=("k", "mean"), auc=("auc", "mean"), auc_sd=("auc", "std")).reset_index()
    # the clinically readable model: the LARGEST C whose mean size is still <= KMAX (best AUROC at that size)
    small = cur[cur.k <= KMAX]
    C_par = float(small.loc[small.auc.idxmax(), "C"]) if len(small) else float(cur.C.min())
    k_par = float(small.loc[small.auc.idxmax(), "k"]) if len(small) else float(cur.k.min())
    auc_par = float(small.loc[small.auc.idxmax(), "auc"]) if len(small) else float(cur.auc.min())

    stab = pd.concat(fold_stab, axis=1).mean(axis=1).sort_values(ascending=False)
    stable = [c for c in stab.index if stab[c] >= STAB_MIN]

    # frozen final model on ALL in-cohort data, stable features only
    ref = dd[dd.bdsp_id.isin(ids_neg & set(lu[lu.clean_normal == True].bdsp_id))]   # reference is ALWAYS normals
    R = ref_curves(ref)
    X = z_table(dd, R)
    have = [i for i in ids if i in X.index]                 # some recordings lack a needed region/stage
    if len(have) < len(ids):
        print(f"  note: {len(ids)-len(have)} of {len(ids)} recordings lack a required region/stage row "
              f"and are dropped from the final fit", flush=True)
    X = X.loc[have]
    ylab_f = np.array([y_map[i] for i in have])
    med = X.median(); X = X.fillna(med)
    Xs = X[[c for c in stable if c in X.columns]]
    mu, sg = Xs.mean(), Xs.std().replace(0, 1)
    C = C_par                                  # freeze the clinically readable model, not the dense one
    final = l1_fit(((Xs - mu) / sg).values, ylab_f, C)
    coef = pd.Series(final.coef_[0], index=Xs.columns)
    coef = coef[coef.abs() > 1e-8].sort_values(key=np.abs, ascending=False)

    return dict(name=name, curve=cur, C_par=C_par, k_par=k_par, auc_par=auc_par,
                nested_auc=float(np.mean(fold_auc)),
                nested_lo=float(np.percentile(fold_auc, 2.5)), nested_hi=float(np.percentile(fold_auc, 97.5)),
                folds=fold_auc, C=C, stability=stab, stable=stable, coef=coef,
                center=mu[coef.index].to_dict(), scale=sg[coef.index].to_dict(),
                intercept=float(final.intercept_[0]), n_pos=int(ylab.sum()), n_neg=int((1 - ylab).sum()),
                impute=med[coef.index].to_dict())


def main():
    d, lu = load()
    gen_only = (lu.gen_class == "pathologic") & (lu.has_focal_slow != 1)
    targets = [
        ("generalized", lu.gen_class == "pathologic", None),
        ("focal", lu.has_focal_slow == 1, None),                       # vs clean-normals (the naive task)
        # focal-SPECIFIC: negatives include generalized slowing, so the model cannot win on global slowing
        ("focal_specific", lu.has_focal_slow == 1, (lu.clean_normal == True) | gen_only),
    ]
    res = {}
    for nm, mask, neg in targets:
        print(f"--- {nm} ---", flush=True)
        res[nm] = run_target(d, lu, nm, mask, neg)
        r = res[nm]
        print(f"  nested AUROC {r['nested_auc']:.3f}  |  kept {len(r['coef'])} of "
              f"{len(r['stability'])} candidates  |  C={r['C']}", flush=True)

    frozen = {nm: dict(intercept=r["intercept"], coef=r["coef"].to_dict(),
                       center=r["center"], scale=r["scale"], impute=r["impute"], C=r["C"])
              for nm, r in res.items()}
    Path("data/derived").mkdir(parents=True, exist_ok=True)
    Path("data/derived/sparse_score_coefs.json").write_text(json.dumps(frozen, indent=2))

    # ---------------- report
    out = ["# The sparse slowing score S\n",
           "S is the **linear predictor** of an L1-regularised logistic model fit on normative deviations "
           "(z-scores), not the probability. The probability saturates near 0 and 1 and destroys grading; the "
           "logit is unbounded, linear in the z's, and monotone in evidence.\n",
           "**S is not the measurement.** `z` is the measurement — unsupervised, fit to nothing but the normal "
           "population. `S` is trained to predict the expert's call and therefore inherits the expert's blind "
           "spots. S is used for detection and interpretability; it is never used to argue that we see slowing "
           "the reader misses. That argument belongs to z (§V4a).\n",
           "Selection (correlation clustering, C, L1 path, stability) is re-derived **inside each outer "
           "training fold**; the normal reference is rebuilt from that fold's clean-normals. Split on patient.\n"]

    for nm, r in res.items():
        out.append(f"\n## {nm} slowing  (n = {r['n_pos']} positive / {r['n_neg']} clean-normal)\n")
        out.append(f"- **Nested-CV AUROC of the linear predictor: {r['nested_auc']:.3f}** "
                   f"[{r['nested_lo']:.3f}, {r['nested_hi']:.3f}] across 5 folds")
        out.append(f"- **Parsimonious frozen model: {len(r['coef'])} features**, nested AUROC "
                   f"{r['auc_par']:.3f} at mean size {r['k_par']:.1f} (C = {r['C_par']})")
        out.append(f"- L1 with the 1-SE rule retains {len(r['stable'])} of {len(r['stability'])} "
                   f"correlation-cluster representatives (from ~100 candidates); the dense model buys "
                   f"{r['nested_auc'] - r['auc_par']:+.3f} AUROC over the parsimonious one")
        out.append(f"\n**How few features suffice?** (nested test AUROC vs model size)\n")
        out.append("| C | mean # features | nested AUROC |"); out.append("|---|---|---|")
        for _, q in r["curve"].iterrows():
            out.append(f"| {q.C:g} | {q.k:.1f} | {q.auc:.3f} |")
        out.append(f"\n| retained feature | coefficient | stability |")
        out.append("|---|---|---|")
        for c, v in r["coef"].items():
            out.append(f"| `{c}` | {v:+.3f} | {r['stability'][c]:.2f} |")
        dropped = [c for c in r["stability"].index if c not in r["stable"]][:5]
        if dropped:
            out.append(f"\nRepresentative features the L1 path *dropped* (stability < {STAB_MIN:.0%}): "
                       + ", ".join(f"`{c}` ({r['stability'][c]:.2f})" for c in dropped))

    # ---------------- figure
    fig, axes = plt.subplots(len(res), 3, figsize=(19, 4.5 * len(res)))
    axes = np.atleast_2d(axes)
    for i, (nm, r) in enumerate(res.items()):
        ax = axes[i, 0]
        c = r["coef"].iloc[::-1]
        ax.barh(range(len(c)), c.values, color=["#4c78a8" if v > 0 else "#e45756" for v in c.values])
        ax.set_yticks(range(len(c))); ax.set_yticklabels(c.index, fontsize=7.5)
        ax.axvline(0, color="k", lw=.8)
        ax.set_title(f"{nm}: the {len(c)} features L1 retained  (nested AUROC {r['nested_auc']:.3f})")
        ax.set_xlabel("coefficient (per SD of the z)")

        ax = axes[i, 2]
        cur = r["curve"]
        ax.plot(cur.k, cur.auc, "o-", color="#4c78a8")
        ax.axvline(r["k_par"], color="crimson", ls="--", lw=1,
                   label=f"frozen: {r['k_par']:.0f} features, AUROC {r['auc_par']:.3f}")
        ax.set_xscale("log"); ax.set_xlabel("number of features retained (log scale)")
        ax.set_ylabel("nested test AUROC"); ax.legend(fontsize=7.5, loc="lower right")
        ax.set_title(f"{nm}: how few features suffice?")

        ax = axes[i, 1]
        s = r["stability"].head(18).iloc[::-1]
        ax.barh(range(len(s)), s.values, color=["#59a14f" if v >= STAB_MIN else "#bbbbbb" for v in s.values])
        ax.axvline(STAB_MIN, color="crimson", ls="--", lw=1, label=f"keep ≥ {STAB_MIN:.0%}")
        ax.set_yticks(range(len(s))); ax.set_yticklabels(s.index, fontsize=7.5)
        ax.set_xlim(0, 1); ax.set_xlabel("bootstrap L1 selection frequency")
        ax.set_title(f"{nm}: stability selection"); ax.legend(fontsize=7, loc="lower right")
    fig.suptitle("The sparse slowing score S: a small, interpretable weighted combination of normative deviations\n"
                 "selection performed inside each cross-validation fold; the reported score is the linear "
                 "predictor, not the probability", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT_FIG, dpi=140); plt.close(fig)

    out.append("\n## Frozen for external confirmation\n")
    out.append("Coefficients written to `data/derived/sparse_score_coefs.json`. The external test against the "
               "18-expert panel is run by `scripts/104_sparse_score_external.py` with these coefficients "
               "**frozen**. Disclosure: OccasionNoise has already been examined with hand-picked scores "
               "(scripts/94), so that run is confirmatory, not a first look.")
    out.append("\n## What is deliberately not modelled\n")
    out.append("The **band** (delta vs theta vs mixed). Experts agree with one another on band at "
               "κ = 0.09–0.38 (`results/moe_band_vs_ours.md`). Fitting an L1 model to a target with that "
               "little reliable signal would select noise and dress it in confidence intervals. We report the "
               "ceiling and decline the axis.")
    Path("results/sparse_slowing_score.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[-6:]))
    print(f"\nwrote results/sparse_slowing_score.md, {OUT_FIG}, data/derived/sparse_score_coefs.json")


if __name__ == "__main__":
    main()
