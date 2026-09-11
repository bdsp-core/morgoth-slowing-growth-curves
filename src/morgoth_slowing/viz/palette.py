"""Canonical figure palette — ONE colour per entity across every manuscript figure.

Import from here (do not hard-code hexes in figure scripts) so the same thing is always the same colour:
methods are the purple/orange/blue triad; data classes are green (normal) / red (abnormal); grey is for
reference operating points (experts, van Putten). Chosen to be colour-blind-distinguishable.
"""
# --- methods / detectors ---
MORGOTH = "#6a3d9a"      # Morgoth foundation-model gate (purple)
OURS = "#e6550d"         # our Morgoth-free deviation detector (orange)
OURS_ALT = "#fd8d3c"     # a second "ours" variant, when two must be shown (light orange — still clearly "ours")
SCORE_AI = "#2c7fb8"     # SCORE-AI (blue)

# --- reference operating points ---
EXPERTS = "#8c8c8c"      # individual expert points (grey)
VANPUTTEN = "#8c510a"    # van Putten qEEG indices (dark ochre). NOT grey: in Figure S7 the index
                         # curve and the expert operating points shared one axes and one grey, so the
                         # method and the humans were indistinguishable inside the same panel.

# --- data classes ---
NORMAL = "#31a354"       # clean-normal reference (green = healthy)
ABNORMAL = "#99000d"     # report-slowing / abnormal (deep crimson). Deliberately NOT the brick red
                         # it used to be: that sat next to the LENS orange above and the two read as
                         # one colour across the manuscript even though they never share a figure.

CHANCE = "#bbbbbb"       # diagonal / chance reference lines


# --- sleep stages -------------------------------------------------------------------------------------
# ONE mapping for the five stages, everywhere. Figure 1A and Figure S4 used to disagree completely --
# W was yellow in one and dark blue in the other, N3 navy in one and red in the other -- so a reader who
# learned either mapping was actively misled by the other. Ordered light-to-dark with depth, REM set apart.
STAGE = {"W": "#E8B800", "N1": "#5FB0D0", "N2": "#4488FF", "N3": "#00008B", "REM": "#A040A0"}
STAGE_ORDER = ("W", "N1", "N2", "N3", "REM")


def stage_colors(stages=STAGE_ORDER):
    """Colours for a stage sequence, in the caller's order."""
    return [STAGE[s] for s in stages]


# --- one hue, one concept ------------------------------------------------------------------------------
# The figure review found red carrying eight meanings across the set and blue nearly as many: red was
# "left hemisphere" in one panel, "report slowing" in the next, "delta band" in a third and "anterior" in a
# fourth, so a reader who learned the encoding from Figure 6 misread Figure 7. The fix is not a nicer
# palette, it is a REGISTRY: every concept that gets a colour anywhere gets it here, once, and the families
# below never share a hue.
#
# Reserved above and not reused for anything else:
#   MORGOTH purple · OURS orange (LENS) · SCORE_AI blue · EXPERTS/CHANCE grey · ABNORMAL brick
#
# Rule of thumb before adding to this file: if the x-axis already names the categories, do not encode them
# in colour at all -- use NEUTRAL and let the axis do the work.

NEUTRAL = "#8c8c8c"      # clean-normal / reference / "the other group" -- the SAME grey everywhere

# bands (delta vs theta). Never the method hues, never the laterality hues.
BAND = {"delta": ABNORMAL, "theta": "#1b9e77", "mixed": NEUTRAL}

# laterality. Anatomy, not pathology -- deliberately outside the warm/cool axis used for bands.
SIDE = {"left": "#762a83", "bilateral": NEUTRAL, "right": "#1b7837"}

# anterior/posterior topography.
# NOT the stage blues: a reader meets gold=W / blue=N2 across ~20 panels of Figures 1A and S5, and
# S8B follows immediately -- reusing those hues for anterior/posterior invites a false association.
TOPO = {"anterior": "#a6761d", "posterior": "#5e3c99", "unspec": NEUTRAL}


def band_colors(keys):
    return [BAND[k] for k in keys]


def side_colors(keys):
    return [SIDE[k] for k in keys]


def topo_colors(keys):
    return [TOPO[k] for k in keys]


# --- one display name per quantity ----------------------------------------------------------------------
# The same measure appeared as "Relative delta (δ / total)", "rel_delta" and "relative delta" on three axes
# of the same paper, and the theta/alpha ratio as "TAR", "log TAR" and "theta/alpha ratio". Column names are
# not display names; look the display name up here.
FEATURE_LABEL = {
    "rel_delta":    "relative delta (δ / total)",
    "rel_theta":    "relative theta (θ / total)",
    "rel_alpha":    "relative alpha (α / total)",
    "TAR":          "theta/alpha ratio (TAR)",
    "DAR":          "delta/alpha ratio (DAR)",
    "DTR":          "delta/theta ratio (DTR)",
    "log_delta":    "delta excess (log δ)",
    "log_theta":    "theta excess (log θ)",
    "log_TAR":      "theta/alpha ratio (TAR)",
    "log_DAR":      "delta/alpha ratio (DAR)",
    "low_freq_rel": "low-frequency relative power",
}


