"""VIGILANCE-MATCHED DETECTION (the primary detection analysis on the recomputed union data).

Rationale: in a ROUTINE EEG the technologist actively keeps the patient maximally awake, so W/N1 are genuine
alert states; in OVERNIGHT studies "wake" is unconstrained and often drowsy (high delta), which inflates the
normal band and masks pathological slowing. So detection should reference vigilance-matched norms.

Design: positives = routine (cohort) abnormals; negatives = held-out routine clean-normals. For each stage
and feature (whole-head), score an age-adjusted normal-referenced z, and vary the NORMAL REFERENCE:
  (R) ROUTINE clean-normals   -> the vigilance-matched primary
  (O) OVERNIGHT clean-normals -> unconstrained wake
  (U) UNION of both
AUROC(abnormal vs held-out routine normal). Primary readout: reference R, stages W & N1.

Run: PYTHONPATH=src python scripts/84_vigilance_matched_detection.py
"""
from __future__ import annotations
from pathlib import Path
import os
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATURES = ["TAR", "DAR", "log_delta", "log_theta", "rel_delta"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
REGION = "whole_head"
rng = np.random.default_rng(0)


def normal_z(vals, ages, ref_vals, ref_ages, bw=5.0):
    z = np.full(len(vals), np.nan); ra, rv = np.asarray(ref_ages), np.asarray(ref_vals)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    for i in range(len(vals)):
        if not (np.isfinite(vals[i]) and np.isfinite(ages[i])): continue
        wt = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = wt.sum()
        if sw < 5: continue
        mu = (wt * rv).sum() / sw; sd = np.sqrt(max((wt * (rv - mu) ** 2).sum() / sw, 1e-9))
        z[i] = (vals[i] - mu) / sd
    return z


def auc_ci(y, s, n=400):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2: return np.nan, np.nan, np.nan
    a = roc_auc_score(y, s); idx = np.arange(len(y)); bs = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    w = d[(d.region == REGION) & d.age.between(0, 100)].merge(lu, on="bdsp_id", how="left")

    # SENSITIVITY (scripts/88): 17.2% of routine recordings carry a report broadcast from a sibling study of
    # the same patient, so their text-derived label terms may describe a different EEG. CLEAN_PAIR=1 keeps
    # only routine recordings that own the report written about them.
    if os.environ.get("CLEAN_PAIR") == "1":
        cp = pd.read_parquet("data/derived/report_pairing.parquet")
        good = set(cp[cp.clean_pair == True].bdsp_id)
        before = w.bdsp_id.nunique()
        w = w[(w.src != "cohort") | (w.bdsp_id.isin(good))]
        print(f"[CLEAN_PAIR] recordings: {before:,} -> {w.bdsp_id.nunique():,}")

    # split routine clean-normals into reference-train (70%) and test-negatives (30%)
    rn_ids = w[(w.src == "cohort") & (w.clean_normal == True)].bdsp_id.unique()
    test_neg = set(rng.choice(rn_ids, int(0.3 * len(rn_ids)), replace=False))
    train_ref = set(rn_ids) - test_neg
    targets = {"abnormal": w.is_abnormal == True,
               "gen_pathologic": w.gen_class == "pathologic",
               "focal": w.has_focal_slow == True}
    w = w.assign(**{f"_t_{k}": v for k, v in targets.items()})

    rows = []
    for st in STAGES:
        s = w[w.stage == st]
        refs = {"R_routine": s[s.bdsp_id.isin(train_ref)],
                "O_overnight": s[(s.src == "expansion") & (s.clean_normal == True)],
                "U_union": s[((s.bdsp_id.isin(train_ref)) | ((s.src == "expansion") & (s.clean_normal == True)))]}
        neg = s[s.bdsp_id.isin(test_neg)]                         # held-out routine normals (negatives)
        for tname in targets:
            pos = s[(s[f"_t_{tname}"] == True) & (s.src == "cohort")]   # routine abnormals of this type
            if len(pos) < 15 or len(neg) < 20: continue
            test = pd.concat([pos.assign(y=1), neg.assign(y=0)])
            for feat in FEATURES:
                for rname, ref in refs.items():
                    z = normal_z(test[feat].values, test.age.values, ref[feat].values, ref.age.values)
                    a, lo, hi = auc_ci(test.y.values, z)
                    rows.append({"stage": st, "target": tname, "feature": feat, "ref": rname,
                                 "auc": a, "lo": lo, "hi": hi, "n_pos": len(pos), "n_neg": len(neg)})
    res = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True); res.to_csv("results/vigilance_matched_detection.csv", index=False)

    # PRIMARY readout: normal vs generalized-pathologic, reference = routine, best feature per stage
    print("=== PRIMARY: normal vs pathologic-generalized slowing, ROUTINE norm, whole-head ===")
    print(f"{'stage':<5}{'best feature':>14}{'AUROC (routine norm)':>22}{'AUROC (overnight)':>20}{'AUROC (union)':>16}")
    for st in STAGES:
        sub = res[(res.target == "gen_pathologic") & (res.stage == st)]
        if sub.empty: continue
        rr = sub[sub.ref == "R_routine"]
        best = rr.loc[rr.auc.idxmax()] if not rr.dropna(subset=["auc"]).empty else None
        if best is None: continue
        o = sub[(sub.ref == "O_overnight") & (sub.feature == best.feature)].auc.values
        u = sub[(sub.ref == "U_union") & (sub.feature == best.feature)].auc.values
        star = "  <- alert-assured" if st in ("W", "N1") else ""
        print(f"{st:<5}{best.feature:>14}{best.auc:>13.3f} [{best.lo:.2f},{best.hi:.2f}]"
              f"{(o[0] if len(o) else float('nan')):>20.3f}{(u[0] if len(u) else float('nan')):>16.3f}{star}")
    print(f"\n(positives n={res[(res.target=='gen_pathologic')].n_pos.max()}, "
          f"held-out routine-normal negatives n={res[(res.target=='gen_pathologic')].n_neg.max()})")

    # figure: for gen_pathologic, best-feature AUROC by stage x reference
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(STAGES)); wd = 0.26
    for i, (rname, lab) in enumerate([("R_routine", "routine norm (alert)"),
                                      ("O_overnight", "overnight norm (drowsy)"), ("U_union", "union norm")]):
        vals = []
        for st in STAGES:
            sub = res[(res.target == "gen_pathologic") & (res.stage == st) & (res.ref == rname)]
            vals.append(sub.auc.max() if not sub.dropna(subset=["auc"]).empty else np.nan)
        ax.bar(x + (i - 1) * wd, vals, wd, label=lab)
    ax.axhline(0.5, color="k", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(STAGES)
    ax.set_ylabel("AUROC (best whole-head feature)"); ax.set_ylim(0.4, 0.9); ax.legend(fontsize=9)
    ax.set_title("Vigilance-matched detection: normal vs pathologic-generalized slowing\n"
                 "routine (alert) norm detects best in W/N1; overnight (drowsy) norm masks it")
    fig.tight_layout(); fig.savefig("figures/growth_v2/vigilance_matched_detection.png", dpi=130); plt.close(fig)
    print("wrote results/vigilance_matched_detection.csv + figures/growth_v2/vigilance_matched_detection.png")


if __name__ == "__main__":
    main()
