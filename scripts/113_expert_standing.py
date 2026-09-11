"""Standing against the individual experts, scored symmetrically and with uncertainty (Beniczky review, comment
7), and paired AUROC differences on ON-100 (comments 8 and 34-36).

Comment 7 has three parts; each is a column of the output.

  (a) Asymmetric reference. Each expert's operating point is graded against the leave-one-out (LOO) majority of
      the OTHER experts, but the model's ROC was graded against the FULL majority, which includes that expert's
      own vote. The two sides of the comparison met different references. The symmetric version recomputes the
      model's ROC, for each expert r, against r's own LOO reference on exactly the recordings r read, and counts r
      as "under" only if r's point lies on or below THAT curve. The published (asymmetric) statistic is computed
      alongside as a self-check: it must reproduce Figures 2 and 3.
  (b) No uncertainty. The percentage is a ratio of small integers (14-18 experts), and it moved from 79% to 64%
      when two SAI-100 recordings were added. It gets a recording-level bootstrap 95% CI, with every expert point
      and every LOO reference re-derived inside each replicate.
  (c) Not a test. The percentage describes relative standing; it is not a hypothesis test of the model against
      any individual expert. AUROC against the full majority remains the primary metric.

Paired differences resample recordings ONCE per replicate and score every model on that same resample, so each
interval is for the difference itself -- the construction already used for SAI-100 in
sandor100_external_validation.py. The best van Putten index is selected, and oriented, once on the full panel and
then held fixed, which slightly favours the comparator.

Writes results/story/expert_standing.md + expert_standing.csv + expert_standing_paired.csv
Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/113_expert_standing.py [--panels on100,sai100]
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


RES = Path("results/story")
B = 2000
MIN_READS = 5          # the same eligibility rule as scripts/46 expert_points


# ---- the expert geometry, in numpy so it can be re-derived 2,000 times per panel -----------------------------
def _expert_refs(V):
    """Per expert j: (rows j read with a LOO reference, LOO majority on those rows, j's own calls on those rows).

    Mirrors scripts/46 expert_points exactly -- rows where j voted and at least one other expert voted; LOO
    majority = mean of the others >= 0.5; experts with < MIN_READS such rows, or a single-class reference, drop.
    """
    out = {}
    for j in range(V.shape[1]):
        me = V[:, j]
        others = np.delete(V, j, axis=1)
        rows = ~np.isnan(me) & (~np.isnan(others)).any(axis=1)
        if rows.sum() < MIN_READS:
            continue
        with np.errstate(invalid="ignore"):
            cons = (np.nanmean(others[rows], axis=1) >= 0.5).astype(int)
        mv = me[rows].astype(int)
        pos, neg = cons == 1, cons == 0
        if not pos.any() or not neg.any():
            continue
        tpr = float((mv[pos] == 1).mean()); fpr = float((mv[neg] == 1).mean())
        out[j] = (rows, cons, fpr, tpr)
    return out


def _under(fpr_m, tpr_m, fpr_e, tpr_e):
    return float(np.interp(fpr_e, fpr_m, tpr_m)) >= tpr_e - 1e-9       # scripts/46 under_roc, unchanged


def standing(V, y, s):
    """(asymmetric fraction, symmetric fraction, n eligible experts) for one model on one panel."""
    refs = _expert_refs(V)
    if not refs:
        return np.nan, np.nan, 0
    fpr_full, tpr_full, _ = roc_curve(y, s)
    asym, sym = [], []
    for rows, cons, fpr_e, tpr_e in refs.values():
        asym.append(_under(fpr_full, tpr_full, fpr_e, tpr_e))
        f, t, _ = roc_curve(cons, s[rows])                             # the model against r's OWN reference
        sym.append(_under(f, t, fpr_e, tpr_e))
    return float(np.mean(asym)), float(np.mean(sym)), len(refs)


def evaluate(panel, axis, V, y, models, comparisons, seed=0):
    """Point estimates + recording-level bootstrap for standing, AUROC and the paired differences."""
    rng = np.random.default_rng(seed)
    N = len(y)
    point = {m: (roc_auc_score(y, s),) + standing(V, y, s) for m, s in models.items()}
    boot_auc = {m: [] for m in models}; boot_sym = {m: [] for m in models}; boot_n = []
    boot_diff = {c: [] for c in comparisons}
    for _ in range(B):
        idx = rng.integers(0, N, N)
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        Vb = V[idx]
        aucs = {}
        for m, s in models.items():
            sb = s[idx]
            aucs[m] = roc_auc_score(yb, sb)
            _, sym, n = standing(Vb, yb, sb)
            boot_auc[m].append(aucs[m]); boot_sym[m].append(sym)
        boot_n.append(n)
        for a, b in comparisons:
            boot_diff[(a, b)].append(aucs[a] - aucs[b])

    def ci(v):
        v = np.asarray([x for x in v if np.isfinite(x)])
        return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) else (np.nan, np.nan)

    rows = []
    for m in models:
        auc, asym, sym, n = point[m]
        rows.append(dict(panel=panel, axis=axis, model=m, n=N, n_pos=int(y.sum()), experts=n,
                         auroc=auc, auroc_lo=ci(boot_auc[m])[0], auroc_hi=ci(boot_auc[m])[1],
                         under_asym=100 * asym, under_asym_k=round(asym * n),
                         under_sym=100 * sym, under_sym_k=round(sym * n),
                         under_sym_lo=100 * ci(boot_sym[m])[0], under_sym_hi=100 * ci(boot_sym[m])[1]))
    paired = []
    for a, b in comparisons:
        d = np.asarray(boot_diff[(a, b)])
        lo, hi = np.percentile(d, [2.5, 97.5])
        p = max(2 * min((d <= 0).mean(), (d >= 0).mean()), 1 / len(d))
        paired.append(dict(panel=panel, axis=axis, comparison=f"{a} - {b}",
                           diff=point[a][0] - point[b][0], lo=float(lo), hi=float(hi), p=float(p), B=len(d)))
    return rows, paired


# ---- the two panels, each through its figure's own scoring code path -----------------------------------------
def on100():
    """ON-100: LENS, the Morgoth gate and the best van Putten index -- scripts/vanputten_panel_s7 exactly."""
    vp = _load("vp", "scripts/vanputten_panel_s7.py")
    lens = vp.lens_panel_scores()
    em = vp.m54.expert_and_morgoth("occasion")
    vp_gen, vp_foc = vp.vanputten_panel_indices()
    out_rows, out_paired = [], []
    for axis, vp_cands in (("focal", vp_foc), ("generalized", vp_gen)):
        wide, morg = em[axis]
        idx = wide.index
        y_all = (wide.mean(axis=1).to_numpy() >= 0.5).astype(int)
        vp_name, vp_s, _ = vp.best_index(vp_cands, y_all, idx)
        raw = {"LENS": lens[axis].reindex(idx).to_numpy(float), "Morgoth gate": morg.reindex(idx).to_numpy(float),
               f"van Putten ({vp_name})": vp_s}
        common = np.isfinite(y_all)
        for s in raw.values():
            common &= np.isfinite(s)
        V = wide.loc[common].to_numpy(float)
        models = {k: v[common] for k, v in raw.items()}
        comps = [("LENS", "Morgoth gate"), ("LENS", f"van Putten ({vp_name})")]
        r, p = evaluate("ON-100", axis, V, y_all[common], models, comps)
        out_rows += r; out_paired += p
    return out_rows, out_paired


def sai100():
    """SAI-100: LENS, Morgoth and SCORE-AI -- sandor100_external_validation.eval_axis exactly."""
    sv = _load("sv", "scripts/sandor100_external_validation.py")
    gen, foc, foc_med, amt_med = sv.train_heads()
    scores = sv.score_sandor(gen, foc, foc_med, amt_med)        # refuses a partial SAI-100 set
    out_rows, out_paired = [], []
    for axis in ("focal", "generalized"):
        d = sv._panel(axis)
        d["key"] = d.file_name.astype(str).str.strip()
        m = scores.merge(d, on="key", how="inner")
        cols = [c for c in d.columns if c.startswith("expert_")]
        V = m[cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        with np.errstate(invalid="ignore"):
            y = (np.nanmean(V, axis=1) >= 0.5).astype(int)
        models = {"LENS": m[f"ours_{axis}"].to_numpy(float), "Morgoth": m["M_pred"].to_numpy(float),
                  "SCORE-AI": m["S_pred"].to_numpy(float)}
        ok = np.ones(len(y), bool)
        for s in models.values():
            ok &= np.isfinite(s)
        r, p = evaluate("SAI-100", axis, V[ok], y[ok], {k: v[ok] for k, v in models.items()},
                        [("LENS", "SCORE-AI"), ("LENS", "Morgoth")])
        out_rows += r; out_paired += p
    return out_rows, out_paired


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panels", default="on100,sai100")
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    rows, paired = [], []
    for name, fn in (("on100", on100), ("sai100", sai100)):
        if name in a.panels.split(","):
            r, p = fn(); rows += r; paired += p
    R = pd.DataFrame(rows); P = pd.DataFrame(paired)
    R.to_csv(RES / "expert_standing.csv", index=False); P.to_csv(RES / "expert_standing_paired.csv", index=False)

    md = ["# Standing against the individual experts, symmetric and with uncertainty (review comment 7)", "",
          "**AUROC** is against the full expert majority (primary metric), with a recording-level bootstrap 95% CI.",
          "**Under, as published**: an expert counts as under the model's ROC when that expert's point (graded "
          "against the leave-one-out majority of the other experts) lies on or below the model's ROC graded "
          "against the FULL majority. This must reproduce Figures 2 and 3.",
          "**Under, symmetric**: the model's ROC is re-graded, for each expert, against that expert's own "
          "leave-one-out reference on the recordings that expert read. Bootstrap 95% CI re-derives every expert "
          "point and reference inside each of "
          f"{B:,} replicates. This is relative standing, not a hypothesis test against any individual expert.", "",
          "**Majority rule and denominator.** Here, as in Figures 2, 3 and S3, a recording is positive when at least "
          "half of its readers call it positive (mean vote >= 0.5), so an exact tie counts as positive. The "
          "human-ceiling table (Table S2) counts ties as negative, which is why its ON-100 base rates (12/100 "
          "focal, 18/100 generalized) differ from the positives here. ON-100 rows use the recordings finite for "
          "every compared method, which is why n is below 100.", "",
          "| panel | axis | model | n (pos) | AUROC [95% CI] | experts | under, as published | "
          "under, symmetric [95% CI] |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['panel']} | {r['axis']} | {r['model']} | {r['n']} ({r['n_pos']}) | "
                  f"{r['auroc']:.3f} [{r['auroc_lo']:.3f}, {r['auroc_hi']:.3f}] | {r['experts']} | "
                  f"{r['under_asym']:.0f}% ({r['under_asym_k']}/{r['experts']}) | "
                  f"{r['under_sym']:.0f}% ({r['under_sym_k']}/{r['experts']}) "
                  f"[{r['under_sym_lo']:.0f}%, {r['under_sym_hi']:.0f}%] |")
    md += ["", "## Paired AUROC differences (same bootstrap resample for both models)", "",
           "| panel | axis | comparison | ΔAUROC [95% CI] | two-sided bootstrap p |", "|---|---|---|---|---|"]
    for p in paired:
        # A bootstrap of B draws cannot resolve p below ~1/B; printing "0.00" claims a precision it does not have.
        ptxt = f"< {10 ** np.ceil(np.log10(2 / p['B'])):.3g}" if p["p"] <= 2 / p["B"] else f"{p['p']:.2f}"
        md.append(f"| {p['panel']} | {p['axis']} | {p['comparison']} | {p['diff']:+.3f} "
                  f"[{p['lo']:+.3f}, {p['hi']:+.3f}] | {ptxt} |")
    (RES / "expert_standing.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
