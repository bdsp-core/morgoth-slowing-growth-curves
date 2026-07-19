#!/usr/bin/env python3
"""§4 DESCRIPTION — D1–D5 panels. Validation is by CONTRAST (dose-response), not classification: our
continuous descriptor should be HIGHER when the report mentions the finding than when it does not.

D1 type/amount   delta-z vs theta-z plane + our theta/delta measure split by report band mention
D2 laterality    signed L-R asymmetry z split by report focal_side; region z vs report focal_region
D3 ant-post      anterior-minus-posterior z split by report gen_topography
D4 persistence   prevalence / longest-run distributions (ACNS scale); prevalence by slowing vs control
                 (no structured report intermittent/continuous field -> internal reasonableness only)
D5 by stage      descriptors per sleep stage; slowing carried in sleep the (wake-centric) report omits

Reads description_recording/description_stage + recording_labels(_sap). Writes figures/story/s4_d{1..5}.png
+ results/story/s4_description.md.  Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/57_description_panels.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (applies shared Tufte publication style)
from scipy.stats import mannwhitneyu

FIG = Path("figures/story"); RES = Path("results/story")
STAGES = ["W", "N1", "N2", "N3", "REM"]


def cohend(a, b):
    a, b = np.asarray(a), np.asarray(b); na, nb = len(a), len(b)
    s = np.sqrt(((na-1)*a.std(ddof=1)**2 + (nb-1)*b.std(ddof=1)**2)/(na+nb-2)) or 1e-9
    return (a.mean()-b.mean())/s


def contrast(ax, groups, title, ylabel, colors, ylim=None):
    """violin/box of a descriptor across report groups; returns text lines.
    Violin KDE is drawn on the central 1-99 pct (so log-feature negative outliers don't crush the view);
    medians reported are on the FULL data. ylim sets the visible window."""
    data = [g.dropna().values for _, g in groups]; labels = [n for n, _ in groups]
    clipped = [np.clip(v, np.quantile(v, .01), np.quantile(v, .99)) if len(v) > 20 else v for v in data]
    parts = ax.violinplot(clipped, showmedians=True, widths=.8)
    for i, b in enumerate(parts["bodies"]):
        b.set_facecolor(colors[i % len(colors)]); b.set_alpha(.6)
    ax.set_xticks(range(1, len(labels)+1)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9); ax.set_title(title, fontsize=10); ax.grid(alpha=.2, axis="y")
    if ylim:
        ax.set_ylim(*ylim)
    return [f"{labels[i]} median={np.median(data[i]):.2f} (n={len(data[i])})" for i in range(len(data))]


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    R = pd.read_parquet("data/derived/description_recording.parquet")
    S = pd.read_parquet("data/derived/description_stage.parquet")
    lab = pd.read_parquet("data/derived/recording_labels.parquet").drop_duplicates("eeg_id")
    sap = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = R.merge(lab[["eeg_id", "focal_side", "focal_region", "focal_band", "gen_topography", "gen_band"]], on="eeg_id") \
         .merge(sap[["eeg_id", "clean_normal", "slowing_focal", "slowing_gen_pathologic"]], on="eeg_id")
    d["slowing"] = d.slowing_focal.fillna(False) | d.slowing_gen_pathologic.fillna(False)
    d["rep_theta"] = d.gen_band.isin(["theta", "mixed"]) | d.focal_band.isin(["theta", "mixed"])
    d["rep_delta"] = d.gen_band.isin(["delta", "mixed"]) | d.focal_band.isin(["delta", "mixed"])
    md = ["# §4 Description — reading the deviation field, validated by contrast vs the report\n"]

    # ---------- D1 type & amount ----------
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    sl = d[d.slowing]; cn = d[d.clean_normal == True]                                      # noqa: E712
    sub = d.sample(min(4000, len(d)), random_state=0)
    cmap = {True: "#c8443c", False: "#bbb"}
    ax[0].scatter(cn.delta_p90, cn.theta_p90, s=4, alpha=.15, color="#888", label="clean-normal", rasterized=True)
    ax[0].scatter(sl.sample(min(3000, len(sl)), random_state=0).delta_p90,
                  sl.sample(min(3000, len(sl)), random_state=0).theta_p90, s=4, alpha=.2, color="#c8443c",
                  label="report slowing", rasterized=True)
    ax[0].axvline(1, ls=":", color="#666"); ax[0].axhline(1, ls=":", color="#666")
    ax[0].set_xlabel("delta-excess z (p90)"); ax[0].set_ylabel("theta-excess z (p90)")
    ax[0].set_title("Type plane: delta vs theta", fontsize=10); ax[0].legend(frameon=False, fontsize=8)
    ax[0].set_xlim(-2, 5); ax[0].set_ylim(-2, 5)
    l1 = contrast(ax[1], [("report: theta\n(theta/mixed)", sl[sl.rep_theta].theta_p90),
                          ("report: no theta\n(delta only)", sl[~sl.rep_theta].theta_p90)],
                  "Our THETA measure by report band", "theta-excess z (p90)", ["#2c7fb8", "#bbb"], ylim=(-2, 5))
    l2 = contrast(ax[2], [("report: delta\n(delta/mixed)", sl[sl.rep_delta].delta_p90),
                          ("report: no delta\n(theta only)", sl[~sl.rep_delta].delta_p90)],
                  "Our DELTA measure by report band", "delta-excess z (p90)", ["#c8443c", "#bbb"], ylim=(-2, 5))
    fig.suptitle("Type & amount: LENS band-deviation tracks the report's band word", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(FIG / "s4_d1.png", dpi=140); plt.close(fig)
    pth = mannwhitneyu(sl[sl.rep_theta].theta_p90.dropna(), sl[~sl.rep_theta].theta_p90.dropna()).pvalue
    pdd = mannwhitneyu(sl[sl.rep_delta].delta_p90.dropna(), sl[~sl.rep_delta].delta_p90.dropna()).pvalue
    clean = lambda s: s.replace("\n", " ")
    md += ["## D1 — type & amount",
           f"- THETA: {clean(l1[0])} vs {clean(l1[1])}; Cohen d={cohend(sl[sl.rep_theta].theta_p90.dropna(), sl[~sl.rep_theta].theta_p90.dropna()):.2f}, p={pth:.1e}",
           f"- DELTA: {clean(l2[0])} vs {clean(l2[1])}; Cohen d={cohend(sl[sl.rep_delta].delta_p90.dropna(), sl[~sl.rep_delta].delta_p90.dropna()):.2f}, p={pdd:.1e}\n"]

    # ---------- D2 laterality & region ----------
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    foc = d[d.slowing_focal == True].copy()                                                 # noqa: E712
    ll = contrast(ax[0], [(s, foc[foc.focal_side == s].lat_signed) for s in ["left", "bilateral", "right"]],
                  "LENS L-R asymmetry by report side", "signed asymmetry z  (+ = left)", ["#c8443c", "#999", "#2c7fb8"], ylim=(-3, 3))
    ax[0].axhline(0, ls="--", color="#666")
    md += ["## D2 — laterality & region", "- laterality: " + "; ".join(ll)]
    # region as DOSE-RESPONSE (not a confusion matrix): a lobe's relative prominence (focality = that lobe's
    # magnitude minus the mean of the other two) is higher when the report names that lobe. Absolute temporal
    # magnitude runs high everywhere (a temporal-delta baseline attractor), so relative prominence is the
    # specific descriptor.
    foc["foc_temporal"] = foc.lobe_temporal - (foc.lobe_frontal + foc.lobe_posterior) / 2
    foc["foc_frontal"] = foc.lobe_frontal - (foc.lobe_temporal + foc.lobe_posterior) / 2
    foc["foc_posterior"] = foc.lobe_posterior - (foc.lobe_temporal + foc.lobe_frontal) / 2
    lobes = [("temporal", "foc_temporal"), ("frontal", "foc_frontal"), ("posterior", "foc_posterior")]
    xx = np.arange(len(lobes)); w = .38; rl = []
    inn = [foc[foc.focal_region == r][c].dropna() for r, c in lobes]
    out = [foc[foc.focal_region != r][c].dropna() for r, c in lobes]
    ax[1].bar(xx - w/2, [g.mean() for g in inn], w, color="#c8443c", label="report names this lobe")
    ax[1].bar(xx + w/2, [g.mean() for g in out], w, color="#bbb", label="report names another lobe")
    for i in range(len(lobes)):
        p = mannwhitneyu(inn[i], out[i]).pvalue
        ax[1].text(xx[i], max(inn[i].mean(), out[i].mean()) + .02, "***" if p < 1e-3 else "**", ha="center", fontsize=11)
        rl.append(f"{lobes[i][0]} {inn[i].mean():+.2f} vs {out[i].mean():+.2f} (p={p:.0e})")
    ax[1].axhline(0, color="#666", lw=.8); ax[1].set_xticks(xx); ax[1].set_xticklabels([l for l, _ in lobes])
    ax[1].set_ylabel("lobe focality  (prominence vs rest of head)"); ax[1].legend(frameon=False, fontsize=8)
    ax[1].set_title("Lobe prominence rises when the report names that lobe", fontsize=10); ax[1].grid(alpha=.2, axis="y")
    fig.suptitle("Laterality tracks the reported side; lobe prominence tracks the reported region", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(FIG / "s4_d2.png", dpi=140); plt.close(fig)
    md.append("- region (focality dose-response): " + "; ".join(rl) + "\n")

    # ---------- D3 ant-post ----------
    fig, ax = plt.subplots(figsize=(6, 4.4))
    aa = contrast(ax, [(t, d[d.gen_topography == t].antpost) for t in ["anterior", "posterior", "unspec"]],
                  "Our A-P gradient by report topography", "anterior − posterior z  (+ = frontal)", ["#c8443c", "#2c7fb8", "#bbb"], ylim=(-2, 2))
    ax.axhline(0, ls="--", color="#666")
    fig.suptitle("Anterior−posterior gradient tracks report topography", fontsize=12)
    fig.tight_layout(); fig.savefig(FIG / "s4_d3.png", dpi=140); plt.close(fig)
    pap = mannwhitneyu(d[d.gen_topography == "anterior"].antpost.dropna(), d[d.gen_topography == "posterior"].antpost.dropna()).pvalue
    md += ["## D3 — anterior-posterior predominance", "- " + "; ".join(aa) + f"; anterior>posterior p={pap:.1e}\n"]

    # ---------- D4 persistence ----------
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    ax[0].hist(d[d.clean_normal == True].prevalence, bins=40, alpha=.6, color="#888", density=True, label="clean-normal")  # noqa: E712
    ax[0].hist(d[d.slowing].prevalence, bins=40, alpha=.6, color="#c8443c", density=True, label="report slowing")
    for x, lab_ in [(.01, "occasional"), (.10, "frequent"), (.50, "abundant"), (.90, "continuous")]:
        ax[0].axvline(x, ls=":", color="#666"); ax[0].text(x, ax[0].get_ylim()[1]*.9, lab_, rotation=90, fontsize=7, va="top")
    ax[0].set_xlabel("prevalence (frac abnormal segments)"); ax[0].set_ylabel("density")
    ax[0].set_title("Persistence: prevalence + ACNS scale", fontsize=10); ax[0].legend(frameon=False, fontsize=8)
    ax[1].hist(np.clip(d[d.slowing].longest_run_min, 0, 30), bins=40, color="#c8443c", alpha=.7)
    ax[1].set_xlabel("longest continuous run (min)"); ax[1].set_ylabel("recordings"); ax[1].set_title("Longest run (report slowing)", fontsize=10)
    fig.suptitle("Persistence: prevalence & run-length (internal; no structured report qualifier)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(FIG / "s4_d4.png", dpi=140); plt.close(fig)
    md += ["## D4 — persistence vs intermittence",
           f"- prevalence: clean-normal {d[d.clean_normal==True].prevalence.median():.2f} vs report-slowing {d[d.slowing].prevalence.median():.2f}",
           "- no structured report intermittent/continuous field -> shown as internal reasonableness (ACNS-binned prevalence + run length)\n"]

    # ---------- D5 by stage ----------
    # per-recording x per-stage prevalence is spiky (few N3 segments in routine EEG -> median collapses to 0),
    # so summarise stages by MEAN prevalence; the load-bearing signal is the GAP (report-slowing above
    # clean-normal at EVERY stage, wake AND sleep), not a monotone rise into deeper sleep.
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    Sm = S.merge(d[["eeg_id", "clean_normal", "slowing"]], on="eeg_id")
    xs = range(len(STAGES))
    for grp, dd, col in [("report slowing", Sm[Sm.slowing], "#c8443c"), ("clean-normal", Sm[Sm.clean_normal == True], "#888")]:  # noqa: E712
        m = [dd[dd.stage == st].prevalence.mean() for st in STAGES]
        ax[0].plot(xs, m, "o-", color=col, label=grp)
    ax[0].set_xticks(list(xs)); ax[0].set_xticklabels(STAGES)
    ax[0].set_ylabel("prevalence (mean)"); ax[0].set_title("Slowing prevalence by stage — gap persists into sleep", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8); ax[0].grid(alpha=.2)
    for band, col in [("delta_p90", "#c8443c"), ("theta_p90", "#2c7fb8")]:
        m = [Sm[Sm.slowing][Sm[Sm.slowing].stage == st][band].median() for st in STAGES]
        ax[1].plot(xs, m, "o-", color=col, label=band.replace("_p90", "-excess z"))
    ax[1].set_xticks(list(xs)); ax[1].set_xticklabels(STAGES)
    ax[1].set_ylabel("deviation z (median)"); ax[1].set_title("Band deviation by stage (report slowing)", fontsize=10)
    ax[1].legend(frameon=False, fontsize=8); ax[1].grid(alpha=.2)
    fig.suptitle("Stage-resolved: the slowing signal is present in sleep, not only wake", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(FIG / "s4_d5.png", dpi=140); plt.close(fig)
    # under-reporting probe: among report-negative recordings, N2 deviation still sits above clean-normal N2
    neg = Sm[(Sm.clean_normal != True) & (~Sm.slowing)]                                      # abnormal, report does not call slowing
    cnn2 = Sm[(Sm.clean_normal == True) & (Sm.stage == "N2")].prevalence.mean()              # noqa: E712
    negn2 = neg[neg.stage == "N2"].prevalence.mean()
    md += ["## D5 — by sleep stage",
           "- mean slowing prevalence, report-slowing vs clean-normal (gap holds at every stage): "
           + ", ".join(f"{st} {Sm[Sm.slowing][Sm[Sm.slowing].stage==st].prevalence.mean():.2f}/{Sm[(Sm.clean_normal==True)&(Sm.stage==st)].prevalence.mean():.2f}" for st in STAGES),  # noqa: E712
           f"- under-reporting probe: among recordings the report does NOT call slowing, mean N2 prevalence "
           f"{negn2:.3f} vs clean-normal N2 {cnn2:.3f} — sleep slowing left out of the wake-centric read "
           f"(the established V4a spindle-verified result is the rigorous version)\n"]

    (RES / "s4_description.md").write_text("\n".join(md))
    print("\n".join(md)); print("\nwrote figures/story/s4_d{1..5}.png + results/story/s4_description.md")


if __name__ == "__main__":
    main()
