#!/usr/bin/env python3
"""Human-ceiling panel scoring RE-RUN on the v6 fleet data (the last legacy number in the manuscript).

The manuscript's panel claims (our score vs 18 electroencephalographers on 100 EEGs: AUROC 0.903,
balanced accuracy 0.835, Spearman rho 0.652) were computed on the LEGACY pipeline and the CONTAMINATED
labels. Given that the same label bug destroyed two other headline claims, this must be verified, not
assumed. Here we re-score using ONLY v6 fleet output for the 100 OccasionNoise EEGs (ON_1..ON_100).

Expert votes: scratchpad Occasion.xlsx sheet "DB" — fid x uid, with
  r1.FN / r2.FN = focal    non-epileptiform (i.e. FOCAL SLOWING), reading 1 / 2
  r1.GN / r2.GN = general  non-epileptiform (i.e. GENERALIZED SLOWING)
Our scores (v6): segment_summary -> Morgoth per-segment p_slowing (p90 over usable segments);
                 _done          -> EEG-level p_focal / p_generalized.

Reports: inter-rater Fleiss kappa (the ceiling; a property of the raters, unchanged by our pipeline),
our gate's AUROC vs the expert MAJORITY, and Spearman rho vs the PROPORTION of experts who saw it
(the "conspicuity" claim — the number the under-reporting argument actually rests on).

Run: PYTHONPATH=src python scripts/recompute_human_ceiling_v6.py
"""
import glob, json, os
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score, balanced_accuracy_score

