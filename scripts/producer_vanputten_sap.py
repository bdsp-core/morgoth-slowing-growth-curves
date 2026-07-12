#!/usr/bin/env python3
"""SAP §8.7 / Table 6 — van Putten benchmark, REWRITTEN to use the FLEET-COMPUTED faithful metrics.

Discrepancy vs old scripts/47: the old code hand-rolled DAR/DTABR and an ad-hoc |R-L|/(R+L) 'BSI' from
log-powers, omitted Q_SLOWING (van Putten's own best metric, κ=0.76), Q_APG and Q_ASYM entirely, used no
stage/bootstrap, and read a legacy label CSV. The re-planned fleet ALREADY persists the faithful metrics:
  segment_master  : DTABR, ADR, SEF95, median_freq, peak_freq (per channel) ; log_DAR/log_TAR (whole-head via median)
  segment_summary : Q_SLOWING (P[2-8]/P[2-25]), Q_APG, r_sBSI, pdBSI, Q_ASYM (whole-head)
So this producer READS those (SAP §4.5) instead of re-deriving them. Three arms (SAP §8.7):
  raw (as-published) | normed (age-conditioned deviation z) | ours+Morgoth.
Targets: abnormal / generalized / focal vs clean-normal. AUROC + patient bootstrap CI.
NEW-DATA-ONLY: segment_master + segment_summary + report_manifest_v6.

Writes results/figs/vanputten_comparison.png + results/vanputten_comparison.md
Run: PYTHONPATH=src python scratchpad/producer_vanputten_sap.py
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

REPO = "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
SM = f"{REPO}/data/derived/segment_master"; SS = f"{REPO}/data/derived/segment_summary"
CH18 = None


def recording_vanputten():
    """Per-recording faithful van Putten metrics from the fleet output."""
    rows = []
    # whole-head DTABR/ADR/SEF95 + DAR/TAR from segment_master (median over usable segments)
    for f in sorted(glob.glob(f"{SM}/eeg_id=*/part.parquet")):
        eid = f.split("eeg_id=")[1].split("/")[0]
        d = pd.read_parquet(f, columns=["artifact_flag", "channel", "log_DAR", "log_TAR",
                                        "DTABR", "ADR", "SEF95", "median_freq"])
        d = d[d.artifact_flag == False]
        if d.empty:
            continue
        rows.append({"bdsp_id": eid,
                     "DAR": float(np.exp(d.log_DAR).median()),
                     "DTABR": float(d.DTABR.median()),
                     "ADR": float(d.ADR.median()),
                     "SEF95": float(d.SEF95.median()),
                     "median_freq": float(d.median_freq.median())})
    vp = pd.DataFrame(rows).set_index("bdsp_id")
    # whole-head Q_* from segment_summary (median over usable segments)  -- thinner coverage
    qrows = []
    for f in sorted(glob.glob(f"{SS}/eeg_id=*/part.parquet")):
        eid = f.split("eeg_id=")[1].split("/")[0]
        s = pd.read_parquet(f, columns=["artifact_flag", "Q_SLOWING", "Q_APG", "r_sBSI", "pdBSI", "Q_ASYM"])
        s = s[s.artifact_flag == False]
        if s.empty:
            continue
        qrows.append({"bdsp_id": eid, "Q_SLOWING": float(s.Q_SLOWING.median()),
                      "Q_APG": float(s.Q_APG.median()), "r_sBSI": float(s.r_sBSI.median()),
                      "Q_ASYM": float(s.Q_ASYM.median())})
    q = pd.DataFrame(qrows).set_index("bdsp_id")
    return vp.join(q, how="left")


def grid_z(age_ref, v_ref, age_q, v_q, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    ok = np.isfinite(age_ref) & np.isfinite(v_ref); ar, vr = age_ref[ok], v_ref[ok]
    if len(ar) < 20:
        return np.full(len(v_q), np.nan)
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((ar - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * vr).sum() / sw; mu[j] = m; sd[j] = np.sqrt(max((w * (vr - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (v_q - np.interp(age_q, grid[good], mu[good], np.nan, np.nan)) / \
           np.interp(age_q, grid[good], sd[good], np.nan, np.nan)


def auc_ci(y, s, rng, n=300):
    s = np.asarray(s, float); m = np.isfinite(s); y2, s2 = np.asarray(y)[m], s[m]
    if m.sum() < 20 or len(np.unique(y2)) < 2:
        return (np.nan, np.nan, np.nan)
    a = roc_auc_score(y2, s2)
    flip = a < 0.5
    if flip:
        s2 = -s2; a = 1 - a
    bs = []
    for _ in range(n):
        j = rng.integers(0, len(y2), len(y2))
        if len(np.unique(y2[j])) == 2:
            bs.append(roc_auc_score(y2[j], s2[j]))
    return (round(a, 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3))


def main():
    # labels from the FLEET labels_unified (authoritative; general_slow = PATHOLOGIC generalized only,
    # per the fleet's phys-vs-path gen classifier -- has_gen_slow would fold in physiologic drowsiness)
    man = pd.read_parquet(f"{REPO}/data/derived/labels_unified.parquet").drop_duplicates("bdsp_id").set_index("bdsp_id")
    vp = recording_vanputten().join(man[["age", "label"]], how="inner")
    print(f"recordings with fleet vP metrics: {len(vp)} (Q_* coverage: {vp.Q_SLOWING.notna().sum()})")

    # normed arm: age-conditioned deviation vs clean-normal, per metric (higher = slower for DAR/DTABR/Q_SLOWING/r_sBSI;
    # SEF95/median_freq/ADR/Q_APG are inverse -> auc_ci auto-orients)
    ref = vp[vp.label == "normal"]
    for c in ["DAR", "DTABR", "ADR", "SEF95", "median_freq", "Q_SLOWING", "Q_APG", "r_sBSI", "Q_ASYM"]:
        vp[c + "_z"] = grid_z(ref.age.values.astype(float), ref[c].values.astype(float),
                              vp.age.values.astype(float), vp[c].values.astype(float))
    # Morgoth gate (pooled p_slowing p90)
    gp = pd.read_parquet(f"{REPO}/data/derived/gate_probs.parquet").set_index("bdsp_id")
    vp = vp.join(gp[["p_slowing_p90"]], how="left")

    rng = np.random.default_rng(0)
    ab = vp[vp.label.isin(["normal", "focal_slow", "general_slow"])]; y_ab = (ab.label != "normal").astype(int).values
    gen = vp[vp.label.isin(["normal", "general_slow"])]; y_g = (gen.label != "normal").astype(int).values
    foc = vp[vp.label.isin(["normal", "focal_slow"])]; y_f = (foc.label != "normal").astype(int).values

    def row(name, col):
        return (name, auc_ci(y_ab, ab[col], rng), auc_ci(y_g, gen[col], rng), auc_ci(y_f, foc[col], rng))

    specs = [
        ("Q_SLOWING (raw) [vP2013 κ.76]", "Q_SLOWING"),
        ("DAR (raw)", "DAR"), ("DTABR (raw)", "DTABR"), ("SEF95 (raw)", "SEF95"),
        ("r_sBSI (raw)", "r_sBSI"), ("Q_APG (raw)", "Q_APG"), ("Q_ASYM (raw)", "Q_ASYM"),
        ("Q_SLOWING (age-normed)", "Q_SLOWING_z"), ("DAR (age-normed)", "DAR_z"),
        ("DTABR (age-normed)", "DTABR_z"), ("r_sBSI (age-normed)", "r_sBSI_z"),
        ("Morgoth p_slowing (gate)", "p_slowing_p90"),
    ]
    rows = [row(n, c) for n, c in specs if c in vp.columns]
    tab = pd.DataFrame([(n, a[0], g[0], f[0]) for n, a, g, f in rows],
                       columns=["method", "abnormal", "generalized", "focal"])
    print(tab.to_string(index=False))

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(tab)); w = 0.26
    for i, t in enumerate(["abnormal", "generalized", "focal"]):
        ax.bar(x + (i - 1) * w, tab[t].fillna(0), w, label=t)
    ax.axhline(0.5, ls=":", color="#aaa"); ax.set_ylim(0.4, 1.0); ax.set_ylabel("AUROC vs report label")
    ax.set_xticks(x); ax.set_xticklabels(tab.method, rotation=40, ha="right", fontsize=8)
    ax.set_title("van Putten metrics (fleet-computed, faithful) — raw vs age-normed vs Morgoth (SAP §8.7)\n"
                 f"n={len(ab)} abnormal-contrast; Q_* on {vp.Q_SLOWING.notna().sum()} recs w/ segment_summary")
    ax.legend(); ax.grid(alpha=0.25, axis="y")
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/vanputten_comparison.png", dpi=130)

    md = ["# van Putten benchmark (SAP §8.7, Table 6) — fleet-computed faithful metrics\n",
          f"n = {len(ab)} (abnormal contrast); Q_SLOWING/Q_APG/r_sBSI/Q_ASYM available on "
          f"{vp.Q_SLOWING.notna().sum()} recordings (segment_summary coverage, partial fleet run).\n",
          "AUROC (point est.; auto-oriented so >0.5). Three arms per SAP: raw as-published, "
          "age-conditioned deviation, Morgoth gate.\n", tab.to_markdown(index=False)]
    Path("results/vanputten_comparison.md").write_text("\n".join(md))
    print("wrote results/figs/vanputten_comparison.png + .md")


if __name__ == "__main__":
    main()
