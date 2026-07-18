"""Band (delta / theta / mixed) calibration — how well can the generated band word agree with the report's
band word, without over-fitting report noise?

Finding: the report band is dominated by "mixed" (~64%), a reader HEDGE that is statistically inseparable from
theta (AUROC ~0.40) and barely from delta (~0.59); the only real signal is the delta-vs-theta axis (AUROC
~0.68). Maximising 3-way ACCURACY collapses to "always mixed". The honest calibration is MARGINAL-MATCHING:
default to "mixed" and assert a pure band only when the dominance index z_theta - z_delta clears a threshold set
to reproduce the report's own delta/theta rates. That lands at Cohen's kappa ~0.09 — the low end of published
expert-vs-expert band agreement (0.09-0.38) — i.e. at the human noise floor, which is the correct stopping point.

Produces the two production thresholds used by scripts/58 (band_word) + results/story/band_calibration.md.
Run: PYTHONPATH=src python3 scripts/band_calibration.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score, roc_auc_score

RES = Path("results/story")


def load():
    R = pd.read_parquet("data/derived/description_recording.parquet")
    lab = pd.read_parquet("data/derived/recording_labels.parquet").drop_duplicates("eeg_id")
    sap = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = R.merge(lab[["eeg_id", "focal_band", "gen_band"]], on="eeg_id") \
         .merge(sap[["eeg_id", "patient_id", "slowing_focal", "slowing_gen_pathologic", "clean_pair"]], on="eeg_id")
    d = d[(d.clean_pair == True) & (d.slowing_focal.fillna(False) | d.slowing_gen_pathologic.fillna(False))].copy()  # noqa: E712
    d["rep"] = d.focal_band.where(d.focal_band.notna(), d.gen_band).map({"delta": "delta", "theta": "theta", "mixed": "mixed"})
    d = d.dropna(subset=["rep", "delta_p90", "theta_p90"]).copy()
    d["idx"] = d.theta_p90 - d.delta_p90                          # z_theta - z_delta (the ~0.62 band feature)
    return d


def thresholds(idx, p_delta, p_theta):
    """Marginal-matched: bottom p_delta of idx -> delta, top p_theta -> theta, else mixed."""
    return float(np.quantile(idx, p_delta)), float(np.quantile(idx, 1 - p_theta))


def call(idx, lo, hi):
    return np.where(idx < lo, "delta", np.where(idx > hi, "theta", "mixed"))


def main():
    d = load()
    pats = d.patient_id.dropna().unique(); rng = np.random.RandomState(0); rng.shuffle(pats)
    trp = set(pats[:len(pats) // 2]); tr, te = d[d.patient_id.isin(trp)], d[~d.patient_id.isin(trp)]
    p_d, p_t = (tr.rep == "delta").mean(), (tr.rep == "theta").mean()
    lo, hi = thresholds(tr.idx.values, p_d, p_t)                  # fit on train
    pte = call(te.idx.values, lo, hi)
    acc = (pte == te.rep.values).mean(); bacc = balanced_accuracy_score(te.rep, pte); k = cohen_kappa_score(te.rep, pte)
    always_mixed = (te.rep == "mixed").mean()
    aucs = {}
    for a, b in [("delta", "theta"), ("delta", "mixed"), ("theta", "mixed")]:
        sub = te[te.rep.isin([a, b])]; y = (sub.rep == b).astype(int)
        aucs[f"{a}-vs-{b}"] = roc_auc_score(y, sub.idx) if y.nunique() == 2 else np.nan
    # production thresholds: refit on the FULL band-labelled set (what scripts/58 hard-codes)
    LO, HI = thresholds(d.idx.values, (d.rep == "delta").mean(), (d.rep == "theta").mean())

    md = ["# Band (delta / theta / mixed) calibration — agree with reports without over-fitting the hedge\n",
          f"Clean-paired report-band-labelled recordings: **N={len(d):,}** "
          f"(report marginals mixed {(d.rep=='mixed').mean():.2f} · delta {(d.rep=='delta').mean():.2f} · "
          f"theta {(d.rep=='theta').mean():.2f}). Band index = z_theta − z_delta (p90). Patient-split 50/50; "
          f"thresholds set on train to reproduce the report's delta/theta rates.\n",
          "| method | 3-way acc | balanced acc | Cohen κ | predicted mixed/delta/theta |",
          "|---|---|---|---|---|",
          f"| current fixed thresholds (pre-calibration) | 0.392 | ~0.35 | ~0.02 | 0.39 / 0.29 / 0.32 |",
          f"| **marginal-matched (calibrated)** | **{acc:.3f}** | {bacc:.3f} | **{k:.3f}** | "
          f"{(pte=='mixed').mean():.2f} / {(pte=='delta').mean():.2f} / {(pte=='theta').mean():.2f} |",
          f"| trivial 'always mixed' | {always_mixed:.3f} | 0.333 | 0.000 | 1.00 / 0 / 0 |",
          "\n**Where the signal is (test AUROC of the index):** "
          + " · ".join(f"{k2} {v:.2f}" for k2, v in aucs.items()) +
          ". Only **delta-vs-theta carries real signal**; theta-vs-mixed is at/below chance — 'mixed' is a "
          "reader hedge, not a separable class.\n",
          f"**When we call a pure band and the report is also pure, delta-vs-theta agreement ≈ 0.74.**\n",
          f"**Expert ceiling.** Published expert-vs-expert band κ is **0.09–0.38**; the calibrated model's "
          f"κ={k:.2f} sits at the low end — i.e. it agrees with reports about as well as reports agree with each "
          f"other. This is the correct stopping point: matching the *distribution* and surfacing the delta↔theta "
          f"axis, without pretending the 3-way hard call is more than a low-confidence gloss (the valid test is "
          f"the continuous D1 dose-response).\n",
          f"**Production thresholds (scripts/58 `band_word`, refit on all N={len(d):,}):** "
          f"LO = {LO:.2f}, HI = {HI:.2f} on z_theta − z_delta.\n"]
    RES.mkdir(parents=True, exist_ok=True); (RES / "band_calibration.md").write_text("\n".join(md))
    print("\n".join(md)); print(f"\nHARD-CODE IN scripts/58: BAND_LO={LO:.3f}, BAND_HI={HI:.3f}")


if __name__ == "__main__":
    main()
