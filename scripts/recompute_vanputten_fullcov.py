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

SM = "data/derived/segment_master"          # per-channel arms (DAR/DTABR/ADR/SEF95/median_freq)
SS = "data/derived/segment_summary"         # whole-head arms (Q_*) + the Morgoth gate
LAB = "data/derived/recording_labels_sap.parquet"
QCOLS = ["Q_SLOWING", "Q_APG", "r_sBSI", "pdBSI", "Q_ASYM"]
CACHE = Path("data/derived/_vp_per_recording.parquet")   # reading 27k parquets is slow — cache it


def per_recording():
    """Per-recording van Putten metrics, median over USABLE segments, at full fleet coverage.
    segment_summary -> Q_* + Morgoth p_slowing(p90);  segment_master -> DAR/DTABR/ADR/SEF95/median_freq."""
    if CACHE.exists():
        print(f"(using cached {CACHE})")
        return pd.read_parquet(CACHE).set_index("eeg_id")
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
    q = pd.DataFrame(rows).set_index("eeg_id")
    print(f"  segment_summary: {len(q):,} recordings")

    mrows = []
    for f in glob.glob(f"{SM}/eeg_id=*/part.parquet"):
        eid = f.split("eeg_id=")[1].split("/")[0]
        d = pd.read_parquet(f, columns=["artifact_flag", "log_DAR", "log_TAR", "DTABR",
                                        "ADR", "SEF95", "median_freq"])
        d = d[~d.artifact_flag]
        if d.empty:
            continue
        mrows.append({"eeg_id": eid,
                      "DAR": float(np.exp(d.log_DAR.median())), "TAR": float(np.exp(d.log_TAR.median())),
                      "DTABR": float(d.DTABR.median()), "ADR": float(d.ADR.median()),
                      "SEF95": float(d.SEF95.median()), "median_freq": float(d.median_freq.median())})
    m = pd.DataFrame(mrows).set_index("eeg_id")
    print(f"  segment_master : {len(m):,} recordings")
    out = m.join(q, how="outer")
    out.reset_index().to_parquet(CACHE, index=False)
    return out


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


def auc_ci(y, s, rng, n=300, groups=None):
    """AUROC with a PATIENT-CLUSTERED bootstrap (SAP §3.3).

    One patient can contribute several EEGs, so resampling RECORDINGS treats correlated observations as
    independent and yields intervals that are too narrow. We instead resample PATIENTS with replacement and
    take all of that patient's recordings — the standard cluster bootstrap."""
    s = np.asarray(s, float); m = np.isfinite(s)
    y2, s2 = np.asarray(y)[m], s[m]
    g2 = np.asarray(groups)[m] if groups is not None else np.arange(len(y2))
    if m.sum() < 20 or len(np.unique(y2)) < 2:
        return (np.nan, np.nan, np.nan, int(m.sum()))
    a = roc_auc_score(y2, s2)
    flip = a < 0.5
    if flip:
        s2 = -s2; a = 1 - a
    # index the recordings belonging to each patient once
    uniq, inv = np.unique(g2, return_inverse=True)
    by_pat = [np.where(inv == k)[0] for k in range(len(uniq))]
    bs = []
    for _ in range(n):
        pick = rng.integers(0, len(uniq), len(uniq))            # resample PATIENTS
        j = np.concatenate([by_pat[k] for k in pick])
        if len(np.unique(y2[j])) == 2:
            bs.append(roc_auc_score(y2[j], s2[j]))
    return (round(a, 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3), int(m.sum()))


