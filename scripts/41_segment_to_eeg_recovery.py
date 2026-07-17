#!/usr/bin/env python3
"""SECTION 1b — recover an EEG-level slowing probability p_eeg' from the 30 s-context segment detections,
and pick a per-stage segment SELECTION rule. Done SEPARATELY BY SLEEP STAGE.

For each recording we have Morgoth's per-segment focal/generalized probability (segment_gate: p_focal_30 /
p_gen_30, the 30 s-context head applied at each 15 s segment) and the segment's sleep stage
(segment_summary.stage). We pool the segments of ONE stage into a single p_eeg' by several rules and ask:

  which rule, using which stage's segments, best (A) reproduces Morgoth's own EEG-level head probability,
  and (B) predicts the report label?  and what per-stage threshold X SELECTS the segments that carry it?

Pooling rules per (recording, stage, axis):
  max            max of the segment probs
  p90            90th percentile
  top5_mean      mean of the 5 highest segment probs
  mean_gt_X      mean of the segments with prob > X      (X swept)
  frac_gt_X      fraction of segments with prob > X      (X swept)
  noisyOR        1 - prod(1 - p_i)  (capped p_i at 0.99)

Targets:
  A (recover head)  Spearman rho between p_eeg' and Morgoth's EEG-level head prob (gate_eeg_level_rerun)
  B (predict report) AUROC of p_eeg' vs the report flag (slowing_focal / slowing_gen_pathologic), clean_pair

Outputs: data/derived/seg2eeg_recovery.parquet (per recording×stage pooled features),
         results/story/s1_seg2eeg.md, figures/story/s1_seg2eeg_{focal,generalized}.png
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/41_segment_to_eeg_recovery.py
"""
from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

SG = Path("data/derived/segment_gate")
SS = Path("data/derived/segment_summary")
STAGES = ["W", "N1", "N2", "N3", "REM"]
XGRID = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]
AXES = [("focal", "p_focal_30", "slowing_focal", "p_focal"),
        ("generalized", "p_gen_30", "slowing_gen_pathologic", "p_generalized")]
FIG = Path("figures/story"); RES = Path("results/story")


def pooled(p):
    """all pooling rules for one 1-D array of segment probs (already stage-filtered)."""
    p = np.asarray(p, float); p = p[np.isfinite(p)]
    if len(p) == 0:
        return None
    d = {"n": len(p), "max": p.max(), "p90": np.quantile(p, 0.9),
         "top5_mean": np.sort(p)[-5:].mean(), "noisyOR": 1 - np.prod(1 - np.minimum(p, 0.99))}
    for X in XGRID:
        m = p > X
        d[f"mean_gt_{X}"] = p[m].mean() if m.any() else 0.0
        d[f"frac_gt_{X}"] = float(m.mean())
    return d


