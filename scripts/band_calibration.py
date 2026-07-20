"""Band (delta / theta / mixed) calibration — how well can the generated band word agree with the report's
band word, without over-fitting report noise?

Band AXIS = ABSOLUTE delta/theta power dominance (whole-head mean log(δ/θ), the "band_dtr" descriptor), NOT the
per-band deviation z. A clinician's "delta slowing" means delta POWER dominates the trace; the age/stage z does
not track that (normal delta σ is large, so a big delta in a young brain sits at a modest z, and a smaller theta
excess can win the deviation axis while delta plainly dominates the trace). Empirically the raw ratio predicts the
report's delta-vs-theta band at AUROC ~0.72, vs ~0.66 for the old deviation axis (z_theta − z_delta).

Finding: the report band is dominated by "mixed" (~64%), a reader HEDGE that is statistically inseparable from
theta and barely from delta; the only real signal is the delta-vs-theta axis. Maximising 3-way ACCURACY collapses
to "always mixed". The honest calibration is MARGINAL-MATCHING: default to "mixed" and assert a pure band only when
the dominance ratio clears a threshold set to reproduce the report's own delta/theta rates. That lands at Cohen's
kappa near the low end of published expert-vs-expert band agreement (0.09-0.38) — i.e. at the human noise floor,
which is the correct stopping point.

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
    d = d.dropna(subset=["rep", "band_dtr"]).copy()
    d["dtr"] = d.band_dtr                                         # whole-head mean log(delta/theta); HIGH = delta-dominant
    return d


def thresholds(dtr, p_delta, p_theta):
    """Marginal-matched: top p_delta of dtr -> delta, bottom p_theta -> theta, else mixed."""
    return float(np.quantile(dtr, p_theta)), float(np.quantile(dtr, 1 - p_delta))   # (LO=theta cut, HI=delta cut)


def call(dtr, lo, hi):
    return np.where(dtr > hi, "delta", np.where(dtr < lo, "theta", "mixed"))


def auc_dvt(df, score):
    """delta-vs-theta discrimination, orientation-free (max(a, 1-a)); the deviation axis runs the opposite
    direction to log(δ/θ), so report the separability, not the sign."""
    sub = df[df.rep.isin(["delta", "theta"])].dropna(subset=[score])
    y = (sub.rep == "delta").astype(int)
    if y.nunique() != 2:
        return np.nan
    a = roc_auc_score(y, sub[score])
    return max(a, 1 - a)


def main():
    d = load()
    d["dev"] = d.theta_p90 - d.delta_p90                         # OLD deviation axis (z_theta − z_delta), for comparison
    pats = d.patient_id.dropna().unique(); rng = np.random.RandomState(0); rng.shuffle(pats)
    trp = set(pats[:len(pats) // 2]); tr, te = d[d.patient_id.isin(trp)], d[~d.patient_id.isin(trp)]
    p_d, p_t = (tr.rep == "delta").mean(), (tr.rep == "theta").mean()
    lo, hi = thresholds(tr.dtr.values, p_d, p_t)                 # fit on train (absolute log(δ/θ) dominance)
    pte = call(te.dtr.values, lo, hi)
    acc = (pte == te.rep.values).mean(); bacc = balanced_accuracy_score(te.rep, pte); k = cohen_kappa_score(te.rep, pte)
    always_mixed = (te.rep == "mixed").mean()
    # headline: does the absolute-dominance axis beat the deviation axis at the reports' delta-vs-theta band?
    auc_new = auc_dvt(te, "dtr"); auc_old = auc_dvt(te, "dev")
    aucs = {}
    for a, b in [("delta", "theta"), ("delta", "mixed"), ("theta", "mixed")]:
        sub = te[te.rep.isin([a, b])]; y = (sub.rep == a).astype(int)
        av = roc_auc_score(y, sub.dtr) if y.nunique() == 2 else np.nan
        aucs[f"{a}-vs-{b}"] = max(av, 1 - av) if np.isfinite(av) else np.nan   # separability (orientation-free)
    # production thresholds: refit on the FULL band-labelled set (what scripts/58 hard-codes)
    LO, HI = thresholds(d.dtr.values, (d.rep == "delta").mean(), (d.rep == "theta").mean())

    md = ["# Band (delta / theta / mixed) calibration — agree with reports without over-fitting the hedge\n",
          f"Clean-paired report-band-labelled recordings: **N={len(d):,}** "
          f"(report marginals mixed {(d.rep=='mixed').mean():.2f} · delta {(d.rep=='delta').mean():.2f} · "
          f"theta {(d.rep=='theta').mean():.2f}). Band axis = **whole-head mean log(δ/θ) power** (`band_dtr`; "
          f"high = delta-dominant). Patient-split 50/50; thresholds set on train to reproduce the report's "
          f"delta/theta rates.\n",
          "**Why the absolute-power axis, not the deviation z.** A clinician's *delta slowing* means delta power "
          "dominates the trace. The per-band age/stage deviation z does not track that — normal delta σ is large, "
          "so a big delta in a young brain sits at a modest z while a smaller theta excess wins the deviation axis "
          "even though delta plainly dominates the trace. On the held-out reports the raw ratio separates "
          f"delta-vs-theta at **AUROC {auc_new:.2f}**, vs **{auc_old:.2f}** for the old deviation axis "
          f"(z_theta − z_delta) — a {auc_new-auc_old:+.2f} gain, and it matches what a reader sees.\n",
          "| method | 3-way acc | balanced acc | Cohen κ | predicted mixed/delta/theta |",
          "|---|---|---|---|---|",
          f"| **marginal-matched on log(δ/θ) (production)** | **{acc:.3f}** | {bacc:.3f} | **{k:.3f}** | "
          f"{(pte=='mixed').mean():.2f} / {(pte=='delta').mean():.2f} / {(pte=='theta').mean():.2f} |",
          f"| trivial 'always mixed' | {always_mixed:.3f} | 0.333 | 0.000 | 1.00 / 0 / 0 |",
          "\n**Where the signal is (test AUROC, separability):** "
          + " · ".join(f"{k2} {v:.2f}" for k2, v in aucs.items()) +
          ". The **delta-vs-theta axis carries the real signal**; 'mixed' is a reader hedge that sits between the "
          "two pure bands and is only weakly separated from either, so we do not chase a 3-way hard call.\n",
          f"**Expert ceiling.** Published expert-vs-expert band κ is **0.09–0.38**; the calibrated model's "
          f"κ={k:.2f} sits at the low end — i.e. it agrees with reports about as well as reports agree with each "
          f"other. This is the correct stopping point: matching the *distribution* and surfacing the delta↔theta "
          f"axis, without pretending the 3-way hard call is more than a low-confidence gloss (the valid test is "
          f"the continuous D1 dose-response).\n",
          f"**Production thresholds (scripts/58 `band_word`, refit on all N={len(d):,}):** "
          f"LO = {LO:.2f}, HI = {HI:.2f} on `band_dtr` = mean log(δ/θ):  dtr > HI → delta, dtr < LO → theta, "
          f"else mixed.\n"]
    RES.mkdir(parents=True, exist_ok=True); (RES / "band_calibration.md").write_text("\n".join(md))
    print("\n".join(md)); print(f"\nHARD-CODE IN scripts/58: BAND_LO={LO:.3f}, BAND_HI={HI:.3f}")


if __name__ == "__main__":
    main()
