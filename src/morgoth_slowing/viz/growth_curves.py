"""Plot growth curves: percentile bands vs age, optionally with subjects overlaid by label."""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PCTL = [3, 10, 25, 50, 75, 90, 97]
LABEL_COLORS = {"normal": "#2c7fb8", "focal_slow": "#d95f02", "general_slow": "#7570b3"}


def plot_curve(curve_df, ax=None, color="#2c7fb8", label_prefix="", show_bands=True):
    """curve_df: columns age, p3..p97 (one sex). Draws median + shaded 10-90 / 25-75 bands."""
    ax = ax or plt.gca()
    a = curve_df["age"].values
    if show_bands:
        ax.fill_between(a, curve_df["p3"], curve_df["p97"], color=color, alpha=0.10, lw=0)
        ax.fill_between(a, curve_df["p10"], curve_df["p90"], color=color, alpha=0.15, lw=0)
        ax.fill_between(a, curve_df["p25"], curve_df["p75"], color=color, alpha=0.20, lw=0)
    ax.plot(a, curve_df["p50"], color=color, lw=2, label=f"{label_prefix}median")
    return ax


def growth_figure(curve_by_sex, feature, region, subjects=None, out=None):
    """curve_by_sex: tidy df with sex, age, p*. subjects: optional df age,value,label to scatter."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    # robust y-limits from all plotted values (curve + subjects)
    yvals = curve_by_sex[[f"p{p}" for p in PCTL]].values.ravel()
    if subjects is not None and len(subjects):
        yvals = np.concatenate([yvals, subjects["value"].values])
    yvals = yvals[np.isfinite(yvals)]
    ylo, yhi = (np.percentile(yvals, 1), np.percentile(yvals, 99)) if len(yvals) else (None, None)
    order = ["normal", "focal_slow", "general_slow"]  # normals behind
    for ax, sex in zip(axes, ["F", "M"]):
        if subjects is not None:
            s = subjects[subjects.sex == sex] if "sex" in subjects else subjects
            for lab in order:
                g = s[s.label == lab]
                if len(g):
                    ax.scatter(g.age, g.value, s=5, alpha=0.30 if lab == "normal" else 0.55,
                               c=LABEL_COLORS.get(lab, "gray"), label=lab, zorder=1 if lab == "normal" else 2)
        c = curve_by_sex[curve_by_sex.sex == sex].sort_values("age")
        if len(c):
            plot_curve(c, ax=ax, color="#111111")
        if ylo is not None:
            ax.set_ylim(ylo, yhi)
        ax.set_title(f"{sex}"); ax.set_xlabel("age (years)"); ax.grid(alpha=0.2)
    axes[0].set_ylabel(feature)
    fig.suptitle(f"{feature} — {region}")
    axes[1].legend(fontsize=7, markerscale=2, loc="best")
    fig.tight_layout()
    if out:
        fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
    return fig