def one(eid):
    fg = SG / f"eeg_id={eid}" / "part.parquet"
    fs = SS / f"eeg_id={eid}" / "part.parquet"
    if not (fg.exists() and fs.exists()):
        return None
    try:
        g = pd.read_parquet(fg, columns=["segment", "p_focal_30", "p_gen_30"])
        s = pd.read_parquet(fs, columns=["segment", "stage"])
    except Exception:
        return None
    m = g.merge(s, on="segment", how="inner")
    rows = []
    for axname, pcol, _, _ in AXES:
        for st in STAGES + ["ALL"]:
            sub = m[m.stage == st] if st != "ALL" else m
            d = pooled(sub[pcol].values)
            if d is None:
                continue
            d.update({"eeg_id": eid, "axis": axname, "stage": st})
            rows.append(d)
    return rows


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    head = pd.read_parquet("data/derived/gate_eeg_level_rerun.parquet").drop_duplicates("eeg_id")
    # report dataset = recordings with report labels + clean_pair (exclude MoE/ON panel clips)
    rep = lab[(lab.clean_pair == True) & (~lab.eeg_id.astype(str).str.startswith(("MOE_", "ON_")))]  # noqa
    ids = [i for i in rep.eeg_id if (SG / f"eeg_id={i}").exists()]
    print(f"pooling segment probs for {len(ids):,} report recordings x {len(STAGES)+1} stages x 2 axes ...",
          flush=True)
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4))) as ex:
        res = [r for rr in ex.map(one, ids) if rr for r in rr]
    D = pd.DataFrame(res)
    D.to_parquet("data/derived/seg2eeg_recovery.parquet", index=False)
    print(f"  pooled table: {len(D):,} rows", flush=True)

    rules = ["max", "p90", "top5_mean", "noisyOR"] + [f"mean_gt_{X}" for X in XGRID] + [f"frac_gt_{X}" for X in XGRID]
    md = ["# Section 1b — recovering EEG-level slowing from 30 s-context segment detections, by stage\n",
          "For each axis, using only ONE stage's segments, we pool them into p_eeg' and score it against "
          "Morgoth's EEG-level head (Spearman rho, 'recover') and the report label (AUROC, 'predict'). Table "
          "shows the BEST rule per (axis, stage) on each target; the selection threshold X is read from the "
          "best `*_gt_X` rule.\n"]

    summary = []
    for axname, pcol, labcol, headcol in AXES:
        y = lab.set_index("eeg_id")[labcol].fillna(False).astype(int)
        h = head.set_index("eeg_id")[headcol]
        A = D[D.axis == axname]
        md.append(f"\n## {axname.upper()} slowing\n")
        md.append("| stage | n EEG | best-recover rule (rho vs head) | best-predict rule (AUROC vs report) |")
        md.append("|---|---|---|---|")
        for st in STAGES + ["ALL"]:
            sub = A[A.stage == st].set_index("eeg_id")
            if len(sub) < 200:
                continue
            hh = h.reindex(sub.index); yy = y.reindex(sub.index)
            best_rec = ("", -1.0); best_pred = ("", -1.0)
            for rule in rules:
                if rule not in sub:
                    continue
                v = sub[rule].values
                ok = np.isfinite(v)
                rho = np.nan; au = np.nan
                # recover: rho vs head
                m2 = ok & hh.notna().values
                if m2.sum() > 100 and np.ptp(v[m2]) > 0:
                    r = spearmanr(v[m2], hh.values[m2]).correlation
                    rho = r if r is not None else np.nan
                    if np.isfinite(rho) and rho > best_rec[1]:
                        best_rec = (rule, rho)
                # predict: AUROC vs report label
                m3 = ok & yy.notna().values
                if m3.sum() > 100 and yy.values[m3].sum() >= 10 and (yy.values[m3] == 0).sum() >= 10 and np.ptp(v[m3]) > 0:
                    try:
                        au = roc_auc_score(yy.values[m3], v[m3])
                        if au > best_pred[1]:
                            best_pred = (rule, au)
                    except Exception:
                        pass
                summary.append({"axis": axname, "stage": st, "rule": rule, "rho_head": rho, "auroc_report": au})
            md.append(f"| {st} | {len(sub):,} | {best_rec[0]} (ρ={best_rec[1]:.2f}) | "
                      f"{best_pred[0]} (AUROC={best_pred[1]:.3f}) |")
    S = pd.DataFrame(summary)
    (RES / "s1_seg2eeg.md").write_text("\n".join(md))
    print("\n".join(md))

    # figure: per stage, AUROC-vs-report of the key rules (max, p90, best mean_gt/frac_gt)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    for axname, pcol, labcol, headcol in AXES:
        y = lab.set_index("eeg_id")[labcol].fillna(False).astype(int)
        A = D[D.axis == axname]
        fig, axx = plt.subplots(1, 2, figsize=(12, 4.5))
        # left: AUROC vs report for max / p90 / noisyOR across stages
        for rule, c in [("max", "#c8443c"), ("p90", "#2c7fb8"), ("top5_mean", "#66a61e"), ("noisyOR", "#8b5cb8")]:
            aus = []
            for st in STAGES + ["ALL"]:
                sub = A[A.stage == st].set_index("eeg_id")
                yy = y.reindex(sub.index); v = sub[rule] if rule in sub else pd.Series(dtype=float)
                ok = v.notna() & yy.notna()
                aus.append(roc_auc_score(yy[ok], v[ok]) if ok.sum() > 100 and yy[ok].nunique() > 1 else np.nan)
            axx[0].plot(range(len(STAGES)+1), aus, "o-", color=c, label=rule)
        axx[0].set_xticks(range(len(STAGES)+1)); axx[0].set_xticklabels(STAGES + ["ALL"])
        axx[0].set_ylabel("AUROC vs report label"); axx[0].set_xlabel("sleep stage")
        axx[0].set_title(f"{axname}: which stage's segments predict the report", fontsize=10)
        axx[0].legend(frameon=False, fontsize=8); axx[0].grid(alpha=.2); axx[0].axhline(.5, ls=":", color="#888")
        # right: mean_gt_X AUROC vs X for the ALL-stage pool (choose selection threshold)
        subA = A[A.stage == "ALL"].set_index("eeg_id"); yA = y.reindex(subA.index)
        for kind, c in [("mean_gt", "#c8443c"), ("frac_gt", "#2c7fb8")]:
            aus = []
            for X in XGRID:
                v = subA[f"{kind}_{X}"]; ok = v.notna() & yA.notna()
                aus.append(roc_auc_score(yA[ok], v[ok]) if ok.sum() > 100 and yA[ok].nunique() > 1 else np.nan)
            axx[1].plot(XGRID, aus, "o-", color=c, label=f"{kind}_X")
        axx[1].set_xlabel("segment-selection threshold X (prob)"); axx[1].set_ylabel("AUROC vs report (ALL stages)")
        axx[1].set_title(f"{axname}: selection threshold X", fontsize=10)
        axx[1].legend(frameon=False, fontsize=8); axx[1].grid(alpha=.2)
        fig.suptitle(f"Recovering EEG-level {axname} slowing from 30 s-context segment probabilities", fontsize=11)
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        fig.savefig(FIG / f"s1_seg2eeg_{axname}.png", dpi=150); plt.close(fig)
    print(f"\nwrote figures/story/s1_seg2eeg_*.png + results/story/s1_seg2eeg.md + data/derived/seg2eeg_recovery.parquet")


if __name__ == "__main__":
    main()
