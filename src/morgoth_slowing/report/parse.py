"""Report NLP — parse a clinical EEG report's slowing sentence(s) for band / side / region.

Lifted from the legacy `scripts/18_report_agreement.py` so the pre-fleet label builder (`scripts/20`)
does not import an archived script by file path. `scripts/20` overrides side/region/band with its v2
clause-scoped extractor; `parse_report` remains the base (mentions_slowing + initial band).
"""
from __future__ import annotations
import re

REGIONS = ["temporal", "frontal", "central", "parietal", "occipital", "frontotemporal", "frontocentral"]


def parse_report(text):
    """Extract slowing band + laterality + region from a report's slowing sentence(s)."""
    t = (text or "").lower()
    out = {"mentions_slowing": bool(re.search(r"slow", t)), "band": None, "side": None, "region": None}
    if not out["mentions_slowing"]:
        return out
    segs = [s for s in re.split(r"[.;\n]", t) if "slow" in s]
    ctx = " ".join(segs) if segs else t
    has_d, has_th = bool(re.search(r"delta", ctx)), bool(re.search(r"theta", ctx))
    out["band"] = "mixed" if (has_d and has_th) else ("delta" if has_d else ("theta" if has_th else None))
    if re.search(r"\bbilateral|diffuse|generalized|generalised\b", ctx):
        out["side"] = "bilateral"
    elif re.search(r"\bleft\b", ctx):
        out["side"] = "left"
    elif re.search(r"\bright\b", ctx):
        out["side"] = "right"
    for rg in REGIONS:
        if rg in ctx:
            out["region"] = rg.replace("frontotemporal", "temporal").replace("frontocentral", "frontal")
            break
    return out
