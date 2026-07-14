#!/usr/bin/env python3
"""Figure 4 / Table 2, rebuilt as the TWO-STAGE SYSTEM actually works.

WHAT WAS WRONG WITH THE OLD FIGURE. It reported our normative deviation score as a STANDALONE DETECTOR —
AUROC for deviation-vs-report-label, per stage. But we never intend to use the deviation that way. The
deviation is the QUANTIFIER; Morgoth is the DETECTOR. We only ever describe slowing in recordings where
Morgoth says there IS slowing. Measuring the quantifier as if it were the detector answers a question we
do not ask, and it made the deviation look weak (~0.72) next to the gate (~0.88) for no useful reason.

WHAT THIS FIGURE SHOWS INSTEAD. Group recordings by MORGOTH's call — no slowing / focal / generalized —
and, within each sleep stage, show the distribution of normative deviation from normal. Triplet of boxes
per stage. This is the deployed pipeline: the gate decides whether and what, the deviation says how much,
and because every segment is scored against ITS OWN STAGE's normal curve, the quantity stays interpretable
in N2/N3 where raw delta is uninformative.

HONEST LIMIT — READ THIS.
Morgoth's SLOWING head is a 3-class *per-window* head: {0: Others, 1: Focal Slowing, 2: Generalized
Slowing} (morgoth2/results_figures.py:2790). So per-SEGMENT focal and generalized probabilities DO exist.
Our fleet worker did not keep them: scripts/31_segment_master_worker.py:162 collapses the window head to
`p_slowing = 1 - class_0_prob` and throws class_1_prob / class_2_prob away. The focal/generalized split we
persisted comes from the SEPARATE EEG-level heads (FOC_SLOWING_EEGlevel / GEN_SLOWING_EEGlevel), which emit
ONE probability per recording.

So the gating here is PER-RECORDING, not per-segment. Recovering per-segment focal/generalized requires
re-running Morgoth's SLOWING window head over the fleet and persisting all three class probabilities.
Nothing on disk can substitute for it. This figure is the best faithful version available today, and the
limitation is stated on the figure itself rather than hidden.

Run: PYTHONPATH=src MPLBACKEND=Agg python scripts/112_gated_deviation_by_stage.py
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve

STAGES = ["W", "N1", "N2", "N3", "REM"]
SLOW_FEATS = ["log_delta", "TAR", "DAR"]          # higher = more slowing
GROUPS = ["Morgoth: no slowing", "Morgoth: focal", "Morgoth: generalized"]
COLORS = ["#8fa6bd", "#f0a259", "#c8443c"]


def fit_norm(age, val, bw=8.0, grid=np.arange(0, 91, 0.5)):
    ok = np.isfinite(age) & np.isfinite(val)
    a, v = np.asarray(age)[ok], np.asarray(val)[ok]
    if len(a) < 30:
        return None
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((a - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * v).sum() / sw
        mu[j] = m
        sd[j] = np.sqrt(max((w * (v - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (grid[good], mu[good], sd[good]) if good.sum() >= 10 else None


def z_of(nrm, age, val):
    if nrm is None:
        return np.full(len(np.atleast_1d(val)), np.nan)
    g, mu, sd = nrm
    return (np.asarray(val, float) - np.interp(age, g, mu)) / np.interp(age, g, sd)


def youden(y, s):
    fpr, tpr, thr = roc_curve(y, s)
    return float(thr[int(np.argmax(tpr - fpr))])


def main():
    csf = pd.read_parquet("data/derived/channel_stage_features.parquet")
    csf = csf[csf.region == "whole_head"].copy()
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    lab = lab[["eeg_id", "patient_id", "age", "clean_normal", "clean_pair",
               "slowing_focal", "slowing_gen_pathologic"]]
    gate = pd.read_parquet("data/derived/gate_eeg_level.parquet").drop_duplicates("eeg_id")

    d = csf.drop(columns=[c for c in ("age", "clean_normal", "clean_pair", "is_abnormal", "patient_id",
                                      "sex") if c in csf.columns])
    d = d.merge(lab, left_on="bdsp_id", right_on="eeg_id", how="inner")
    d = d.merge(gate[["eeg_id", "p_focal", "p_generalized"]], on="eeg_id", how="left")
    d = d[d.age.notna() & d.p_generalized.notna() & ~d.eeg_id.astype(str).str.startswith("ON_")]

    # --- Morgoth's CALL. Thresholds by Youden J against the corrected report labels, on clean_pair only
    #     (the labels are used ONLY to pick the operating point, never to define the groups plotted).
    rec = d.drop_duplicates("eeg_id")
    cp = rec[rec.clean_pair == True]                                       # noqa: E712
    tf = youden(cp.slowing_focal.fillna(False).astype(int), cp.p_focal)
    tg = youden(cp.slowing_gen_pathologic.fillna(False).astype(int), cp.p_generalized)
    print(f"gate operating points (Youden J on clean_pair): p_focal >= {tf:.3f} | p_generalized >= {tg:.3f}")

    fire_f, fire_g = d.p_focal >= tf, d.p_generalized >= tg
    d["gate_call"] = np.where(
        ~fire_f & ~fire_g, GROUPS[0],
        np.where(fire_g & (~fire_f | (d.p_generalized >= d.p_focal)), GROUPS[2], GROUPS[1]))

    # --- normative deviation: each feature z'd against ITS OWN STAGE's age-matched clean-normal curve
    d["dev"] = np.nan
    for st in STAGES:
        m = d.stage == st
        if m.sum() < 200:
            continue
        ref = d[m & (d.clean_normal == True) & (d.clean_pair == True)]      # noqa: E712
        acc, k = np.zeros(int(m.sum())), 0
        for f in SLOW_FEATS:
            nz = fit_norm(ref.age.values.astype(float), ref[f].values.astype(float))
            if nz is None:
                continue
            acc += z_of(nz, d.loc[m, "age"].values.astype(float), d.loc[m, f].values)
            k += 1
        if k:
            d.loc[m, "dev"] = acc / k

    p = d.dropna(subset=["dev"])
    print(f"\nrecordings x stage cells: {len(p):,}  ({p.eeg_id.nunique():,} recordings)")

    # ------------------------------------------------------------------ the figure
    fig, ax = plt.subplots(figsize=(11.5, 6))
    W = 0.26
    rows = []
    for gi, (grp, col) in enumerate(zip(GROUPS, COLORS)):
        for si, st in enumerate(STAGES):
            v = p[(p.gate_call == grp) & (p.stage == st)].dev.values
            if len(v) < 10:
                continue
            pos = si + (gi - 1) * W
            bp = ax.boxplot([v], positions=[pos], widths=W * 0.88, showfliers=False,
                            patch_artist=True, medianprops=dict(color="black", lw=1.6))
            bp["boxes"][0].set_facecolor(col); bp["boxes"][0].set_alpha(.85)
            bp["boxes"][0].set_edgecolor("#333"); bp["boxes"][0].set_linewidth(.8)
            rows.append({"stage": st, "gate_call": grp, "n": len(v),
                         "median_z": round(float(np.median(v)), 3),
                         "IQR": f"[{np.percentile(v,25):.2f}, {np.percentile(v,75):.2f}]"})
            ax.text(pos, -3.62, f"{len(v):,}", ha="center", va="center", fontsize=6.2, color="#666",
                    rotation=90)

    ax.axhline(0, color="#333", lw=1.1, ls="--", zorder=0)
    ax.text(-0.60, 0.10, "0 = normal\nfor this age\nAND this stage",
            fontsize=7, color="#555", va="bottom", ha="left")
    ax.set_xticks(range(len(STAGES)))
    ax.set_xticklabels([f"{s}" for s in STAGES], fontsize=11)
    ax.tick_params(axis="x", length=0, pad=26)          # keep the stage labels clear of the n counts
    ax.set_xlim(-0.65, len(STAGES) - 0.35)
    ax.set_ylim(-4.1, 4.4)
    ax.set_xlabel("Sleep stage (each recording scored against its OWN stage's normal curve)")
    ax.set_ylabel("Normative deviation  (whole-head slowing z:  log δ, TAR, DAR)")
    ax.set_title("How much slowing, in the recordings Morgoth says have slowing\n"
                 "The gate detects; the normative deviation quantifies. Boxes: median, IQR, 1.5×IQR.",
                 fontsize=12)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, alpha=.85, ec="#333") for c in COLORS]
    ax.legend(handles, GROUPS, frameon=False, fontsize=9, loc="upper right", ncol=3)
    ax.grid(alpha=.22, axis="y")
    fig.text(0.012, 0.012,
             "Gating is PER-RECORDING (Morgoth's EEG-level FOC/GEN heads). Morgoth's window head is 3-class "
             "{0 others, 1 focal, 2 generalized}, so per-SEGMENT focal/generalized probabilities exist — but the "
             "fleet worker kept only 1−P(class 0) and discarded them. Recovering them needs a gate re-run.",
             fontsize=6.6, color="#777", wrap=True)
    fig.tight_layout(rect=[0, 0.045, 1, 1])
    Path("figures/growth_v2").mkdir(parents=True, exist_ok=True)
    fig.savefig("figures/growth_v2/gated_deviation_by_stage.png", dpi=150)
    plt.close(fig)

    t = pd.DataFrame(rows)
    piv = t.pivot(index="gate_call", columns="stage", values="median_z").reindex(GROUPS)[STAGES]
    npiv = t.pivot(index="gate_call", columns="stage", values="n").reindex(GROUPS)[STAGES]
    print("\nmedian deviation z by stage x Morgoth's call:")
    print(piv.to_string())
    print("\nn recordings per cell:")
    print(npiv.to_string())

    Path("results").mkdir(exist_ok=True)
    Path("results/gated_deviation_by_stage.md").write_text(
        "# Figure 4 / Table 2 — how much slowing, in the recordings Morgoth says have slowing\n\n"
        "The previous version of this figure reported the normative deviation as a **standalone detector** "
        "(AUROC vs the report label, per stage). That is not how the deviation is meant to be used, and we "
        "never intend to report slowing except where Morgoth has already decided there is slowing. The "
        "deviation is the **quantifier**, not the detector.\n\n"
        "This figure groups recordings by **Morgoth's call** and shows, within each sleep stage, the "
        "distribution of normative deviation from normal. Because every recording is scored against **its "
        "own stage's** age-matched normal curve, the quantity stays interpretable in N2/N3 — where raw delta "
        "is uninformative because deep sleep is *supposed* to be slow.\n\n"
        f"Gate operating points, chosen by Youden J against the corrected report labels on the `clean_pair` "
        f"set (labels pick the threshold only; they do not define the groups plotted): "
        f"**p_focal ≥ {tf:.3f}**, **p_generalized ≥ {tg:.3f}**.\n\n"
        "## Median deviation z\n\n" + piv.round(2).to_markdown() + "\n\n"
        "## n recordings per cell\n\n" + npiv.to_markdown() + "\n\n"
        "## The honest limit\n\n"
        "**The gating here is per-RECORDING, not per-segment.** Morgoth's SLOWING head is a 3-class "
        "*per-window* head — `{0: Others, 1: Focal Slowing, 2: Generalized Slowing}` "
        "(`morgoth2/results_figures.py:2790`) — so per-segment focal and generalized probabilities *do* "
        "exist. Our fleet worker did not keep them: `scripts/31_segment_master_worker.py:162` collapses the "
        "window head to `p_slowing = 1 − class_0_prob` and discards `class_1_prob` / `class_2_prob`. The "
        "focal/generalized split we persisted comes from the separate **EEG-level** heads, which emit one "
        "probability per recording.\n\n"
        "Recovering per-segment focal/generalized requires re-running Morgoth's SLOWING window head across "
        "the fleet and persisting all three class probabilities. Nothing on disk substitutes for it.\n")
    print("\nwrote figures/growth_v2/gated_deviation_by_stage.png + results/gated_deviation_by_stage.md")


if __name__ == "__main__":
    main()
