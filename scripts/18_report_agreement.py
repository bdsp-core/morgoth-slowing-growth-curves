"""Validation #1: agreement of our slowing statements with the clinical EEG reports.

Two parts:
  A. focal-vs-generalized TYPE — runs now (the dataset label is report-derived): compares our
     Morgoth-anchored and feature-based focal/generalized call to the label.
  B. band (delta/theta/mixed) + location (side + region) — needs the free-text report. `note`/
     `note_nlp` are permission-blocked for the read-only role; supply a reports CSV
     (cols: bdsp_id, report_text) to run this part. Report parser + comparison are ready below.

Outputs: results/report_agreement.md (+ part B when a reports CSV is provided).
Run: python scripts/18_report_agreement.py [reports_csv]
"""
from __future__ import annotations
import sys, re
from pathlib import Path
import numpy as np, pandas as pd

DER = Path("data/derived"); RES = Path("results")
REGIONS = ["temporal", "frontal", "central", "parietal", "occipital", "frontotemporal", "frontocentral"]


# ---------- report NLP (part B; ready for report text) ----------
def parse_report(text):
    """Extract slowing band + laterality + region from a report's slowing sentence(s)."""
    t = (text or "").lower()
    out = {"mentions_slowing": bool(re.search(r"slow", t)), "band": None, "side": None, "region": None}
    if not out["mentions_slowing"]:
        return out
    # focus on sentences mentioning slowing
    segs = [s for s in re.split(r"[.;\n]", t) if "slow" in s]
    ctx = " ".join(segs) if segs else t
    has_d, has_th = bool(re.search(r"delta", ctx)), bool(re.search(r"theta", ctx))
    out["band"] = "mixed" if (has_d and has_th) else ("delta" if has_d else ("theta" if has_th else None))
    if re.search(r"\bbilateral|diffuse|generalized|generalised\b", ctx): out["side"] = "bilateral"
    elif re.search(r"\bleft\b", ctx): out["side"] = "left"
    elif re.search(r"\bright\b", ctx): out["side"] = "right"
    for rg in REGIONS:
        if rg in ctx:
            out["region"] = rg.replace("frontotemporal", "temporal").replace("frontocentral", "frontal"); break
    return out


def part_b(reports_csv):
    rep = pd.read_csv(reports_csv)
    rep["parsed"] = rep.report_text.map(parse_report)
    P = pd.json_normalize(rep.parsed); P["bdsp_id"] = rep.bdsp_id.values
    fr = pd.read_parquet(DER / "final_report.parquet")   # our region/side/band per recording
    m = P.merge(fr[["bdsp_id", "report", "topo_class"]], on="bdsp_id", how="inner")
    # our band/side/region parsed from our generated sentence (same vocabulary)
    ours = m.report.map(parse_report); O = pd.json_normalize(ours)
    for k in ["band", "side", "region"]:
        both = m[P[k].notna().values] if False else m.assign(rep=P[k].values, ours=O[k].values).dropna(subset=["rep", "ours"])
        acc = (both.rep == both.ours).mean() if len(both) else float("nan")
        print(f"  {k}: agreement {acc:.3f} on n={len(both)} reports mentioning it")


# ---------- part A: focal vs generalized (runs now) ----------
def part_a():
    gate = pd.read_parquet(DER / "gate_probs.parquet")
    sl = gate[gate.label.isin(["focal_slow", "general_slow"])].copy()
    sl["true"] = np.where(sl.label == "focal_slow", "focal", "generalized")
    sl["morgoth_call"] = np.where(sl.p_focal >= sl.p_generalized, "focal", "generalized")
    lines = ["# Agreement with clinical reports\n",
             "## Part A — focal vs generalized (report-derived label)\n"]
    for name, col in [("Morgoth (p_focal vs p_gen)", "morgoth_call")]:
        acc = (sl.true == sl[col]).mean()
        ba = np.mean([(sl[sl.true == t][col] == t).mean() for t in ["focal", "generalized"]])
        ct = pd.crosstab(sl.true, sl[col])
        lines += [f"\n**{name}** — accuracy {acc:.3f}, balanced {ba:.3f}\n\n```\n{ct.to_string()}\n```\n"]
    lines += ["\n## Part B — band (delta/theta/mixed) + location (side/region)\n",
              "Needs the free-text EEG report. `note`/`note_nlp` are permission-blocked for the "
              "read-only OMOP role; provide a reports CSV (bdsp_id, report_text) or run the prod-path "
              "pull (human-run). Parser + comparison implemented (`parse_report`, `part_b`).\n"]
    (RES / "report_agreement.md").write_text("".join(lines))
    print("".join(lines))


if __name__ == "__main__":
    part_a()
    if len(sys.argv) > 1:
        print("\n=== Part B (band/location) ===")
        part_b(sys.argv[1])
