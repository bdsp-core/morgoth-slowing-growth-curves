"""Head-to-head vs prior quantitative-slowing methods (van Putten lineage) — Brandon's request.

Implements the standard published metrics and scores them against the SAME report labels as our methods:
  - DAR   = delta/alpha ratio (whole head)                         [Finnigan & van Putten 2013]
  - DTABR = (delta+theta)/(alpha+beta) ratio (whole head)          [Finnigan & van Putten 2013]
  - BSI   = Brain Symmetry Index: mean over homologous pairs & bands of |R-L|/(R+L)  [van Putten 2004/2007]
Compared to: our AGE/SEX-NORMED deviation of the same quantities (adjusted_z), and Morgoth (gate_probs).
Targets: abnormal-vs-normal, generalized-vs-normal (global metrics), focal-vs-normal (asymmetry metrics).
The scientific point: raw fixed-threshold metrics ignore age/sex/stage; our normed deviation should beat
them. Writes results/vanputten_comparison.md + results/figs/vanputten_comparison.png.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

PAIRS = [("Fp1-F3", "Fp2-F4"), ("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"),
         ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("T5-O1", "T6-O2"), ("P3-O1", "P4-O2")]
BANDS = ["delta", "theta", "alpha", "beta"]


def auroc(y, s):
    s = np.asarray(s, float); m = ~np.isnan(s)
    if m.sum() < 20 or len(np.unique(y[m])) < 2:
        return None
    a = roc_auc_score(y[m], s[m]); return round(max(a, 1 - a), 3)


def main():
    rf = pd.read_parquet("data/derived/recording_features.parquet")
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "label"]].drop_duplicates("bdsp_id").set_index("bdsp_id")
    LB = ["log_delta", "log_theta", "log_alpha", "log_beta"]
    wh = rf[rf.region == "whole_head"].groupby("bdsp_id")[LB].mean()   # dedupe multi-session
    # --- van Putten raw metrics ---
    P = pd.DataFrame(index=wh.index)
    P["DAR"] = np.exp(wh.log_delta) / np.exp(wh.log_alpha)
    P["DTABR"] = (np.exp(wh.log_delta) + np.exp(wh.log_theta)) / (np.exp(wh.log_alpha) + np.exp(wh.log_beta))
    # BSI over homologous channel pairs & bands
    powers = {}
    for ch in set(c for p in PAIRS for c in p):
        r = rf[rf.region == ch].groupby("bdsp_id")[LB].mean()
        for b in BANDS:
            powers[(ch, b)] = np.exp(r[f"log_{b}"])
    bsi = pd.DataFrame(index=wh.index)
    contribs = []
    for L, R in PAIRS:
        for b in BANDS:
            l = powers.get((L, b)); rr = powers.get((R, b))
            if l is not None and rr is not None:
                contribs.append((np.abs(rr - l) / (rr + l + 1e-12)).rename(f"{L}_{b}"))
    P["BSI"] = pd.concat(contribs, axis=1).mean(axis=1)

    # --- our age/sex-normed deviations (same quantities) ---
    az = pd.read_parquet("data/derived/adjusted_z.parquet")
    def dev(feat):
        s = az[(az.feature == feat) & (az.region == "whole_head")].groupby("bdsp_id").z.mean()
        return s
    ours = pd.DataFrame({"our_DAR_z": dev("DAR"), "our_logdelta_z": dev("log_delta")})
    asym = pd.read_parquet("data/derived/recording_asymmetry.parquet").drop_duplicates("bdsp_id").set_index("bdsp_id")
    nmA = asym[asym.label == "normal"].asym_temporal_delta
    ours["our_asym_z"] = (asym.asym_temporal_delta - nmA.mean()).abs() / (nmA.std() + 1e-9)  # magnitude
    bz = pd.read_parquet("data/derived/bsi_features.parquet").bsi_z
    ours["our_BSI_z"] = bz
    # --- Morgoth ---
    g = pd.read_parquet("data/derived/gate_probs.parquet").drop_duplicates("bdsp_id").set_index("bdsp_id")

    df = P.join(ours, how="outer").join(g[["p_abnormal", "p_slowing", "p_focal"]], how="outer").join(meta, how="inner")
    df = df[df.label.isin(["normal", "focal_slow", "general_slow"])]
    y_ab = (df.label != "normal").astype(int).to_numpy()
    foc = df[df.label.isin(["normal", "focal_slow"])]; y_f = (foc.label != "normal").astype(int).to_numpy()
    gen = df[df.label.isin(["normal", "general_slow"])]; y_g = (gen.label != "normal").astype(int).to_numpy()

    rows = [
        ("van Putten DAR", auroc(y_ab, df.DAR), auroc(y_f, foc.DAR), auroc(y_g, gen.DAR)),
        ("van Putten DTABR", auroc(y_ab, df.DTABR), auroc(y_f, foc.DTABR), auroc(y_g, gen.DTABR)),
        ("van Putten BSI", auroc(y_ab, df.BSI), auroc(y_f, foc.BSI), auroc(y_g, gen.BSI)),
        ("ours: DAR deviation (age/sex)", auroc(y_ab, df.our_DAR_z), auroc(y_f, foc.our_DAR_z), auroc(y_g, gen.our_DAR_z)),
        ("ours: |temporal asym| dev", auroc(y_ab, df.our_asym_z), auroc(y_f, foc.our_asym_z), auroc(y_g, gen.our_asym_z)),
        ("ours: BSI deviation (age/sex)", auroc(y_ab, df.our_BSI_z), auroc(y_f, foc.our_BSI_z), auroc(y_g, gen.our_BSI_z)),
        ("Morgoth p_abnormal", auroc(y_ab, df.p_abnormal), auroc(y_f, foc.p_abnormal), auroc(y_g, gen.p_abnormal)),
        ("Morgoth p_focal", auroc(y_ab, df.p_focal), auroc(y_f, foc.p_focal), auroc(y_g, gen.p_focal)),
    ]
    tab = pd.DataFrame(rows, columns=["method", "abnormal", "focal", "generalized"])
    print(tab.to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(tab)); w = 0.26
    for i, t in enumerate(["abnormal", "focal", "generalized"]):
        ax.bar(x + (i - 1) * w, tab[t].fillna(0), w, label=t)
    ax.axhline(0.5, ls=":", color="#aaa"); ax.set_ylim(0.4, 1.0); ax.set_ylabel("AUROC vs report label")
    ax.set_xticks(x); ax.set_xticklabels(tab.method, rotation=35, ha="right", fontsize=8)
    ax.set_title("Prior slowing metrics (van Putten) vs ours vs Morgoth"); ax.legend(); ax.grid(alpha=0.25, axis="y")
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/vanputten_comparison.png", dpi=130)
    out = ["# Comparison vs prior quantitative-slowing methods (van Putten lineage)\n",
           "AUROC vs the clinical report label. Raw metrics use no age/sex/stage normalization (as clinically "
           "applied); our versions are age/sex-normed deviations of the same quantities.\n",
           tab.to_markdown(index=False) + "\n",
           "\n_DAR/DTABR are global-slowing severity metrics (abnormal/generalized); BSI is an asymmetry "
           "metric (focal). References: van Putten 2004/2007 (BSI); Finnigan & van Putten 2013 (DAR, "
           "(δ+θ)/(α+β)). BSI is unsigned (detects asymmetry, not side) — our signed asymmetry adds "
           "lateralization on top._\n"]
    Path("results/vanputten_comparison.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
