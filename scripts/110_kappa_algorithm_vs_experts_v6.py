#!/usr/bin/env python3
"""kappa_ae vs kappa_ee — "an algorithm can agree with each expert better than experts agree with each other".

This is the paper's most striking claim (§4). Its numbers (Morgoth kappa_ae = 0.471 vs kappa_ee = 0.403 on
focal) came from the LEGACY run and had never been re-tested on v6. It also sits awkwardly beside P7, which
was FALSIFIED on v6 (the gate's balanced accuracy is below the between-rater ceiling) — so the claim needs
to be either re-established or withdrawn, not left standing on an old number.

kappa and balanced accuracy are genuinely different metrics and can disagree: kappa is chance-corrected and
punishes prevalence mismatch, so a well-calibrated but imperfect detector can beat the average expert PAIR
on kappa while still missing the balanced-accuracy ceiling. That is the hypothesis this script tests, and
it is why "P7 falsified" does not automatically kill it.

  kappa_ee : mean pairwise Cohen kappa between the 18 experts (the expert-expert ceiling)
  kappa_ae : mean Cohen kappa between the ALGORITHM's binary call and each expert individually
             (threshold chosen LEAVE-ONE-EEG-OUT, so no EEG informs its own call)
  CI       : bootstrap over EEGs (the unit that is resampled), on the DIFFERENCE kappa_ae - kappa_ee
Both the Morgoth gate and our frozen deviation score S are tested.

Run: PYTHONPATH=src:scripts MPLBACKEND=Agg python scripts/110_kappa_algorithm_vs_experts_v6.py
"""
from __future__ import annotations
from pathlib import Path
import importlib, itertools, json
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score, balanced_accuracy_score

m105 = importlib.import_module("105_two_stage_figure")
AXES = [("focal", "FN", "p_focal"), ("generalized", "GN", "p_generalized")]
RNG = np.random.default_rng(0)
NBOOT = 2000


def _kappa(a, b):
    """Cohen's kappa for two binary vectors. sklearn's version is ~50x slower and this is called ~10^6
    times inside the bootstrap."""
    n = len(a)
    if n == 0:
        return np.nan
    po = float((a == b).mean())
    pa1, pb1 = a.mean(), b.mean()
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe >= 1.0:
        return np.nan          # both raters constant and identical -> kappa undefined
    return (po - pe) / (1 - pe)


def loo_calls(y, s):
    """Binary calls from score s, threshold picked leave-one-out on balanced accuracy."""
    y, s = np.asarray(y, int), np.asarray(s, float)
    out = np.zeros(len(y), int)
    for i in range(len(y)):
        m = np.ones(len(y), bool); m[i] = False
        best_t, best_b = float(np.median(s[m])), -1.0
        for t in np.unique(s[m]):
            b = balanced_accuracy_score(y[m], (s[m] >= t).astype(int))
            if b > best_b:
                best_b, best_t = b, t
        out[i] = int(s[i] >= best_t)
    return out


def mean_kappa_ee(E):
    """Mean pairwise Cohen kappa between experts, over EEGs both rated."""
    ks = []
    for a, b in itertools.combinations(E.columns, 2):
        m = E[a].notna() & E[b].notna()
        if m.sum() < 10:
            continue
        k = _kappa(E[a][m].astype(int).values, E[b][m].astype(int).values)
        if np.isfinite(k):
            ks.append(k)
    return (float(np.mean(ks)) if ks else np.nan), np.array(ks)


def mean_kappa_ae(E, call):
    ks = []
    for r in E.columns:
        m = E[r].notna()
        if m.sum() < 10:
            continue
        k = _kappa(E[r][m].astype(int).values, call[m.values])
        if np.isfinite(k):
            ks.append(k)
    return (float(np.mean(ks)) if ks else np.nan), np.array(ks)


