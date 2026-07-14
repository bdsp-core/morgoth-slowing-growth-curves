#!/usr/bin/env python3
"""Table 4 — the PRE-REGISTERED PREDICTIONS SCORECARD (SAP §10). Never produced until now.

The point of pre-registering P1–P8b is to report every one of them against its stated falsification
threshold, including the ones that fail. This builds that table from the completed v6 run, and marks
UNEVALUATED anything we cannot yet honestly score (rather than quietly omitting it).

Also computes P7 properly: the prediction is about BALANCED ACCURACY vs the between-rater ceiling, not
AUROC. We score our gate at an operating point chosen leave-one-out (no EEG informs its own threshold),
against the expert majority, and compare with the average expert's balanced accuracy vs their peers.

Run: PYTHONPATH=src python scripts/table4_predictions_scorecard.py
"""
import glob, json, os
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, balanced_accuracy_score

SCR = os.environ.get("PANEL_SCRATCH",
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
XLS = f"{SCR}/moe/occ/Occasion.xlsx"


# ---------------------------------------------------------------- P7: ceiling comparison
def p7_ceiling():
    db = pd.ExcelFile(XLS).parse("DB")
    d = db[["fid", "uid", "r1.FN", "r1.GN"]].dropna()
    d = d.assign(FN=(d["r1.FN"] > 0).astype(int), GN=(d["r1.GN"] > 0).astype(int))
    sc = pd.read_parquet("data/derived/panel_v6_scores.parquet")
    out = {}
    for tag, col, score_col in [("focal", "FN", "p_focal"), ("generalized", "GN", "p_generalized")]:
        agg = d.groupby("fid")[col].agg(["sum", "size"])
        maj = (agg["sum"] / agg["size"] > 0.5).astype(int)
        m = sc.set_index("fid")[score_col].reindex(maj.index)
        ok = m.notna()
        y, s = maj[ok].values, m[ok].values

        # OUR balanced accuracy, threshold chosen LEAVE-ONE-OUT (no EEG informs its own call)
        preds = []
        for i in range(len(y)):
            mask = np.ones(len(y), bool); mask[i] = False
            ths = np.unique(s[mask])
            best_t, best_b = 0.5, -1
            for t in ths:
                b = balanced_accuracy_score(y[mask], (s[mask] >= t).astype(int))
                if b > best_b:
                    best_b, best_t = b, t
            preds.append(int(s[i] >= best_t))
        ours_bacc = balanced_accuracy_score(y, preds)
        ours_auroc = roc_auc_score(y, s)

        # THE CEILING: average expert vs the majority of their peers
        accs = []
        for uid, g in d.groupby("uid"):
            others = d[d.uid != uid]
            om = others.groupby("fid")[col].mean()
            omaj = (om > 0.5).astype(int)
            j = g.set_index("fid")[col].reindex(omaj.index).dropna()
            if j.nunique() < 2 or omaj.loc[j.index].nunique() < 2:
                continue
            accs.append(balanced_accuracy_score(omaj.loc[j.index], j))
        ceiling = float(np.mean(accs))
        out[tag] = dict(ours_bacc=ours_bacc, ours_auroc=ours_auroc, ceiling=ceiling,
                        verdict="CONFIRMED" if ours_bacc >= ceiling else "FALSIFIED")
    return out


def main():
    p7 = p7_ceiling()
    print("P7 — our balanced accuracy vs the between-rater ceiling (100 EEGs, 18 experts):")
    for k, v in p7.items():
        print(f"  {k:12} ours {v['ours_bacc']:.3f} (AUROC {v['ours_auroc']:.3f})  vs ceiling "
              f"{v['ceiling']:.3f}  -> {v['verdict']}")

    # --- van Putten arms, from the full-coverage recompute (P8a / P8b) ---
    # values sourced from results/vanputten_fullcoverage.md (27,003 recordings)
    vp = {  # metric: (raw, age-normed) per target  -- generalized shown; see Table 6 for all
        "Q_SLOWING": {"abnormal": (0.654, 0.692), "generalized": (0.702, 0.751), "focal": (0.630, 0.671)},
        "r_sBSI":    {"abnormal": (0.698, 0.686), "generalized": (0.692, 0.675), "focal": (0.726, 0.715)},
    }
    ours = {"abnormal": 0.881, "generalized": 0.918, "focal": 0.875}   # Morgoth gate
    p8a = []
    for met, tg in vp.items():
        for t, (raw, normed) in tg.items():
            p8a.append({"metric": met, "target": t, "raw": raw, "normed": normed,
                        "delta": round(normed - raw, 3),
                        "verdict": "CONFIRMED" if normed - raw > 0 else "FALSIFIED"})
    p8a = pd.DataFrame(p8a)
    print("\nP8a — does age-norming a van Putten metric beat it as-published? (falsified if delta <= 0)")
    print(p8a.to_string(index=False))

    best_vp = {"abnormal": 0.698, "generalized": 0.751, "focal": 0.726}
    p8b = [{"target": t, "ours(Morgoth)": ours[t], "best van Putten": best_vp[t],
            "margin": round(ours[t] - best_vp[t], 3),
            "verdict": "CONFIRMED (no adoption)" if ours[t] - best_vp[t] > -0.02 else "ADOPT THEIRS"}
           for t in ours]
    p8b = pd.DataFrame(p8b)
    print("\nP8b — is our score >= the best van Putten on each target? (adopt theirs if they beat us by >0.02)")
    print(p8b.to_string(index=False))

    # ---------------- the scorecard ----------------
    rows = [
        dict(P="P1", prediction="Detection AUROC >= 0.80 whole-recording, vigilance-matched",
             falsified_if="< 0.75",
             result="Morgoth gate 0.881 (any slowing); sparse score 0.844; normative deviation 0.806 (N1) / 0.784 (W)",
             verdict="CONFIRMED"),
        dict(P="P2", prediction="Sex can be pooled in the norms", falsified_if="dAUROC from adding sex > 0.01",
             result="dAUROC <= 0.002 (prior run); NOT re-verified on v6",
             verdict="CONFIRMED (pending v6 re-verification)"),
        dict(P="P3", prediction="Amount score is reliable", falsified_if="split-half ICC < 0.8",
             result="Table 3 (descriptor reliability) not yet produced", verdict="UNEVALUATED"),
        dict(P="P4", prediction="Prevalence descriptor is reliable", falsified_if="ICC < 0.8",
             result="Table 3 (descriptor reliability) not yet produced", verdict="UNEVALUATED"),
        dict(P="P5", prediction="Band call is WEAK (report only as low-confidence)",
             falsified_if="band-match > 0.8 (then promote it)",
             result="near-chance against per-expert band calls (kappa 0.01-0.07)",
             verdict="CONFIRMED (weak, as predicted)"),
        dict(P="P6", prediction="Readers under-report SLEEP slowing", falsified_if="our sleep rate <= report rate",
             result="LITERAL criterion: our sleep-slowing rate 15.6% <= report slowing rate 48.2% -> falsified. "
                    "BUT the conditional (non-circular) test supports the phenomenon: readers name slowing in "
                    "75.0% of recordings where it is visible AWAKE vs only 54.1% where it is visible ONLY IN "
                    "SLEEP (n=4,280 vs 703, clean_pair). The pre-registered criterion compares a 95th-centile "
                    "exceedance rate (~5% in normals BY CONSTRUCTION) against the report's overall slowing rate "
                    "- not commensurable quantities. Falsified as written; phenomenon supported.",
             verdict="FALSIFIED (as written) / phenomenon SUPPORTED"),
        dict(P="P7", prediction="Our detection meets/exceeds the human ceiling",
             falsified_if="our balanced acc < between-rater ceiling",
             result=f"focal: ours {p7['focal']['ours_bacc']:.3f} vs ceiling {p7['focal']['ceiling']:.3f}; "
                    f"generalized: ours {p7['generalized']['ours_bacc']:.3f} vs ceiling "
                    f"{p7['generalized']['ceiling']:.3f}",
             verdict=f"focal {p7['focal']['verdict']} / generalized {p7['generalized']['verdict']}"),
        dict(P="P8a", prediction="Age-norming a van Putten metric beats it as-published",
             falsified_if="dAUROC(normed - raw) <= 0",
             result="Q_SLOWING +0.038/+0.049/+0.041 (CONFIRMED); r_sBSI -0.012/-0.017/-0.011 (FALSIFIED)",
             verdict="MIXED — confirmed for the slowing indices, falsified for the asymmetry index"),
        dict(P="P8b", prediction="Our best score >= best van Putten on each target",
             falsified_if="any van Putten arm beats ours by dAUROC > 0.02 -> adopt it",
             result="Morgoth 0.881/0.918/0.875 vs best vP 0.698/0.751/0.726 (margin +0.18/+0.17/+0.15)",
             verdict="CONFIRMED (no adoption triggered)"),
    ]
    tab = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True)
    md = ["# Table 4 — Pre-registered predictions scorecard (SAP §10)\n",
          "Every pre-registered prediction, scored against its stated falsification threshold on the "
          "completed v6 run. Predictions we could not yet honestly score are marked **UNEVALUATED** "
          "rather than omitted.\n", tab.to_markdown(index=False), "\n",
          "## P7 detail — the human ceiling\n", pd.DataFrame(p7).T.round(3).to_markdown(), "\n",
          "## P8a detail — does our normative framing improve HIS instruments?\n",
          p8a.to_markdown(index=False), "\n",
          "## P8b detail — the adoption rule\n", p8b.to_markdown(index=False), "\n"]
    Path("results/table4_predictions.md").write_text("\n".join(md))
    print("\n" + tab[["P", "verdict"]].to_string(index=False))
    print("\nwrote results/table4_predictions.md")


if __name__ == "__main__":
    main()
