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
