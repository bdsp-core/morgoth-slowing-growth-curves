#!/usr/bin/env python3
"""Regenerate the manuscript's supplementary appendix (Figures F1-F4b) on the v6 run.

WHY THIS EXISTS. Every one of these figures was produced by a script now in scripts/archive/, reading the
LEGACY derived tables. They therefore predate BOTH corrections:
  * the label bug  — 5,528 recordings of PHYSIOLOGIC drowsy slowing were scored as pathologic;
  * the age bug    — `age` was a whole number of years for 100% of recordings, and partly wrong.
So the appendix figures, and the numbers quoted around them in the manuscript (e.g. "AUC 0.962 versus
Morgoth 0.921", "0.79 in children rising to 0.95 in older adults"), are stale. Four of them
(discrimination_auc, roc_prc, lr_vs_morgoth, region_confusion_supervised) had no producer left in the repo
at all — the manuscript referenced figures that did not exist.

This rebuilds them from the v6 canonical tables with the CORRECTED SAP labels and the AUTHORITATIVE ages
(metadata/ages_v6.parquet), using exactly the label construction Table 6 uses:
    abnormal    = slowing_positive  vs clean_normal
    generalized = slowing_gen_pathologic vs clean_normal
    focal       = slowing_focal          vs clean_normal
all restricted to clean_pair (SAP §3.3 report-broadcast guard).

F4c (region confusion, supervised) is NOT regenerated — it needs a supervised region classifier that no
longer exists in the repo. Its manuscript reference is removed rather than left pointing at nothing.

Run: PYTHONPATH=src MPLBACKEND=Agg python scripts/106_appendix_figures_v6.py
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve, average_precision_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

STAGES = ["W", "N1", "N2", "N3", "REM"]
AGE_BANDS = [(0, 12), (12, 18), (18, 40), (40, 60), (60, 75), (75, 91)]
BAND_LBL = ["0–12", "12–18", "18–40", "40–60", "60–75", "75+"]
DEV_FEATS = ["rel_delta", "DAR", "TAR"]
C_NORM, C_ABN, C_GATE = "#2c7fb8", "#d95f02", "#111111"


def fit_norm(age, val, bw=8.0, grid=np.arange(0, 91, 0.5)):
    """Age-smoothed normative mean/sd from the clean-normals (Gaussian kernel, bw years)."""
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


def smooth_median(age, val, grid, bw=6.0, qs=(0.5,)):
    """Weighted quantile curve over age (used for the display bands)."""
    a, v = np.asarray(age, float), np.asarray(val, float)
    ok = np.isfinite(a) & np.isfinite(v); a, v = a[ok], v[ok]
    out = {q: np.full(len(grid), np.nan) for q in qs}
    for j, g in enumerate(grid):
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


def auc(y, s):
    y = np.asarray(y); s = np.asarray(s, float)
    ok = np.isfinite(s)
    if ok.sum() < 30 or len(np.unique(y[ok])) < 2:
        return np.nan
    a = roc_auc_score(y[ok], s[ok])
    return max(a, 1 - a)


def main():
    Path("figures/curves").mkdir(parents=True, exist_ok=True)
    Path("figures/stage_curves").mkdir(parents=True, exist_ok=True)
    Path("figures/roc_prc").mkdir(parents=True, exist_ok=True)
    Path("results/figs").mkdir(parents=True, exist_ok=True)

    csf = pd.read_parquet("data/derived/channel_stage_features.parquet")
    csf = csf[csf.region == "whole_head"].copy()
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    LB = ["eeg_id", "patient_id", "clean_normal", "slowing_positive", "slowing_focal",
          "slowing_gen_pathologic", "clean_pair", "age", "sex"]
    lab = lab[LB]
    vp = pd.read_parquet("data/derived/_vp_per_recording.parquet")[["eeg_id", "p_slowing_p90"]]

    d = csf.drop(columns=[c for c in ("age", "sex", "patient_id", "clean_normal", "clean_pair",
                                      "is_abnormal") if c in csf.columns])
    d = d.merge(lab, left_on="bdsp_id", right_on="eeg_id", how="inner")
    d = d[(d.clean_pair == True) & d.age.notna()]                      # noqa: E712
    print(f"whole_head rows on clean_pair: {len(d):,} "
          f"({d.eeg_id.nunique():,} recordings)  age max={d.age.max():.1f}")

    # ---------------------------------------------------------------- F1: developmental delta curve
    w = d[d.stage == "W"]
    nrm = w[w.clean_normal == True]                                    # noqa: E712
    abn = w[w.slowing_positive == True]                                # noqa: E712
    grid = np.arange(0.25, 90, 0.5)
    qn = smooth_median(nrm.age, nrm.log_delta, grid, qs=(0.1, 0.5, 0.9))
    qa = smooth_median(abn.age, abn.log_delta, grid, qs=(0.5,))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(nrm.age, nrm.log_delta, s=2, alpha=.10, color=C_NORM, lw=0, label=None, rasterized=True)
    ax.fill_between(grid, qn[0.1], qn[0.9], color=C_NORM, alpha=.22, lw=0,
                    label="clean-normal 10–90th pct")
    ax.plot(grid, qn[0.5], color=C_NORM, lw=2.4, label=f"clean-normal median (n={len(nrm):,})")
    ax.plot(grid, qa[0.5], color=C_ABN, lw=2.4, ls="--", label=f"slowing-positive median (n={len(abn):,})")
    ax.set_xscale("log")
    ax.set_xticks([0.25, 0.5, 1, 2, 5, 10, 20, 40, 60, 90])
    ax.set_xticklabels(["3 mo", "6 mo", "1", "2", "5", "10", "20", "40", "60", "90"])
    ax.set_xlim(0.15, 90)
    ax.set_xlabel("Age (years, log scale)"); ax.set_ylabel("log delta power (whole head, wake)")
    ax.set_title("F1 — Developmental delta growth curve (v6, corrected labels + exact ages)")
    ax.legend(frameon=False, fontsize=8); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig("figures/curves/log_delta__whole_head.png", dpi=150); plt.close(fig)
    print("wrote figures/curves/log_delta__whole_head.png  (F1)")

    # ---------------------------------------------------------------- F2: stage-resolved norms
    fig, ax = plt.subplots(figsize=(8, 5))
    med = {}
    for st, col in zip(STAGES, ["#4575b4", "#91bfdb", "#fdae61", "#d73027", "#7b3294"]):
        s = d[(d.stage == st) & (d.clean_normal == True)]              # noqa: E712
        if len(s) < 200:
            continue
        q = smooth_median(s.age, s.rel_delta, grid, qs=(0.5,))
        ax.plot(grid, q[0.5], color=col, lw=2.2, label=f"{st} (n={len(s):,})")
        med[st] = float(np.nanmedian(s.rel_delta))
    ax.set_xscale("log")
    ax.set_xticks([0.25, 0.5, 1, 2, 5, 10, 20, 40, 60, 90])
    ax.set_xticklabels(["3 mo", "6 mo", "1", "2", "5", "10", "20", "40", "60", "90"])
    ax.set_xlim(0.15, 90)
    ax.set_xlabel("Age (years, log scale)"); ax.set_ylabel("relative delta (whole head)")
    ax.set_title("F2 — Stage-resolved normative curves, clean-normals (v6)")
    ax.legend(frameon=False, fontsize=8, title="stage"); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig("figures/stage_curves/rel_delta__whole_head.png", dpi=150); plt.close(fig)
    order = " < ".join(sorted(med, key=med.get))
    print(f"wrote figures/stage_curves/rel_delta__whole_head.png  (F2)  median rel_delta order: {order}")

    # DAR stage curves — the dashboard's Figure 3 pairs rel_delta with DAR. Its DAR panel was the last
    # figure still dating from the pre-age-fix run.
    fig, ax = plt.subplots(figsize=(8, 5))
    for st, col in zip(STAGES, ["#4575b4", "#91bfdb", "#fdae61", "#d73027", "#7b3294"]):
        s = d[(d.stage == st) & (d.clean_normal == True)]              # noqa: E712
        if len(s) < 200 or "DAR" not in s.columns:
            continue
        q = smooth_median(s.age, s.DAR, grid, qs=(0.5,))
        ax.plot(grid, q[0.5], color=col, lw=2.2, label=f"{st} (n={len(s):,})")
    ax.set_xscale("log")
    ax.set_xticks([0.25, 0.5, 1, 2, 5, 10, 20, 40, 60, 90])
    ax.set_xticklabels(["3 mo", "6 mo", "1", "2", "5", "10", "20", "40", "60", "90"])
    ax.set_xlim(0.15, 90)
    ax.set_xlabel("Age (years, log scale)"); ax.set_ylabel("DAR (delta/alpha ratio, whole head)")
    ax.set_title("Stage-resolved DAR norms, clean-normals (v6)")
    ax.legend(frameon=False, fontsize=8, title="stage"); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig("figures/stage_curves/DAR__whole_head.png", dpi=150); plt.close(fig)
    print("wrote figures/stage_curves/DAR__whole_head.png")

    # ---------------------------------------------------------------- deviation score (for F2b)
    # sum of |z| over rel_delta/DAR/TAR, each z'd against its own (stage) age-matched normal curve
    d["dev"] = 0.0; d["dev_ok"] = True
    for st in STAGES:
        ms = d.stage == st
        if ms.sum() < 200:
            continue
        ref = d[ms & (d.clean_normal == True)]                          # noqa: E712
        acc = np.zeros(int(ms.sum()))
        for f in DEV_FEATS:
            nz = fit_norm(ref.age.values.astype(float), ref[f].values.astype(float))
            acc += np.abs(z_of(nz, d.loc[ms, "age"].values.astype(float), d.loc[ms, f].values))
        d.loc[ms, "dev"] = acc

    # ---------------------------------------------------------------- F2b: stage-stratified AUROC by age
    rows = []
    for st in STAGES:
        for (lo, hi), bl in zip(AGE_BANDS, BAND_LBL):
            s = d[(d.stage == st) & d.age.between(lo, hi, inclusive="left")]
            s = s[(s.clean_normal == True) | (s.slowing_positive == True)]      # noqa: E712
            if len(s) < 60:
                continue
            a = auc(s.slowing_positive.astype(int).values, s.dev.values)
            if np.isfinite(a):
                rows.append({"stage": st, "age_band": bl, "n": len(s), "AUROC": round(a, 3)})
    t2b = pd.DataFrame(rows)
    t2b.to_csv("results/age_auroc_by_stage.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for st in STAGES:
        s = t2b[t2b.stage == st]
        if s.empty:
            continue
        ax.plot(s.age_band, s.AUROC, marker="o", lw=1.8, label=st)
    ax.axhline(.5, color="gray", ls=":", lw=1)
    ax.set_ylim(.4, 1.0); ax.set_xlabel("Age band (y)"); ax.set_ylabel("AUROC (slowing-positive vs clean-normal)")
    ax.set_title("F2b — Spectral deviation score: stage-stratified detection by age (v6)")
    ax.legend(frameon=False, fontsize=8, title="stage", ncol=5); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig("results/figs/age_auroc_by_stage.png", dpi=150); plt.close(fig)
    print(f"wrote results/figs/age_auroc_by_stage.png  (F2b)  AUROC range "
          f"{t2b.AUROC.min():.2f}–{t2b.AUROC.max():.2f}")

    # ---------------------------------------------------------------- per-recording table for F3/F4/F4b
    r = lab[lab.clean_pair == True].merge(vp, on="eeg_id", how="inner")     # noqa: E712
    r = r[r.age.notna() & r.p_slowing_p90.notna()]
    dev_rec = d.groupby("eeg_id").dev.mean().rename("dev_rec")
    r = r.merge(dev_rec, left_on="eeg_id", right_index=True, how="left")
    print(f"per-recording scoring set: {len(r):,}")

    TASKS = [("abnormal", "slowing_positive"), ("generalized", "slowing_gen_pathologic"),
             ("focal", "slowing_focal")]

    # ---------------------------------------------------------------- F4b: gate AUROC vs age
    rows = []
    for tname, tcol in TASKS:
        sub = r[(r.clean_normal == True) | (r[tcol] == True)]               # noqa: E712
        for (lo, hi), bl in zip(AGE_BANDS, BAND_LBL):
            s = sub[sub.age.between(lo, hi, inclusive="left")]
            if len(s) < 60:
                continue
            a = auc(s[tcol].fillna(False).astype(int).values, s.p_slowing_p90.values)
            if np.isfinite(a):
                rows.append({"task": tname, "age_band": bl, "n": len(s), "AUROC": round(a, 3)})
    t4b = pd.DataFrame(rows)
    t4b.to_csv("results/age_auroc.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for tname, _ in TASKS:
        s = t4b[t4b.task == tname]
        if s.empty:
            continue
        ax.plot(s.age_band, s.AUROC, marker="o", lw=2, label=tname)
    ax.axhline(.5, color="gray", ls=":", lw=1)
    ax.set_ylim(.5, 1.0); ax.set_xlabel("Age band (y)"); ax.set_ylabel("AUROC (vs clean-normal)")
    ax.set_title("F4b — Morgoth gate discrimination by age (v6, corrected labels + exact ages)")
    ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig("results/figs/age_auroc.png", dpi=150); plt.close(fig)
    ab = t4b[t4b.task == "abnormal"]
    print(f"wrote results/figs/age_auroc.png  (F4b)  abnormal AUROC by band: "
          f"{dict(zip(ab.age_band, ab.AUROC))}")

    # ---------------------------------------------------------------- F3: ROC / PRC / discrimination bar
    sub = r[(r.clean_normal == True) | (r.slowing_positive == True)]        # noqa: E712
    y = sub.slowing_positive.astype(int).values
    figr, axr = plt.subplots(figsize=(5.4, 5.2))
    figp, axp = plt.subplots(figsize=(5.4, 5.2))
    for nm, sc, c in [("Morgoth gate (p_slowing)", sub.p_slowing_p90.values, C_GATE),
                      ("spectral deviation score", sub.dev_rec.values, C_NORM)]:
        ok = np.isfinite(sc)
        fpr, tpr, _ = roc_curve(y[ok], sc[ok])
        a = roc_auc_score(y[ok], sc[ok])
        if a < .5:
            fpr, tpr, a = tpr, fpr, 1 - a
        axr.plot(fpr, tpr, lw=2, color=c, label=f"{nm}  AUROC={a:.3f}")
        pr, rc, _ = precision_recall_curve(y[ok], sc[ok])
        axp.plot(rc, pr, lw=2, color=c,
                 label=f"{nm}  AP={average_precision_score(y[ok], sc[ok]):.3f}")
    axr.plot([0, 1], [0, 1], ls=":", color="gray", lw=1)
    axr.set_xlabel("False-positive rate"); axr.set_ylabel("True-positive rate")
    axr.set_title("F3 — ROC, slowing-positive vs clean-normal (v6)")
    axr.legend(frameon=False, fontsize=8, loc="lower right"); axr.grid(alpha=.25)
    figr.tight_layout(); figr.savefig("figures/roc_prc/roc.png", dpi=150); plt.close(figr)
    axp.axhline(y.mean(), ls=":", color="gray", lw=1)
    axp.set_xlabel("Recall"); axp.set_ylabel("Precision")
    axp.set_title("F3 — Precision–recall (v6)")
    axp.legend(frameon=False, fontsize=8, loc="lower left"); axp.grid(alpha=.25)
    figp.tight_layout(); figp.savefig("figures/roc_prc/prc.png", dpi=150); plt.close(figp)

    bars = []
    for tname, tcol in TASKS:
        s = r[(r.clean_normal == True) | (r[tcol] == True)]                 # noqa: E712
        yy = s[tcol].fillna(False).astype(int).values
        bars.append({"task": tname, "Morgoth gate": auc(yy, s.p_slowing_p90.values),
                     "spectral deviation": auc(yy, s.dev_rec.values)})
    bd = pd.DataFrame(bars).set_index("task")
    fig, ax = plt.subplots(figsize=(7, 4.4))
    x = np.arange(len(bd)); wd = .36
    ax.bar(x - wd/2, bd["Morgoth gate"], wd, color=C_GATE, label="Morgoth gate")
    ax.bar(x + wd/2, bd["spectral deviation"], wd, color=C_NORM, label="spectral deviation")
    for i, (m, s) in enumerate(zip(bd["Morgoth gate"], bd["spectral deviation"])):
        ax.text(i - wd/2, m + .012, f"{m:.3f}", ha="center", fontsize=8)
        ax.text(i + wd/2, s + .012, f"{s:.3f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(bd.index)
    ax.axhline(.5, color="gray", ls=":", lw=1)
    ax.set_ylim(.5, 1.0); ax.set_ylabel("AUROC (vs clean-normal)")
    ax.set_title("F3 — Discrimination by task (v6, corrected labels + exact ages)")
    ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.25, axis="y")
    fig.tight_layout(); fig.savefig("figures/discrimination_auc.png", dpi=150); plt.close(fig)
    print(f"wrote figures/roc_prc/{{roc,prc}}.png + figures/discrimination_auc.png  (F3)")
    print("  " + bd.round(3).to_string().replace("\n", "\n  "))

    # ---------------------------------------------------------------- F4: deviation LR vs Morgoth
    # Cross-fitted by PATIENT so the LR's probability is out-of-fold (SAP §3.3 clustering).
    lr_in = r[r.dev_rec.notna() & r.sex.notna()].copy()
    lr_in["is_f"] = lr_in.sex.astype(str).str[0].str.upper().eq("F").astype(float)
    X = lr_in[["dev_rec", "age", "is_f"]].values
    ylr = lr_in.slowing_positive.fillna(False).astype(int).values
    p_lr = np.full(len(lr_in), np.nan)
    gkf = GroupKFold(n_splits=5)
    for tr, te in gkf.split(X, ylr, groups=lr_in.patient_id.values):
        m = LogisticRegression(max_iter=2000).fit(X[tr], ylr[tr])
        p_lr[te] = m.predict_proba(X[te])[:, 1]
    lr_in["p_lr"] = p_lr
    ok = np.isfinite(p_lr) & np.isfinite(lr_in.p_slowing_p90.values)
    pm = lr_in.p_slowing_p90.values[ok]
    pearson = float(np.corrcoef(p_lr[ok], pm)[0, 1])
    spear = float(pd.Series(p_lr[ok]).corr(pd.Series(pm), method="spearman"))
    a_lr = auc(ylr[ok], p_lr[ok]); a_mg = auc(ylr[ok], pm)
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.scatter(pm, p_lr[ok], s=3, alpha=.12, lw=0, color=C_NORM, rasterized=True)
    ax.plot([0, 1], [0, 1], ls=":", color="gray", lw=1)
    ax.set_xlabel("Morgoth gate  p_slowing (p90)"); ax.set_ylabel("deviation LR  P(slowing)  [out-of-fold]")
    ax.set_title(f"F4 — Deviation LR vs Morgoth (v6)\nPearson r={pearson:.3f}, Spearman ρ={spear:.3f}")
    ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig("figures/lr_vs_morgoth.png", dpi=150); plt.close(fig)
    Path("results/lr_vs_morgoth.md").write_text(
        "# F4 — objective deviation LR vs the Morgoth gate (v6)\n\n"
        "Recomputed on the v6 run with the **corrected SAP labels** and the **authoritative exact ages**. "
        "The LR (spectral deviation + age + sex) is **cross-fitted by patient** (5-fold `GroupKFold`), so its "
        "probability is out-of-fold — the legacy version reported an in-sample AUC (0.962), which is why it "
        "appeared to beat the gate.\n\n"
        f"| quantity | value |\n|---|---|\n"
        f"| n recordings | {int(ok.sum()):,} |\n"
        f"| Pearson r (LR vs Morgoth) | {pearson:.3f} |\n"
        f"| Spearman ρ | {spear:.3f} |\n"
        f"| AUROC — deviation LR (out-of-fold) | {a_lr:.3f} |\n"
        f"| AUROC — Morgoth gate | {a_mg:.3f} |\n\n"
        f"The gate out-ranks the objective deviation model ({a_mg:.3f} vs {a_lr:.3f}); the two agree only "
        f"moderately (ρ={spear:.3f}), so the deviation features capture much — not all — of what the "
        "report-calibrated detector encodes. This supports keeping Morgoth as the gate and the deviation "
        "field as the *descriptor*.\n")
    print(f"wrote figures/lr_vs_morgoth.png + results/lr_vs_morgoth.md  (F4)  "
          f"r={pearson:.3f} rho={spear:.3f} | AUROC LR={a_lr:.3f} vs Morgoth={a_mg:.3f}")

    # ---------------------------------------------------------------- van Putten comparison (dashboard Fig 9)
    # The dashboard embedded results/figs/vanputten_comparison.png from the LEGACY run (3,130 recordings,
    # no clean_pair filter). Redraw it straight from the current Table 6 so the two cannot disagree.
    import re as _re
    rows_vp = {}
    for ln in Path("results/vanputten_fullcoverage.md").read_text().splitlines():
        if not ln.startswith("|") or ln.startswith("|:") or "method" in ln:
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) < 4:
            continue
        v = [float(_re.match(r"([0-9.]+)", x).group(1)) for x in c[1:4] if _re.match(r"([0-9.]+)", x)]
        if len(v) == 3:
            rows_vp[c[0].replace("*", "").strip()] = v
    if rows_vp:
        names = list(rows_vp)
        gate = [n for n in names if "Morgoth" in n]
        others = [n for n in names if n not in gate]
        order = others + gate
        y = np.arange(len(order))[::-1]
        fig, ax = plt.subplots(figsize=(10, 0.42 * len(order) + 2))
        w = 0.26
        for k, (tname, col) in enumerate(zip(["abnormal", "generalized", "focal"],
                                             ["#4c78a8", "#e45756", "#54a24b"])):
            vals = [rows_vp[n][k] for n in order]
            bars = ax.barh(y + (1 - k) * w, vals, w, color=col, label=tname)
            for b, n in zip(bars, order):
                if "Morgoth" in n:
                    b.set_edgecolor("black"); b.set_linewidth(1.4)
        ax.set_yticks(y); ax.set_yticklabels(order, fontsize=8)
        ax.set_xlim(0.5, 1.0); ax.axvline(.5, color="gray", lw=1, ls=":")
        ax.set_xlabel("AUROC vs clean-normal (patient-clustered bootstrap)")
        ax.set_title("Table 6 — Morgoth gate vs the van Putten lineage (v6, SAP §3.3 clean_pair set)")
        ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower right")
        ax.grid(alpha=.25, axis="x")
        Path("results/figs").mkdir(parents=True, exist_ok=True)
        fig.tight_layout(); fig.savefig("results/figs/vanputten_comparison.png", dpi=150); plt.close(fig)
        g = rows_vp[gate[0]] if gate else [np.nan] * 3
        print(f"wrote results/figs/vanputten_comparison.png  (gate {g[0]}/{g[1]}/{g[2]}, "
              f"{len(order)} arms, redrawn from Table 6)")

    Path("results/appendix_v6_numbers.json").write_text(json.dumps({
        "f2b_auroc_by_stage": t2b.to_dict("records"),
        "f4b_gate_auroc_by_age": t4b.to_dict("records"),
        "f3_discrimination": bd.round(4).to_dict(),
        "f4_lr_vs_morgoth": {"pearson": round(pearson, 4), "spearman": round(spear, 4),
                             "auroc_lr_oof": round(a_lr, 4), "auroc_morgoth": round(a_mg, 4),
                             "n": int(ok.sum())},
    }, indent=2))
    print("\nwrote results/appendix_v6_numbers.json  (the numbers the manuscript must quote)")


if __name__ == "__main__":
    main()
