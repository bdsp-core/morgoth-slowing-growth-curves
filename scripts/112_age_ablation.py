#!/usr/bin/env python3
"""Does the detector read the deviation field, or is it exploiting age? (Beniczky review, comment 14)

The concern, stated precisely. Abnormal recordings are ~17 y older than clean-normals (Table 2). The
deviation features are already age-normalised, but chronological age is then handed to BOTH logistic heads
as an extra feature. A classifier can therefore recover the strong age-label association directly and use
age as a diagnostic shortcut, which would undercut the claim that performance comes from the deviation
field rather than from demographics.

Five arms, reported even-handedly. None was pre-registered as primary and the outcome is reported whichever
way it falls, as with the severity null:

  age-only          age as the SOLE feature. The floor: whatever this reaches is available without ever
                    looking at the EEG.
  deviation-only    the production feature set with `age` dropped.
  deviation+age     the production model, unchanged.
  age-stratified    deviation+age AUROC within decade bands, where age varies little inside a band, so a
                    shortcut cannot operate.
  age-matched       external sets re-scored after matching the age distribution of positives and negatives
                    by inverse-propensity reweighting, which removes the marginal age-label association.

Falsification: if deviation-only collapses toward age-only, performance is substantially a demographic
shortcut and the deviation-field claim must be scoped. If deviation-only is close to deviation+age, the
claim stands and is demonstrated rather than assumed.

Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/112_age_ablation.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

RES = Path("results/story"); RES.mkdir(parents=True, exist_ok=True)


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


m54 = _load("m54", "scripts/54_single_model_train_eval.py")
m55 = _load("m55", "scripts/55_recording_model.py")


def boot_auc(y, s, n=2000, seed=0):
    """Recording-level bootstrap CI, matching the rest of the paper."""
    y, s = np.asarray(y), np.asarray(s)
    ok = np.isfinite(s) & np.isfinite(y)
    y, s = y[ok], s[ok]
    if len(np.unique(y)) < 2:
        return np.nan, (np.nan, np.nan)
    rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        j = rng.choice(len(y), len(y), replace=True)
        if 0 < y[j].sum() < len(j):
            out.append(roc_auc_score(y[j], s[j]))
    return roc_auc_score(y, s), (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def fit_score(tr, te, cols, ylab):
    """Train one head on `tr[cols]` and score `te`. Identical estimator to production (m54.Head)."""
    med = tr[cols].median()
    h = m54.Head().fit(tr[cols].fillna(med).values, tr[ylab].astype(int).values)
    return h.score(te[cols].fillna(med).values)


def ipw_age_weights(age, y, bins=np.arange(0, 101, 10)):
    """Inverse-propensity weights that equalise the age distribution of positives and negatives."""
    b = np.digitize(np.asarray(age, float), bins)
    w = np.ones(len(y), float)
    y = np.asarray(y).astype(int)
    for k in np.unique(b):
        m = b == k
        if m.sum() < 10 or len(np.unique(y[m])) < 2:
            continue
        for cls in (0, 1):                       # reweight each class to the band's overall share
            sel = m & (y == cls)
            if sel.sum():
                w[sel] = m.mean() / (sel.sum() / len(y))
    return w


def weighted_auc(y, s, w):
    """AUROC under sample weights, via the Mann-Whitney form on weighted pair counts."""
    y, s, w = np.asarray(y), np.asarray(s, float), np.asarray(w, float)
    ok = np.isfinite(s)
    y, s, w = y[ok], s[ok], w[ok]
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return np.nan
    sp, wp = s[pos], w[pos]; sn, wn = s[neg], w[neg]
    num = float(sum(wp[i] * ((sp[i] > sn) * wn).sum() + 0.5 * wp[i] * ((sp[i] == sn) * wn).sum()
                    for i in range(len(sp))))
    return num / (wp.sum() * wn.sum())


def main() -> None:
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    R = m55.aggregate(S)
    AMT = [f"{c}_{s}" for c in m55.AMT0 for s in ("mean", "p90", "max", "prev")]
    FOC = [f"{c}_{s}" for c in m55.FOC0 for s in ("mean", "p90", "max", "prev")]
    for c in AMT + FOC + ["age"]:
        if c not in R.columns:
            R[c] = np.nan
    tr = R[(R.dataset == "report") & (R.split == "train")]
    rt = R[(R.dataset == "report") & (R.split == "test")]

    # ON-100 carries no report labels (y_focal/y_gen are NaN for every ON_ row); its ground truth is the
    # expert-vote majority, exactly as scripts/55 builds it. Attach that so the external arms -- which is
    # where the reviewer's age-matching question actually bites -- can run at all.
    on = R[R.index.astype(str).str.startswith("ON_")].copy()
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    for tag, mx in [("focal", "FN"), ("generalized", "GN")]:
        w = V.dropna(subset=[f"r1.{mx}"]).pivot_table(index="fid", columns="rater", values=f"r1.{mx}")
        w.index = [f"ON_{int(i)}" for i in w.index]
        keep = w.index.intersection(on.index)
        on.loc[keep, f"y_{'focal' if tag == 'focal' else 'gen'}"] = (w.loc[keep].mean(axis=1) >= 0.5).astype(int)
    on = on[on.y_focal.notna() & on.y_gen.notna()]

    arms = {"age-only": lambda base: ["age"],
            "deviation-only": lambda base: list(base),
            "deviation+age": lambda base: list(base) + ["age"]}
    rows = []
    for tag, base, ylab in [("focal", FOC, "y_focal"), ("generalized", AMT, "y_gen")]:
        for arm, pick in arms.items():
            cols = pick(base)
            for setname, te in [("report-test", rt), ("ON-100", on)]:
                if not len(te) or te[ylab].nunique() < 2:
                    continue
                s = fit_score(tr, te, cols, ylab)
                a, (lo, hi) = boot_auc(te[ylab].astype(int).values, s)
                rows.append(dict(axis=tag, arm=arm, testset=setname, auroc=a, lo=lo, hi=hi,
                                 n=int(len(te)), n_pos=int(te[ylab].sum())))
    t = pd.DataFrame(rows)
    t.to_csv(RES / "age_ablation.csv", index=False)

    # ---- age-stratified (deviation+age), decade bands -------------------------------------------
    strat = []
    for tag, base, ylab in [("focal", FOC, "y_focal"), ("generalized", AMT, "y_gen")]:
        cols = list(base) + ["age"]
        s_all = pd.Series(fit_score(tr, rt, cols, ylab), index=rt.index)
        for lo_ in range(0, 90, 10):
            m = rt.age.between(lo_, lo_ + 10, inclusive="left")
            sub = rt[m]
            if len(sub) < 60 or sub[ylab].nunique() < 2:
                continue
            a, (l, h) = boot_auc(sub[ylab].astype(int).values, s_all[m].values)
            strat.append(dict(axis=tag, band=f"{lo_}-{lo_ + 10}", auroc=a, lo=l, hi=h,
                              n=int(len(sub)), n_pos=int(sub[ylab].sum())))
    st = pd.DataFrame(strat)
    st.to_csv(RES / "age_ablation_stratified.csv", index=False)

    # ---- age-matched external (IPW) -------------------------------------------------------------
    matched = []
    for tag, base, ylab in [("focal", FOC, "y_focal"), ("generalized", AMT, "y_gen")]:
        cols = list(base) + ["age"]
        for setname, te in [("report-test", rt), ("ON-100", on)]:
            if not len(te) or te[ylab].nunique() < 2:
                continue
            s = fit_score(tr, te, cols, ylab)
            y = te[ylab].astype(int).values
            w = ipw_age_weights(te.age.values, y)
            matched.append(dict(axis=tag, testset=setname, auroc_raw=roc_auc_score(y, s),
                                auroc_age_matched=weighted_auc(y, s, w), n=int(len(te))))
    mt = pd.DataFrame(matched)
    mt.to_csv(RES / "age_ablation_matched.csv", index=False)

    def g(axis, arm, ts):
        r = t[(t.axis == axis) & (t.arm == arm) & (t.testset == ts)]
        return None if r.empty else r.iloc[0]

    L = ["# Does the detector exploit age? (review comment 14)", "",
         "Abnormal recordings are ~17 y older than clean-normals, and chronological age is a feature in both "
         "heads, so the classifier could in principle recover the age-label association instead of reading "
         "the deviation field. Five arms, reported even-handedly.", "",
         "| axis | arm | test set | AUROC [95% CI] | n | positives |", "|---|---|---|---|---|---|"]
    for r in t.itertuples():
        L.append(f"| {r.axis} | {r.arm} | {r.testset} | {r.auroc:.3f} [{r.lo:.3f}, {r.hi:.3f}] | "
                 f"{r.n:,} | {r.n_pos:,} |")

    L += ["", "## Age-stratified (deviation+age, report-test)", "",
          "Within a decade band age barely varies, so a shortcut has little to exploit; if performance held "
          "up only across bands it would be doing demographics, not EEG.", "",
          "| axis | age band | AUROC [95% CI] | n | positives |", "|---|---|---|---|---|"]
    for r in st.itertuples():
        L.append(f"| {r.axis} | {r.band} | {r.auroc:.3f} [{r.lo:.3f}, {r.hi:.3f}] | {r.n:,} | {r.n_pos:,} |")

    L += ["", "## Age-matched (inverse-propensity reweighted)", "",
          "| axis | test set | AUROC raw | AUROC age-matched | n |", "|---|---|---|---|---|"]
    for r in mt.itertuples():
        L.append(f"| {r.axis} | {r.testset} | {r.auroc_raw:.3f} | {r.auroc_age_matched:.3f} | {r.n:,} |")

    L += ["", "## Verdict", ""]
    for axis in ("focal", "generalized"):
        for ts in ("report-test", "ON-100"):
            ao, do, da = g(axis, "age-only", ts), g(axis, "deviation-only", ts), g(axis, "deviation+age", ts)
            if ao is None or do is None or da is None:
                continue
            L.append(f"- **{axis}, {ts}** — age alone {ao.auroc:.3f}; deviation alone {do.auroc:.3f}; "
                     f"deviation+age {da.auroc:.3f}. Dropping age costs {da.auroc - do.auroc:+.3f}; "
                     f"the deviation field adds {do.auroc - ao.auroc:+.3f} over age alone.")
    (RES / "age_ablation.md").write_text("\n".join(L) + "\n")
    print(f"wrote {RES/'age_ablation.md'}")
    for r in t.itertuples():
        print(f"  {r.axis:12s} {r.arm:15s} {r.testset:12s} AUROC {r.auroc:.3f}")


if __name__ == "__main__":
    main()
