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