def make_figure(arms):
    """Figure S7 — best van Putten qEEG index vs the learned representation, per contrast, with bootstrap CIs.
    Reproducible producer of results/figs/vanputten_comparison.png (supersedes the old orphaned figure)."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from morgoth_slowing.viz import palette  # noqa: F401  (applies shared Tufte publication style)
    morg = arms.get("** Morgoth p_slowing (gate) **")
    vp = {k: v for k, v in arms.items() if not k.startswith("**")}
    if morg is None or not vp:
        return
    v = lambda rows: [float(rows[i][0]) for i in range(3)]
    e = lambda rows: [[float(rows[i][0]) - float(rows[i][1]) for i in range(3)],
                      [float(rows[i][2]) - float(rows[i][0]) for i in range(3)]]
    best = [max(vp.values(), key=lambda t: float(t[i][0]))[i] for i in range(3)]
    mrow = [morg[i] for i in range(3)]
    fig, ax = plt.subplots(figsize=(7, 4.2)); x = np.arange(3); w = 0.36
    ax.bar(x - w / 2, v(best), w, yerr=e(best), capsize=3, color="#9aa0a6", label="best van Putten index")
    ax.bar(x + w / 2, v(mrow), w, yerr=e(mrow), capsize=3, color="#6a3d9a", label="Morgoth gate (foundation model)")
    ax.axhline(0.5, ls="--", color="#bbb", lw=1); ax.text(2.46, 0.505, "chance", color="#999", fontsize=8, va="bottom", ha="right")
    ax.set_xticks(x); ax.set_xticklabels(["Any abnormal", "Generalized", "Focal"]); ax.set_ylim(0.5, 1.0)
    ax.set_ylabel("AUROC (auto-oriented > 0.5)")
    ax.set_title("Slowing detection: best van Putten qEEG index vs the Morgoth foundation-model gate\n"
                 "(each contrast one-vs-clean-normal; patient-clustered bootstrap 95% CI)", fontsize=9.5)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    for xi, val in zip(x - w / 2, v(best)):
        ax.text(xi, val + 0.012, f"{val:.2f}", ha="center", fontsize=8)
    for xi, val in zip(x + w / 2, v(mrow)):
        ax.text(xi, val + 0.012, f"{val:.2f}", ha="center", fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("results/figs/vanputten_comparison.png", dpi=300); plt.close(fig)
    print("wrote results/figs/vanputten_comparison.png")


def main():
    vp = per_recording()
    lab = pd.read_parquet(LAB).drop_duplicates("eeg_id").set_index("eeg_id")
    d = vp.join(lab, how="inner")
    print(f"segment_summary partitions read : {len(vp):,}")
    print(f"joined to corrected SAP labels   : {len(d):,}")
    # SAP 3.3 PITFALL 1 (report-broadcast guard): a single report is stamped onto up to 170 EEGs of the
    # same patient, so a recording that is not `clean_pair` carries a label describing a DIFFERENT study.
    # Every label-dependent analysis must filter to clean_pair -- and this table is label-dependent
    # (slowing-positive / focal / generalized vs clean-normal). It previously did not, which quietly put
    # ~840 borrowed-label recordings into the headline benchmark.
    _n0 = len(d)
    d = d[d.clean_pair == True]                                          # noqa: E712
    print(f"after SAP 3.3 clean_pair filter  : {len(d):,}   ({_n0 - len(d):,} borrowed-report EEGs dropped)")
    print(f"Q_SLOWING coverage               : {int(d.Q_SLOWING.notna().sum()):,}"
          f"   (was 3,130 in the committed results)")
    print(f"Morgoth p_slowing coverage       : {int(d.p_slowing_p90.notna().sum()):,}\n")

    # age-conditioned deviation FIRST (reference = clean-normal), so the slices below carry the _z cols
    METRICS = ["DAR", "TAR", "DTABR", "ADR", "SEF95", "median_freq"] + QCOLS + ["p_slowing_p90"]
    ref = d[d.clean_normal == True]                                      # noqa: E712
    for c in METRICS:
        if c not in d.columns:
            continue
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
        return (auc_ci(y_ab, ab[col], rng, groups=ab.patient_id.values),
                auc_ci(y_g,  gen[col], rng, groups=gen.patient_id.values),
                auc_ci(y_f,  foc[col], rng, groups=foc.patient_id.values))

    specs = [
        # --- raw, as published ---
        ("Q_SLOWING (raw) [vP2013 k=.76]", "Q_SLOWING"), ("DAR (raw)", "DAR"),
        ("DTABR (raw)", "DTABR"), ("SEF95 (raw)", "SEF95"), ("median_freq (raw)", "median_freq"),
        ("r_sBSI (raw)", "r_sBSI"), ("Q_APG (raw)", "Q_APG"), ("Q_ASYM (raw)", "Q_ASYM"),
        # --- age-conditioned deviation (our normative framing applied to HIS metrics) ---
        ("Q_SLOWING (age-normed)", "Q_SLOWING_z"), ("DAR (age-normed)", "DAR_z"),
        ("DTABR (age-normed)", "DTABR_z"), ("SEF95 (age-normed)", "SEF95_z"),
        ("r_sBSI (age-normed)", "r_sBSI_z"), ("Q_ASYM (age-normed)", "Q_ASYM_z"),
        # --- ours ---
        ("** Morgoth p_slowing (gate) **", "p_slowing_p90"),
    ]
    out = []; arms = {}
    for name, col in specs:
        if col not in d.columns:
            continue
        A, G, F = arm(col); arms[name] = (A, G, F)
        out.append({"method": name,
                    "abnormal": f"{A[0]} [{A[1]}–{A[2]}]", "generalized": f"{G[0]} [{G[1]}–{G[2]}]",
                    "focal": f"{F[0]} [{F[1]}–{F[2]}]", "n_scored": A[3]})
    tab = pd.DataFrame(out)
    make_figure(arms)
    print(tab.to_string(index=False))
    Path("results").mkdir(exist_ok=True)
    n_ab = len(norm) + len(pos)
    Path("results/vanputten_fullcoverage.md").write_text(
        "# van Putten benchmark (SAP §8.7, Table 6) — FULL fleet coverage\n\n"
        f"All arms recomputed on the SAP §3.3 **clean_pair** set (feature coverage "
        f"{int(d.DAR.notna().sum()):,} recordings for the segment_master metrics [DAR/DTABR/SEF95/median_freq] "
        f"and {int(d.Q_SLOWING.notna().sum()):,} for the whole-head metrics + the Morgoth gate [Q_*/p_slowing]). "
        f"Each AUROC is scored on its own contrast — clean-normal vs the relevant positive class — so the "
        f"benchmark denominator is the **n_scored** column (**{n_ab:,}** for the any-abnormal contrast: "
        f"{len(norm):,} clean-normal vs {len(pos):,} slowing-positive), NOT the raw feature-coverage count.\n\n"
        "> The previously committed `vanputten_comparison.md` used only **3,130** recordings for the "
        "whole-head/gate arms and **14,450** for the rest — an incomplete `segment_summary` DOWNLOAD on the "
        "analysis box, not a fleet gap (S3 holds all 27,478; segment_master and segment_summary partition "
        "counts match exactly). This table supersedes it.\n\n"
        "Labels are the CORRECTED SAP labels (`label_rederive_sap.py`: physiologic generalized slowing is "
        "NOT a positive — 5,528 recordings were previously mislabelled pathologic). "
        "AUROC [95% CI from a PATIENT-CLUSTERED bootstrap — patients resampled with replacement, all of "
        "their recordings carried along, per SAP §3.3]; auto-oriented so >0.5.\n\n" + tab.to_markdown(index=False) + "\n")
    print("\nwrote results/vanputten_fullcoverage.md")


if __name__ == "__main__":
    main()
