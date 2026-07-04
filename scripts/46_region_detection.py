"""Per-region ONE-vs-NORMAL slowing detection (Brandon's request).

Different question from the multi-class lobe confusion (which forces one label per case and gets swamped
by temporal). Here, for each region R independently: can we tell recordings that HAVE slowing in R
(regardless of other regions) from NORMAL recordings (no focal slowing)? Positives = reports stating
slowing in R; negatives = normals; score = that region's age-adjusted slowing deviation. Reports AUROC
per region + n, as a bar chart.

Writes results/figs/region_detection_bars.png + results/region_detection.md.
Run: PYTHONPATH=src python scripts/46_region_detection.py
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

_s = importlib.util.spec_from_file_location("p42", str(Path("scripts/42_region_gated.py")))
p42 = importlib.util.module_from_spec(_s); _s.loader.exec_module(p42)
METRICS = p42.METRICS
LOBES = {"frontal": ["Fp1-F3", "Fp2-F4", "Fp1-F7", "Fp2-F8"],
         "temporal": ["F7-T3", "T3-T5", "F8-T4", "T4-T6"],
         "central": ["F3-C3", "F4-C4", "Fz-Cz"],
         "parietal": ["C3-P3", "C4-P4", "Cz-Pz"],
         "occipital": ["T5-O1", "T6-O2", "P3-O1", "P4-O2"]}
REGIONS = ["temporal", "frontal", "central", "parietal", "occipital"]


def main():
    ch = p42.channel_z()                                   # per-channel age-adjusted deviations (z_*)
    rep = pd.read_csv("results/report_extracted_labels.csv").drop_duplicates("bdsp_id").set_index("bdsp_id")
    # region slowing score = mean deviation (rel_delta+DAR+TAR) over that lobe's channels
    scores = {}
    for R, chans in LOBES.items():
        cols = [f"z_{m}" for m in ["rel_delta", "DAR", "TAR"]]
        sub = ch[ch.region.isin(chans)]
        piv = sub.pivot_table(index="bdsp_id", columns="region", values=cols)
        scores[R] = piv.mean(axis=1)                       # one score per recording for region R
    S = pd.DataFrame(scores)                               # index bdsp_id, cols regions
    S = S.join(rep[["label", "region"]], how="inner")
    normal = S[S.label == "normal"]
    rows = []; boot = {}
    rng = np.random.default_rng(0)
    for R in REGIONS:
        pos = S[(S.label != "normal") & (S.region == R)]   # has slowing in R (primary region)
        if len(pos) < 10:
            rows.append({"region": R, "n_pos": len(pos), "auroc": None, "lo": None, "hi": None}); continue
        y = np.r_[np.ones(len(pos)), np.zeros(len(normal))]
        x = np.r_[pos[R].fillna(0).to_numpy(), normal[R].fillna(0).to_numpy()]
        a = roc_auc_score(y, x)
        bs = [roc_auc_score(y[i], x[i]) for i in (rng.integers(0, len(y), len(y)) for _ in range(300))
              if len(np.unique(y[i])) == 2]
        rows.append({"region": R, "n_pos": int(len(pos)), "auroc": round(a, 3),
                     "lo": round(np.percentile(bs, 2.5), 3), "hi": round(np.percentile(bs, 97.5), 3)})
    tab = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ok = tab.dropna(subset=["auroc"])
    yerr = np.abs(np.vstack([ok.auroc - ok.lo, ok.hi - ok.auroc]))
    ax.bar(ok.region, ok.auroc, yerr=yerr, capsize=4, color="#4a90e2")
    for i, r in enumerate(ok.itertuples()):
        ax.text(i, r.auroc + 0.02, f"{r.auroc:.2f}\n(n={r.n_pos})", ha="center", fontsize=8)
    ax.axhline(0.5, ls=":", color="#aaa"); ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("AUROC — region slowing present vs. normal")
    ax.set_title("Per-region slowing detection vs. normal controls (one-vs-normal)")
    ax.grid(alpha=0.25, axis="y")
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/region_detection_bars.png", dpi=130)
    out = ["# Per-region slowing detection (one-vs-normal)\n",
           "For each region: AUROC separating recordings with slowing in that region from normal controls, "
           "using that region's age-adjusted slowing deviation (independent of other regions).\n",
           tab.to_markdown(index=False) + "\n",
           "\n_This is the clinically natural 'can we see region-X slowing at all?' question; unlike the "
           "multi-class lobe confusion it is not swamped by temporal predominance._\n"]
    Path("results/region_detection.md").write_text("\n".join(out))
    print(tab.to_string(index=False))


if __name__ == "__main__":
    main()
