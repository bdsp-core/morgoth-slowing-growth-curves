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
VANPUTTEN = "#9aa0a6"    # van Putten qEEG indices (grey)

# --- data classes ---
NORMAL = "#31a354"       # clean-normal reference (green = healthy)
ABNORMAL = "#c8443c"     # report-slowing / abnormal (brick red)

CHANCE = "#bbbbbb"       # diagonal / chance reference lines


# --- sleep stages -------------------------------------------------------------------------------------
# ONE mapping for the five stages, everywhere. Figure 1A and Figure S5 used to disagree completely --
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
TOPO = {"anterior": "#a6761d", "posterior": "#386cb0", "unspec": NEUTRAL}


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
