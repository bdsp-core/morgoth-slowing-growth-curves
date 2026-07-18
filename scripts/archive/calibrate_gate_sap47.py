#!/usr/bin/env python3
"""SAP §4.7 — calibrate the Morgoth gate probability. REQUIRED before any operating-point claim.

The raw softmax `p_slowing` is uncalibrated (neural nets are systematically overconfident). The SAP
requires: "fit a calibration map (Platt / isotonic) for p_slowing against the labels on held-out data,
and store the calibrated probability alongside the raw one. This is required before any operating-point
(§7.1) or detection-AUROC claim uses the gate probability as a score."

NOTE on scope, stated plainly: calibration is a MONOTONIC map, so it cannot change AUROC — the Table 6
benchmark (0.881/0.918/0.875) is rank-based and therefore unaffected. What calibration changes is whether
the probability MEANS anything (Brier / ECE / reliability) and where a threshold should sit. That is what
P7 (balanced accuracy vs the human ceiling) and §7.1 operating points depend on.

Cross-fitted by PATIENT (SAP §3.3/§6.3) so no recording informs its own calibration map.

Run: PYTHONPATH=src python scripts/calibrate_gate_sap47.py
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, brier_score_loss

SS = "data/derived/segment_summary"
LAB = "data/derived/recording_labels_sap.parquet"
OUT = Path("data/derived/gate_calibrated.parquet")


def ece(y, p, bins=10):
    """Expected calibration error."""
    edges = np.linspace(0, 1, bins + 1)
    e, n = 0.0, len(y)
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= 1)
        if m.sum() == 0:
            continue
        e += (m.sum() / n) * abs(y[m].mean() - p[m].mean())
    return e


def main():
    rows = []
    for f in glob.glob(f"{SS}/eeg_id=*/part.parquet"):
        eid = f.split("eeg_id=")[1].split("/")[0]
        s = pd.read_parquet(f, columns=["artifact_flag", "p_slowing"])
        s = s[~s.artifact_flag]
        if s.empty or s.p_slowing.isna().all():
            continue
        rows.append({"eeg_id": eid, "p_slowing_p90": float(np.nanpercentile(s.p_slowing, 90))})
    g = pd.DataFrame(rows)
    lab = pd.read_parquet(LAB).drop_duplicates("eeg_id")
    d = g.merge(lab[["eeg_id", "patient_id", "clean_normal", "slowing_positive"]], on="eeg_id")
    d = d[d.clean_normal | d.slowing_positive].copy()
    d["y"] = d.slowing_positive.astype(int)
    print(f"calibration set: {len(d):,} recordings ({int(d.y.sum()):,} slowing-positive, "
          f"{int((1 - d.y).sum()):,} clean-normal) over {d.patient_id.nunique():,} patients")

    X = d[["p_slowing_p90"]].values
    y = d.y.values
    groups = d.patient_id.values
    d["p_platt"] = np.nan
    d["p_isotonic"] = np.nan
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):          # patient-split: no leakage
        lr = LogisticRegression().fit(X[tr], y[tr])
        d.iloc[te, d.columns.get_loc("p_platt")] = lr.predict_proba(X[te])[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip").fit(X[tr].ravel(), y[tr])
        d.iloc[te, d.columns.get_loc("p_isotonic")] = iso.predict(X[te].ravel())

    print("\n                   AUROC    Brier      ECE   (AUROC is rank-based: calibration cannot change it)")
    for name, col in [("raw p_slowing", "p_slowing_p90"), ("Platt", "p_platt"), ("isotonic", "p_isotonic")]:
        p = d[col].values
        print(f"  {name:16} {roc_auc_score(y, p):.3f}  {brier_score_loss(y, p):.4f}  {ece(y, p):.4f}")

    d[["eeg_id", "patient_id", "p_slowing_p90", "p_platt", "p_isotonic", "y"]].to_parquet(OUT, index=False)
    raw_b, iso_b = brier_score_loss(y, d.p_slowing_p90), brier_score_loss(y, d.p_isotonic)
    Path("results").mkdir(exist_ok=True)
    Path("results/gate_calibration.md").write_text(
        "# Morgoth gate calibration (SAP §4.7)\n\n"
        f"Cross-fitted by patient (5-fold GroupKFold) on {len(d):,} recordings "
        f"({int(d.y.sum()):,} slowing-positive / {int((1-d.y).sum()):,} clean-normal), corrected SAP labels.\n\n"
        "| map | AUROC | Brier | ECE |\n|---|---|---|---|\n"
        + "".join(f"| {n} | {roc_auc_score(y, d[c]):.3f} | {brier_score_loss(y, d[c]):.4f} | {ece(y, d[c].values):.4f} |\n"
                 for n, c in [("raw p_slowing", "p_slowing_p90"), ("Platt", "p_platt"), ("isotonic", "p_isotonic")])
        + f"\n**AUROC is identical across maps by construction** — calibration is monotonic, so it cannot "
          f"change ranking. The Table 6 benchmark is therefore unaffected. What improves is the *meaning* "
          f"of the probability: Brier {raw_b:.4f} → {iso_b:.4f} and the reliability curve. Operating-point "
          f"claims (§7.1) and P7 must use the calibrated column (`p_isotonic`), stored alongside the raw "
          f"one in `data/derived/gate_calibrated.parquet`.\n")
    print(f"\nwrote {OUT} + results/gate_calibration.md")


if __name__ == "__main__":
    main()