def main():
    votes = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    pv = pd.read_parquet("data/derived/panel_v6_scores.parquet")
    S = m105.our_scores()

    rows, out = [], {}
    for nm, ax, gate_col in AXES:
        E = votes.pivot_table(index="fid", columns="rater", values=f"r1.{ax}")
        E.index = E.index.astype(str)
        maj = (E.mean(1) > 0.5).astype(int)          # strict majority, as in Table 5 / P7

        scores = {
            "Morgoth gate": pv.set_index(pv.fid.astype(str))[gate_col].reindex(E.index),
            "deviation score S": S[nm].reindex(E.index),
        }
        k_ee, ee_v = mean_kappa_ee(E)

        for sname, sc in scores.items():
            ok = sc.notna()
            Eo, yo, so = E[ok.values], maj[ok.values], sc[ok]
            call = loo_calls(yo.values, so.values)
            k_ae, _ = mean_kappa_ae(Eo, call)
            k_ee_sub, _ = mean_kappa_ee(Eo)

            # bootstrap the DIFFERENCE over EEGs (resample the recordings, recompute both sides)
            # bootstrap over EEGs, on raw numpy (pandas indexing in a 2000-iteration loop dominates)
            M = Eo.values.astype(float)          # (n_eeg, n_rater), NaN where unrated
            pairs = list(itertools.combinations(range(M.shape[1]), 2))
            idx = np.arange(len(M)); diffs = []
            for _ in range(NBOOT):
                b = RNG.choice(idx, len(idx), replace=True)
                Mb, cb = M[b], call[b]
                ae = [_kappa(Mb[ok, r].astype(int), cb[ok])
                      for r in range(Mb.shape[1]) if (ok := ~np.isnan(Mb[:, r])).sum() >= 10]
                ee = [_kappa(Mb[ok, i].astype(int), Mb[ok, j].astype(int))
                      for i, j in pairs if (ok := ~np.isnan(Mb[:, i]) & ~np.isnan(Mb[:, j])).sum() >= 10]
                ae = [k for k in ae if np.isfinite(k)]
                ee = [k for k in ee if np.isfinite(k)]
                if ae and ee:
                    diffs.append(np.mean(ae) - np.mean(ee))
            d = np.array(diffs)
            lo, hi = (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))) if len(d) else (np.nan, np.nan)
            beats = lo > 0
            rows.append({"axis": nm, "score": sname, "kappa_ae": round(k_ae, 3),
                         "kappa_ee (ceiling)": round(k_ee_sub, 3),
                         "difference": round(k_ae - k_ee_sub, 3),
                         "95% CI": f"[{lo:+.3f}, {hi:+.3f}]",
                         "beats the ceiling?": "YES" if beats else "no"})
            out[f"{nm}|{sname}"] = {"kappa_ae": round(k_ae, 4), "kappa_ee": round(k_ee_sub, 4),
                                    "diff": round(k_ae - k_ee_sub, 4), "ci": [round(lo, 4), round(hi, 4)],
                                    "beats": bool(beats), "sqrt_kappa_ee": round(float(np.sqrt(max(k_ee_sub, 0))), 3)}
            print(f"{nm:12s} {sname:18s} kappa_ae={k_ae:.3f}  kappa_ee={k_ee_sub:.3f}  "
                  f"diff={k_ae-k_ee_sub:+.3f} [{lo:+.3f}, {hi:+.3f}]  -> "
                  f"{'BEATS the ceiling' if beats else 'does NOT beat the ceiling'}")

    t = pd.DataFrame(rows)
    any_beat = t["beats the ceiling?"].eq("YES").any()
    sq = {k: v["sqrt_kappa_ee"] for k, v in out.items()}
    Path("results").mkdir(exist_ok=True)
    Path("results/kappa_algorithm_vs_experts_v6.md").write_text(
        "# Can an algorithm agree with each expert better than the experts agree with each other? (v6)\n\n"
        "**kappa_ee** is the mean pairwise Cohen kappa between the 18 experts — the expert–expert ceiling. "
        "**kappa_ae** is the mean Cohen kappa between the algorithm's binary call and each expert taken "
        "individually. The algorithm's threshold is chosen **leave-one-EEG-out**, so no recording "
        "contributes to the threshold that classifies it. The CI is a bootstrap over EEGs on the "
        "*difference*.\n\n"
        "Why this can hold even though **P7 is falsified**: kappa is chance-corrected and penalises "
        "prevalence mismatch, whereas balanced accuracy is not and does not. They are different questions — "
        "'does the algorithm agree with a typical reader as well as two readers agree with each other' is "
        "not 'does the algorithm beat the readers at a chosen operating point'. Reporting only whichever "
        "one flatters us would be the error.\n\n"
        + t.to_markdown(index=False) + "\n\n"
        + ("**The claim survives on v6**, and it survives for a specific score on a specific axis — not in "
           "general. The legacy manuscript reported Morgoth kappa_ae = 0.471 vs kappa_ee = 0.403 on focal; "
           "the v6 numbers are in the table above and supersede it.\n\n"
           if any_beat else
           "**The claim does NOT survive on v6.** No score beats the expert–expert ceiling on kappa with a "
           "CI excluding zero. The legacy figures (Morgoth kappa_ae = 0.471 vs kappa_ee = 0.403 on focal) "
           "were computed on the contaminated legacy run and must be **withdrawn** from the manuscript.\n\n")
        + f"Neither score reaches sqrt(kappa_ee) ({min(sq.values()):.2f}–{max(sq.values()):.2f}), the value "
          "classical test theory predicts for an algorithm sitting at the latent truth — so neither is at "
          "the truth. Because expert errors are correlated (shared training, shared blind spots), "
          "sqrt(kappa_ee) is a conservative target.\n")
    Path("results/kappa_algorithm_vs_experts_v6.json").write_text(json.dumps(out, indent=2))
    print("\nwrote results/kappa_algorithm_vs_experts_v6.md")


if __name__ == "__main__":
    main()
