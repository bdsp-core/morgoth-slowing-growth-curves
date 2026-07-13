#!/usr/bin/env python3
"""Recompute the segment_summary-derived arms of the van Putten benchmark at FULL fleet coverage.

WHY: results/vanputten_comparison.md was produced with only 3,130 recordings of `segment_summary`
locally (an incomplete download — S3 has all 27,478). Every metric that lives in segment_summary was
therefore computed on ~11% of the run:
    Q_SLOWING, Q_APG, r_sBSI, pdBSI, Q_ASYM   (whole-head van Putten)
    p_slowing                                  (the MORGOTH GATE — the paper's headline comparator)
This recomputes those on all available segment_summary partitions, using the CORRECTED SAP labels
(scripts/label_rederive_sap.py — which fixes the physiologic-vs-pathologic generalized-slowing bug).

The segment_master-derived arms (DAR/DTABR/SEF95) are untouched here (they had far wider coverage).
Run: PYTHONPATH=src python scripts/recompute_vanputten_fullcov.py
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

SS = "data/derived/segment_summary"
LAB = "data/derived/recording_labels_sap.parquet"
QCOLS = ["Q_SLOWING", "Q_APG", "r_sBSI", "pdBSI", "Q_ASYM"]


def per_recording():
    """Median Q_* over usable segments + p90 of the Morgoth per-segment gate (as the producer used)."""
    rows = []
    for f in glob.glob(f"{SS}/eeg_id=*/part.parquet"):
        eid = f.split("eeg_id=")[1].split("/")[0]
        s = pd.read_parquet(f, columns=["artifact_flag", "p_slowing"] + QCOLS)
        s = s[~s.artifact_flag]
        if s.empty:
            continue
        r = {"eeg_id": eid, "p_slowing_p90": float(np.nanpercentile(s.p_slowing, 90))
             if s.p_slowing.notna().any() else np.nan}
        for c in QCOLS:
            r[c] = float(s[c].median())
        rows.append(r)
    return pd.DataFrame(rows).set_index("eeg_id")


def grid_z(age_ref, v_ref, age_q, v_q, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    """Age-conditioned deviation vs the clean-normal reference (same kernel the producer used)."""
    ok = np.isfinite(age_ref) & np.isfinite(v_ref); ar, vr = age_ref[ok], v_ref[ok]
    if len(ar) < 20:
        return np.full(len(v_q), np.nan)
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((ar - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * vr).sum() / sw; mu[j] = m
        sd[j] = np.sqrt(max((w * (vr - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (v_q - np.interp(age_q, grid[good], mu[good], np.nan, np.nan)) / \
           np.interp(age_q, grid[good], sd[good], np.nan, np.nan)


def auc_ci(y, s, rng, n=300):
    s = np.asarray(s, float); m = np.isfinite(s)
    y2, s2 = np.asarray(y)[m], s[m]
    if m.sum() < 20 or len(np.unique(y2)) < 2:
        return (np.nan, np.nan, np.nan, int(m.sum()))
    a = roc_auc_score(y2, s2)
    if a < 0.5:
        s2 = -s2; a = 1 - a
    bs = []
    for _ in range(n):
        j = rng.integers(0, len(y2), len(y2))
        if len(np.unique(y2[j])) == 2:
            bs.append(roc_auc_score(y2[j], s2[j]))
    return (round(a, 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3), int(m.sum()))


def main():
    vp = per_recording()
    lab = pd.read_parquet(LAB).drop_duplicates("eeg_id").set_index("eeg_id")
    d = vp.join(lab, how="inner")
    print(f"segment_summary partitions read : {len(vp):,}")
    print(f"joined to corrected SAP labels   : {len(d):,}")
    print(f"Q_SLOWING coverage               : {int(d.Q_SLOWING.notna().sum()):,}"
          f"   (was 3,130 in the committed results)")
    print(f"Morgoth p_slowing coverage       : {int(d.p_slowing_p90.notna().sum()):,}\n")

    # age-conditioned deviation FIRST (reference = clean-normal), so the slices below carry the _z cols
    ref = d[d.clean_normal == True]                                      # noqa: E712
    for c in QCOLS + ["p_slowing_p90"]:
        d[c + "_z"] = grid_z(ref.age.values.astype(float), ref[c].values.astype(float),
                             d.age.values.astype(float), d[c].values.astype(float))

    # contrasts, using the CORRECTED labels (sliced AFTER _z exists)
    norm = d[d.clean_normal == True]                                     # noqa: E712
    pos = d[d.slowing_positive == True]                                  # noqa: E712
    gen = d[(d.clean_normal == True) | (d.slowing_gen_pathologic == True)]   # noqa: E712
    foc = d[(d.clean_normal == True) | (d.slowing_focal == True)]         # noqa: E712
    print(f"contrasts — abnormal: {len(norm):,} normal vs {len(pos):,} slowing-positive | "
          f"gen-path: {int((gen.slowing_gen_pathologic == True).sum()):,} | "
          f"focal: {int((foc.slowing_focal == True).sum()):,}\n")

    rng = np.random.default_rng(0)
    ab = pd.concat([norm, pos]); y_ab = ab.slowing_positive.astype(int).values
    y_g = gen.slowing_gen_pathologic.fillna(False).astype(int).values
    y_f = foc.slowing_focal.fillna(False).astype(int).values

    def arm(col):
        return auc_ci(y_ab, ab[col], rng), auc_ci(y_g, gen[col], rng), auc_ci(y_f, foc[col], rng)

    specs = [("Q_SLOWING (raw) [vP2013]", "Q_SLOWING"), ("Q_APG (raw)", "Q_APG"),
             ("r_sBSI (raw)", "r_sBSI"), ("Q_ASYM (raw)", "Q_ASYM"),
             ("Q_SLOWING (age-normed)", "Q_SLOWING_z"), ("r_sBSI (age-normed)", "r_sBSI_z"),
             ("** Morgoth p_slowing (gate) **", "p_slowing_p90")]
    out = []
    for name, col in specs:
        if col not in d.columns:
            continue
        A, G, F = arm(col)
        out.append({"method": name,
                    "abnormal": f"{A[0]} [{A[1]}–{A[2]}]", "generalized": f"{G[0]} [{G[1]}–{G[2]}]",
                    "focal": f"{F[0]} [{F[1]}–{F[2]}]", "n_scored": A[3]})
    tab = pd.DataFrame(out)
    print(tab.to_string(index=False))
    Path("results").mkdir(exist_ok=True)
    Path("results/vanputten_fullcoverage.md").write_text(
        "# van Putten benchmark — segment_summary arms at FULL fleet coverage\n\n"
        f"Recomputed on **{int(d.Q_SLOWING.notna().sum()):,}** recordings (the committed table used only "
        "**3,130** — an incomplete `segment_summary` download, not a fleet gap; S3 has all 27,478).\n\n"
        "Labels are the CORRECTED SAP labels (`label_rederive_sap.py`; physiologic generalized slowing is "
        "NOT a positive). AUROC [95% bootstrap CI].\n\n" + tab.to_markdown(index=False) + "\n")
    print("\nwrote results/vanputten_fullcoverage.md")


if __name__ == "__main__":
    main()