# --- one style for the ROC/PRC family ------------------------------------------------------------------
# Figures 2, 3, S3 and S7 plot the same 0-1 space and are read against each other, but were drawn with two
# tick sets, two decimal conventions (x at 2 dp against y at 1 dp in the same panel), three type sizes and
# two title cases. Everything that makes them comparable lives here.
ROC_TICKS = (0.0, 0.25, 0.50, 0.75, 1.0)
PANEL_PT = 10          # panel letters: one size, everywhere
TITLE_PT = 9.5
LABEL_PT = 8.5
TICK_PT = 7.5
LEGEND_PT = 7.0        # Elsevier's 7 pt floor applies at PRINTED size; at 6.5 the Figure S7 legend printed
                       # at 6.84 pt. The ROC figures print at ~1.0-1.1x, so 7.0 authored clears it.


def style_roc(ax, xlabel="1 \u2212 specificity", ylabel="sensitivity"):
    """Apply the shared ROC/PRC axis style. Square, same ticks, same decimals, same type."""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
    ax.set_xticks(ROC_TICKS); ax.set_yticks(ROC_TICKS)
    ax.set_xticklabels([f"{t:.2f}" for t in ROC_TICKS])
    ax.set_yticklabels([f"{t:.2f}" for t in ROC_TICKS])
    ax.tick_params(labelsize=TICK_PT)
    ax.set_xlabel(xlabel, fontsize=LABEL_PT); ax.set_ylabel(ylabel, fontsize=LABEL_PT)


def panel_letter(ax, i, dx=-0.16, dy=1.02):
    """One panel-letter convention for the whole set: bold, PANEL_PT, top-left, outside the axes."""
    ax.text(dx, dy, "ABCDEFGHIJKLMNO"[i], transform=ax.transAxes, fontsize=PANEL_PT,
            fontweight="bold", va="bottom", ha="left")


def flabel(key: str) -> str:
    """Display name for a feature column. Unknown keys pass through, so a new feature is visible, not silent."""
    return FEATURE_LABEL.get(key, key)


# --- shared publication style (Tufte-leaning) ---------------------------------------------------------------
# Applied once at import so every figure script that imports this module inherits the same look: no top/right
# spines (drop the box), frameless legends, thin axes, and one consistent font ladder. Individual scripts can
# still override locally, and call despine()/despine_all() for axes that need extra treatment.
_PUB_RC = {
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "axes.titleweight": "normal",
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
    "font.size": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.fontsize": 9,
    "legend.frameon": False,
    "axes.grid": False,
}


def set_pub_style():
    import matplotlib as mpl
    mpl.rcParams.update(_PUB_RC)


def despine(ax, which=("top", "right")):
    """Hide the named spines on one Axes (use for axes made before rcParams applies, e.g. mne/twin axes)."""
    for s in which:
        if s in ax.spines:
            ax.spines[s].set_visible(False)


def despine_all(fig):
    for ax in fig.get_axes():
        despine(ax)


set_pub_style()


# --- journal artwork: a vector twin of every committed figure panel ------------------------------------
# Elsevier asks for line art at 1000 dpi (TIFF) or as vector (EPS/PDF), and our panels are committed as
# 300-dpi PNGs. Upsampling those to 1000 dpi would invent pixels, not detail. So, when MORGOTH_VECTOR_DIR is
# set, every PNG a figure script saves under figures/ is ALSO saved as a vector PDF at the same geometry
# (same bbox_inches) under that directory, and scripts/export_journal_figures.py composes and rasterizes from
# those. Unset -- the normal case -- this does nothing, so committed outputs are untouched.
def _install_vector_twin():
    import os
    from pathlib import Path
    out = os.environ.get("MORGOTH_VECTOR_DIR")
    if not out:
        return
    import matplotlib as mpl
    from matplotlib.figure import Figure
    # TrueType (Type 42), not matplotlib's default Type 3: production systems re-flow Type 3 glyphs badly,
    # and Elsevier asks that fonts be embedded. It also keeps font sizes readable by the size check.
    mpl.rcParams["pdf.fonttype"] = 42
    if getattr(Figure.savefig, "_vector_twin", False):
        return
    orig = Figure.savefig

    def savefig(self, fname, *args, **kwargs):
        res = orig(self, fname, *args, **kwargs)
        p = Path(os.fspath(fname)) if isinstance(fname, (str, os.PathLike)) else None
        if p is not None and p.suffix.lower() == ".png" and "figures" in p.parts:
            rel = Path(*p.parts[p.parts.index("figures"):]).with_suffix(".pdf")
            dst = Path(out) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            kw = {k: v for k, v in kwargs.items() if k not in ("dpi", "format", "pil_kwargs")}
            # dpi matters in a PDF only for artists drawn with rasterized=True (the dense scatter clouds in
            # scripts/111 and 57). Left at the default it is figure.dpi = 100, which would embed those at 100 dpi
            # inside an otherwise vector file.
            orig(self, dst, *args, dpi=1200, **kw)
        return res
    savefig._vector_twin = True
    Figure.savefig = savefig


_install_vector_twin()
