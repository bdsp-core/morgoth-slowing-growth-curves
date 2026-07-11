"""Add Brain Symmetry Index (BSI) as one of OUR features, with age growth curves (overall + per stage).

BSI (van Putten) = mean over homologous channel pairs & bands of |R-L|/(R+L). We compute it per recording
(overall) and per (recording, sleep stage), build normal percentile growth curves vs age, and save the
feature so it can be deviation-scored like the others. Figures named to match the dashboard convention.

Overall BSI: from recording_features per-channel band powers.
Per-stage BSI: from segment_features (per-channel, per-segment) joined to segment_stages, averaged to
(recording, stage, channel) then BSI — normals are staged, which is what the growth curve needs.

Writes data/derived/bsi_features.parquet, figures/curves/BSI__whole_head.png,
figures/stage_curves/BSI__whole_head.png.
Run: PYTHONPATH=src python scripts/48_bsi_growth.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

PAIRS = [("Fp1-F3", "Fp2-F4"), ("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"),
         ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("T5-O1", "T6-O2"), ("P3-O1", "P4-O2")]
BANDS = ["delta", "theta", "alpha", "beta"]
CHS = sorted(set(c for p in PAIRS for c in p))
AGE_BINS = list(range(0, 96, 5))


def bsi_from_powers(pw):
    """pw: DataFrame indexed by bdsp_id with columns (channel, band) of band power -> Series BSI."""
    contribs = []
    for L, R in PAIRS:
        for b in BANDS:
            if (L, b) in pw and (R, b) in pw:
                contribs.append(np.abs(pw[(R, b)] - pw[(L, b)]) / (pw[(R, b)] + pw[(L, b)] + 1e-12))
    return pd.concat(contribs, axis=1).mean(axis=1)


def pct_curve(ax, age, val, label, color):
    df = pd.DataFrame({"age": pd.to_numeric(age, errors="coerce"), "v": val}).dropna()
    df = df[(df.age >= 0) & (df.age <= 95)]
    df["ab"] = pd.cut(df.age, AGE_BINS)
    g = df.groupby("ab", observed=True).v
    mid = [iv.mid for iv in g.median().index]
    ax.plot(mid, g.median().values, color=color, lw=2, label=label)
    ax.fill_between(mid, g.quantile(.1).values, g.quantile(.9).values, color=color, alpha=0.12)


def main():
    rf = pd.read_parquet("data/derived/recording_features.parquet")
    LB = [f"log_{b}" for b in BANDS]
    meta = rf.groupby("bdsp_id").agg(age=("age", "first"), label=("label", "first"))
    # overall BSI per recording
    pw = {}
    for ch in CHS:
        r = rf[rf.region == ch].groupby("bdsp_id")[LB].mean()
        for b in BANDS:
            pw[(ch, b)] = np.exp(r[f"log_{b}"])
    bsi = bsi_from_powers(pd.DataFrame(pw)).rename("bsi")
    rec = meta.join(bsi, how="inner")
    # age-normalized deviation vs CLEAN normals (robust z: IQR/1.349), same convention as other
    # deviation features; consumed by 47 (van Putten BSI-deviation row) and 16 (gated report).
    bins = np.arange(0, 96, 5)
    nm = rec[rec.label == "normal"].copy(); nm["ab"] = pd.cut(nm.age, bins)
    st = nm.groupby("ab", observed=True).bsi.agg(
        med="median", sig=lambda x: max((x.quantile(.75) - x.quantile(.25)) / 1.349, 1e-6))
    rec["ab"] = pd.cut(rec.age, bins)
    rec = rec.join(st, on="ab")
    rec["bsi_z"] = (rec.bsi - rec["med"]) / rec["sig"]
    rec = rec.drop(columns=["ab", "med", "sig"])
    rec.reset_index().to_parquet("data/derived/bsi_features.parquet")   # bdsp_id as COLUMN + bsi + bsi_z
    print(f"overall BSI: {len(rec)} recordings; normal median {rec[rec.label=='normal'].bsi.median():.3f}, "
          f"focal {rec[rec.label=='focal_slow'].bsi.median():.3f}")

    # overall growth curve (normals)
    nb = rec[rec.label == "normal"]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    pct_curve(ax, nb.age, nb.bsi, "normal BSI (median, 10-90%)", "#4a90e2")
    ax.set_xlabel("age (years)"); ax.set_ylabel("BSI"); ax.set_title("Brain Symmetry Index vs age (normal)")
    ax.legend(); ax.grid(alpha=0.25)
    Path("figures/curves").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("figures/curves/BSI__whole_head.png", dpi=130); plt.close(fig)

    # per-stage BSI (normals staged): computed from the pre-aggregated (recording, region, stage) table
    # using the homologous L/R AGGREGATE-region pairs (temporal, parasagittal) — no per-channel segment
    # table needed. Regional BSI (coarser than the 8-pair channel BSI but per-stage and label-clean).
    AGG_PAIRS = [("L_temporal", "R_temporal"), ("L_parasagittal", "R_parasagittal")]
    srf = pd.read_parquet("data/derived/stage_recording_features.parquet")
    def stage_bsi(sub):
        """sub: rows for one stage; return Series BSI per bdsp_id from L/R aggregate pairs & bands."""
        wide = sub.pivot_table(index="bdsp_id", columns="region", values=LB)  # cols: (log_band, region)
        contribs = []
        for L, R in AGG_PAIRS:
            for lb in LB:
                if (lb, L) in wide and (lb, R) in wide:
                    pl, pr = np.exp(wide[(lb, L)]), np.exp(wide[(lb, R)])
                    contribs.append((np.abs(pr - pl) / (pr + pl + 1e-12)))
        return pd.concat(contribs, axis=1).mean(axis=1) if contribs else pd.Series(dtype=float)
    lab_by_id = srf.groupby("bdsp_id").label.first(); age_by_id = srf.groupby("bdsp_id").age.first()
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    colors = {"W": "#f5a623", "N2": "#4a90e2", "N3": "#2ec4b6", "REM": "#e0568a"}
    for stage, color in colors.items():
        b = stage_bsi(srf[srf.stage == stage])
        if b.empty:
            continue
        nmask = lab_by_id.reindex(b.index) == "normal"
        pct_curve(ax, age_by_id.reindex(b.index)[nmask.values], b[nmask.values], stage, color)
    ax.set_xlabel("age (years)"); ax.set_ylabel("BSI (normal)")
    ax.set_title("BSI vs age by sleep stage (normal)"); ax.legend(title="stage"); ax.grid(alpha=0.25)
    Path("figures/stage_curves").mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig("figures/stage_curves/BSI__whole_head.png", dpi=130); plt.close(fig)
    print("wrote figures/curves/BSI__whole_head.png + figures/stage_curves/BSI__whole_head.png")


if __name__ == "__main__":
    main()
