"""Set the operating points that minimise "flag for review", PER BRANCH (docs/description_architecture.md §1d).

Morgoth gates; our descriptors DESCRIBE (they do not re-detect). A flag is a genuine CONTRADICTION, and we
separate a data limitation from a disagreement with three outcomes per branch:

  agree / quantify        gate fires, we measure slowing            (normal operation)
  quantification-limited  gate fires, we measure nothing, but the recording is WAKE-ONLY (no sleep staged) --
                          slowing is subtle in alert wake, so this is a data limitation, NOT a flag
  FLAG                    case 1  (we measure MARKED slowing, gate silent)  OR
                          case 2b (gate fires, we measure nothing, WITH sleep coverage: real contradiction)

Descriptor cutoffs are held at principled values; only the gate cutoff tau_M is swept. Branch-appropriate:
generalized uses whole-head amount/prevalence; focal uses the max lobar excess E.

Run: PYTHONPATH=src python scripts/112_operating_points.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd


def main():
    g = pd.read_parquet("data/derived/gate_probs.parquet").set_index("bdsp_id")
    D = pd.read_parquet("data/derived/description_descriptors.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id").set_index("bdsp_id")

    cov = D.groupby("bdsp_id").agg(amt=("amount_median", "max"), prev=("prevalence", "max"),
                                   E=("focal_excess", "max"),
                                   has_sleep=("stage", lambda x: bool(set(x) & {"N1", "N2", "N3", "REM"})))
    J = g[["p_focal", "p_generalized"]].join(cov).join(lu).dropna(subset=["p_focal"])
    J["has_sleep"] = J.has_sleep.fillna(False).astype(bool)
    J["E"] = J.E.fillna(0.0)

    branches = [("generalized", "p_generalized", J.amt > 3.0, (J.amt <= 0) & (J.prev < 0.05),
                 (J.gen_class == "pathologic").astype(int)),
                ("focal", "p_focal", J.E > 3.0, J.E < 1.0,
                 (J.has_focal_slow == 1).astype(int))]

    lines = ["# Operating points, per branch — flag-for-review\n",
             f"n = {len(J):,}. Three outcomes per branch, so a data limitation is not scored as a disagreement:",
             "",
             "- **agree / quantify** — gate fires, we measure slowing (normal operation)",
             "- **quantification-limited** — gate fires, we measure nothing, but the recording is WAKE-ONLY "
             "(no sleep staged); slowing is subtle in alert wake, so this is a data limitation, NOT a flag",
             "- **FLAG** — case 1 (we measure MARKED slowing, gate silent) OR case 2b (gate fires, we measure "
             "nothing, WITH sleep coverage: a genuine contradiction)"]
    for name, pcol, marked, absent, report in branches:
        lines += [f"\n## {name}\n",
                  "| gate tau | % gated | case 1 (marked, silent) | quant-limited (wake-only) | "
                  "case 2b (FLAG: has sleep, nothing) | true flag | gate sens vs report |",
                  "|---|---|---|---|---|---|---|"]
        for t in np.round(np.arange(0.30, 0.86, 0.05), 2):
            gate = J[pcol] >= t
            c1 = marked & ~gate
            ag = gate & absent
            ql = ag & ~J.has_sleep
            c2b = ag & J.has_sleep
            flag = c1 | c2b
            se = gate[report == 1].mean()
            lines.append(f"| {t:.2f} | {gate.mean():.1%} | {c1.mean():.2%} | {ql.mean():.2%} | "
                         f"{c2b.mean():.2%} | **{flag.mean():.2%}** | {se:.2f} |")
    txt = "\n".join(lines) + "\n"
    Path("results/operating_points.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
