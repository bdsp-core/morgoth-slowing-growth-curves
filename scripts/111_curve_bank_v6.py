#!/usr/bin/env python3
"""Regenerate the supplementary curve bank — figures/curves/ and figures/stage_curves/ — on v6.

The manuscript says "Curves for all 8 features x 5 regions are provided in `figures/curves/`". That
directory held 41 PNGs, every one of them produced by an ARCHIVED script from the legacy tables: pre
label-fix, pre age-fix. Only the one figure the manuscript inlines (log_delta whole_head) had been
regenerated. A reader opening the directory got the old curves.

This rebuilds the whole bank from the v6 canonical tables with the authoritative ages:
  figures/curves/<feature>__<region>.png        normative curve, clean-normals vs slowing-positive (wake)
  figures/stage_curves/<feature>__whole_head.png  the same feature per sleep stage, clean-normals

BSI is dropped: it is an interhemispheric asymmetry index, not a per-region band feature, and it is not in
channel_stage_features. It is covered by Table 6 (r_sBSI / Q_ASYM) instead.

Run: PYTHONPATH=src MPLBACKEND=Agg python scripts/111_curve_bank_v6.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FEATURES = ["log_delta", "log_theta", "rel_delta", "rel_theta", "DAR", "TAR", "DTR", "low_freq_rel"]
REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
GRID = np.arange(0.25, 90, 0.5)
C_NORM, C_ABN = "#2c7fb8", "#d95f02"
XT = [0.25, 0.5, 1, 2, 5, 10, 20, 40, 60, 90]
XL = ["3 mo", "6 mo", "1", "2", "5", "10", "20", "40", "60", "90"]


def smooth_q(age, val, qs=(0.5,), bw=6.0):
    a, v = np.asarray(age, float), np.asarray(val, float)
    ok = np.isfinite(a) & np.isfinite(v); a, v = a[ok], v[ok]
    out = {q: np.full(len(GRID), np.nan) for q in qs}
    for j, g in enumerate(GRID):
        w = np.exp(-0.5 * ((a - g) / bw) ** 2)
        m = w > 1e-4
        if m.sum() < 25:
            continue
        aw, vw = w[m], v[m]
        o = np.argsort(vw); vw, aw = vw[o], aw[o]
        c = np.cumsum(aw) / aw.sum()
        for q in qs:
            out[q][j] = np.interp(q, c, vw)
    return out


def axfmt(ax, xlab="Age (years, log scale)"):
    ax.set_xscale("log"); ax.set_xticks(XT); ax.set_xticklabels(XL); ax.set_xlim(0.15, 90)
    ax.set_xlabel(xlab); ax.grid(alpha=.25)


def main():
    Path("figures/curves").mkdir(parents=True, exist_ok=True)
    Path("figures/stage_curves").mkdir(parents=True, exist_ok=True)

    csf = pd.read_parquet("data/derived/channel_stage_features.parquet")
    csf = csf[csf.region.isin(REGIONS)].copy()
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    lab = lab[["eeg_id", "age", "clean_normal", "slowing_positive", "clean_pair"]]
    d = csf.drop(columns=[c for c in ("age", "clean_normal", "clean_pair", "is_abnormal", "patient_id",
                                      "sex") if c in csf.columns])
    d = d.merge(lab, left_on="bdsp_id", right_on="eeg_id", how="inner")
    d = d[(d.clean_pair == True) & d.age.notna()]                       # noqa: E712
    print(f"rows: {len(d):,}  recordings: {d.eeg_id.nunique():,}  (clean_pair, exact ages)")

    n = 0
    wake = d[d.stage == "W"]
    for feat in FEATURES:
        if feat not in d.columns:
            print(f"  skip {feat} (not in channel_stage_features)")
            continue
        for reg in REGIONS:
            s = wake[wake.region == reg]
            nrm = s[s.clean_normal == True]                              # noqa: E712
            abn = s[s.slowing_positive == True]                          # noqa: E712
            if len(nrm) < 200:
                continue
            qn = smooth_q(nrm.age, nrm[feat], qs=(0.1, 0.5, 0.9))
            qa = smooth_q(abn.age, abn[feat], qs=(0.5,)) if len(abn) > 200 else None
            fig, ax = plt.subplots(figsize=(7.5, 4.8))
            ax.scatter(nrm.age, nrm[feat], s=2, alpha=.08, color=C_NORM, lw=0, rasterized=True)
            ax.fill_between(GRID, qn[0.1], qn[0.9], color=C_NORM, alpha=.22, lw=0,
                            label="clean-normal 10–90th pct")
            ax.plot(GRID, qn[0.5], color=C_NORM, lw=2.3, label=f"clean-normal median (n={len(nrm):,})")
            if qa is not None:
                ax.plot(GRID, qa[0.5], color=C_ABN, lw=2.3, ls="--",
                        label=f"slowing-positive median (n={len(abn):,})")
            axfmt(ax)
            ax.set_ylabel(f"{feat}  ({reg})")
            ax.set_title(f"{feat} — {reg}, wake (v6: corrected labels + exact ages)", fontsize=10)
            ax.legend(frameon=False, fontsize=7)
            fig.tight_layout()
            fig.savefig(f"figures/curves/{feat}__{reg}.png", dpi=140)
            plt.close(fig)
            n += 1

        # stage-resolved variant, whole head
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        drew = False
        for st, col in zip(STAGES, ["#4575b4", "#91bfdb", "#fdae61", "#d73027", "#7b3294"]):
            s = d[(d.stage == st) & (d.region == "whole_head") & (d.clean_normal == True)]   # noqa: E712
            if len(s) < 200:
                continue
            q = smooth_q(s.age, s[feat], qs=(0.5,))
            ax.plot(GRID, q[0.5], color=col, lw=2.2, label=f"{st} (n={len(s):,})")
            drew = True
        if drew:
            axfmt(ax)
            ax.set_ylabel(f"{feat}  (whole head)")
            ax.set_title(f"{feat} by sleep stage — clean-normals (v6)", fontsize=10)
            ax.legend(frameon=False, fontsize=8, title="stage")
            fig.tight_layout()
            fig.savefig(f"figures/stage_curves/{feat}__whole_head.png", dpi=140)
            n += 1
        plt.close(fig)

    # retire the legacy BSI curves rather than leave stale images in a directory the manuscript cites
    for p in [Path("figures/curves/BSI__whole_head.png"), Path("figures/stage_curves/BSI__whole_head.png")]:
        if p.exists():
            p.unlink()
            print(f"  removed stale {p} (BSI is an asymmetry index, not a band feature; see Table 6)")

    print(f"\nwrote {n} curve figures across figures/curves/ + figures/stage_curves/ (all v6)")


if __name__ == "__main__":
    main()