SCR = os.environ.get("PANEL_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
XLS = f"{SCR}/moe/occ/Occasion.xlsx"
SS = "data/derived/segment_summary"
DONE = "data/derived/segment_master/_done"


def fleiss_kappa(counts):
    """counts: (n_items, 2) yes/no counts per item. Standard Fleiss kappa."""
    n = counts.sum(axis=1)
    keep = n > 1
    counts, n = counts[keep], n[keep]
    N = len(counts)
    p_i = ((counts * (counts - 1)).sum(axis=1)) / (n * (n - 1))
    P_bar = p_i.mean()
    p_j = counts.sum(axis=0) / counts.sum()
    P_e = (p_j ** 2).sum()
    return (P_bar - P_e) / (1 - P_e) if (1 - P_e) > 0 else np.nan


def expert_votes():
    db = pd.ExcelFile(XLS).parse("DB")
    out = {}
    for read, tag in [("r1", "read1"), ("r2", "read2")]:
        d = db[["fid", "uid", f"{read}.FN", f"{read}.GN"]].dropna(subset=[f"{read}.FN", f"{read}.GN"])
        # a rater "saw" it if the vote is non-zero
        d = d.assign(FN=(d[f"{read}.FN"] > 0).astype(int), GN=(d[f"{read}.GN"] > 0).astype(int))
        out[tag] = d[["fid", "uid", "FN", "GN"]]
    return out


def our_scores():
    rows = []
    for f in glob.glob(f"{SS}/eeg_id=ON_*/part.parquet"):
        eid = f.split("eeg_id=")[1].split("/")[0]
        s = pd.read_parquet(f, columns=["artifact_flag", "p_slowing"])
        s = s[~s.artifact_flag]
        if s.empty or s.p_slowing.isna().all():
            continue
        rows.append({"eeg_id": eid, "fid": int(eid.split("_")[1]),
                     "p_slowing_p90": float(np.nanpercentile(s.p_slowing, 90)),
                     "p_slowing_mean": float(s.p_slowing.mean())})
    sc = pd.DataFrame(rows)
    # EEG-level focal/generalized heads from the .done sidecars
    lvl = []
    for f in glob.glob(f"{DONE}/ON_*.done"):
        d = json.load(open(f))
        lvl.append({"eeg_id": d["eeg_id"], "p_focal": d.get("p_focal"),
                    "p_generalized": d.get("p_generalized")})
    if lvl:
        sc = sc.merge(pd.DataFrame(lvl), on="eeg_id", how="left")
    return sc


def main():
    ev = expert_votes()
    r1 = ev["read1"]
    n_raters = r1.uid.nunique()
    agg = r1.groupby("fid").agg(FN_yes=("FN", "sum"), GN_yes=("GN", "sum"), n=("FN", "size")).reset_index()
    agg["FN_frac"] = agg.FN_yes / agg.n
    agg["GN_frac"] = agg.GN_yes / agg.n
    agg["FN_maj"] = (agg.FN_frac > 0.5).astype(int)
    agg["GN_maj"] = (agg.GN_frac > 0.5).astype(int)

    # --- the ceiling: inter-rater agreement (property of the raters; our pipeline cannot change it) ---
    k_fn = fleiss_kappa(np.c_[agg.FN_yes, agg.n - agg.FN_yes])
    k_gn = fleiss_kappa(np.c_[agg.GN_yes, agg.n - agg.GN_yes])
    print(f"panel: {len(agg)} EEGs x {n_raters} raters")
    print(f"INTER-RATER (the ceiling)  Fleiss kappa   focal slowing {k_fn:.3f} | generalized {k_gn:.3f}")
    print(f"  prevalence by expert majority: focal {int(agg.FN_maj.sum())}/{len(agg)} | "
          f"generalized {int(agg.GN_maj.sum())}/{len(agg)}\n")

    sc = our_scores().merge(agg, on="fid", how="inner")
    print(f"scored with v6 fleet output: {len(sc)} of {len(agg)} panel EEGs")
    if sc.empty:
        return

    def report(name, col, y, frac):
        s = sc[col]
        m = s.notna() & y.notna()
        if m.sum() < 10 or y[m].nunique() < 2:
            print(f"  {name:34} n/a"); return
        a = roc_auc_score(y[m], s[m])
        if a < 0.5:
            a = 1 - a
        rho, p = spearmanr(s[m], frac[m])
        print(f"  {name:34} AUROC vs majority {a:.3f}   |   Spearman rho vs expert-proportion "
              f"{rho:+.3f} (p={p:.1e})")
        return a, rho

    print("\nOUR v6 SCORES vs THE PANEL")
    print("  --- generalized slowing ---")
    report("Morgoth p_generalized (EEG-level)", "p_generalized", sc.GN_maj, sc.GN_frac)
    report("Morgoth p_slowing (p90)", "p_slowing_p90", sc.GN_maj, sc.GN_frac)
    print("  --- focal slowing ---")
    report("Morgoth p_focal (EEG-level)", "p_focal", sc.FN_maj, sc.FN_frac)
    report("Morgoth p_slowing (p90)", "p_slowing_p90", sc.FN_maj, sc.FN_frac)

    # --- the average expert vs the majority (the human operating point) ---
    print("\nTHE AVERAGE EXPERT (leave-one-out vs the majority of the others)")
    for tag, col in [("focal", "FN"), ("generalized", "GN")]:
        accs = []
        for uid, g in r1.groupby("uid"):
            others = r1[r1.uid != uid]
            om = others.groupby("fid")[col].mean()
            oth_maj = (om > 0.5).astype(int)
            j = g.set_index("fid")[col].reindex(oth_maj.index).dropna()
            if j.nunique() < 2 or oth_maj.loc[j.index].nunique() < 2:
                continue
            accs.append(balanced_accuracy_score(oth_maj.loc[j.index], j))
        if accs:
            print(f"  {tag:12} average expert balanced accuracy vs peers: {np.mean(accs):.3f} "
                  f"(n={len(accs)} raters)")

    Path("results").mkdir(exist_ok=True)
    sc.to_parquet("data/derived/panel_v6_scores.parquet", index=False)
    print("\nwrote data/derived/panel_v6_scores.parquet")


if __name__ == "__main__":
    main()
