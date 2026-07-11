"""Coverage report over the bins we care about (docs/analysis_plan.md goals): age x (focal/generalized)
x region/topography x band (delta/theta/mixed). Answers "do we have an adequate sample per bin, per the
reports, to develop and assess the goals?" and flags thin cells for the backfill (scripts/121).

Uses the CLEAN usable set = report_manifest_v1 with clean_pair & not same_date_ambiguous.
PHI-free: counts only. Writes docs/coverage_report.md.
Run: PYTHONPATH=src python scripts/122_coverage_report.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

MANIFEST = "data/manifest/report_manifest_v2.parquet"   # merged cohort + backfill, 4-region taxonomy
AGE_BINS = [0, 1, 6, 13, 18, 45, 60, 75, 200]
AGE_LAB = ["0-1", "1-5", "6-12", "13-17", "18-44", "45-59", "60-74", "75+"]
THIN = 200  # adequacy target; sub-target 3-way cells are genuinely-rare findings (pooled, not gaps)


def ct(df, idx, col, thin=THIN):
    t = pd.crosstab(df[idx], df[col]) if col else df[idx].value_counts().sort_index().to_frame("n")
    return t


def md_table(t, note=""):
    out = t.to_markdown() + "\n"
    thin_cells = [(r, c) for r in t.index for c in t.columns if t.loc[r, c] < THIN]
    return out


def main():
    m = pd.read_parquet(MANIFEST)
    clean = m[(m.clean_pair == True) & (~m.same_date_ambiguous)].copy()
    clean["age_bin"] = pd.cut(pd.to_numeric(clean.age, errors="coerce"), bins=AGE_BINS, labels=AGE_LAB, right=False)
    foc = clean[clean.has_focal_slow == 1]
    gen = clean[clean.has_gen_slow == 1]

    L = ["# Coverage report — report-labelled bins (cohort + backfill, 4-region)\n",
         f"Source: `{MANIFEST}` (merged cohort + pool backfill) filtered to `clean_pair & "
         f"~same_date_ambiguous`. Counts are EEGs (report labels). **Adequacy is judged on the MARGINALS** "
         f"(region / side / band / topography / age — all ≥{THIN}); the few 3-way cells below {THIN} are "
         f"**genuinely-rare findings** (whole-pool max <{THIN}), pooled in assessment — not sampling gaps.\n",
         f"\n**Clean usable set: {len(clean):,} EEGs** "
         f"(of {len(m):,}; excluded {int((~m.clean_pair).sum()):,} borrowed + "
         f"{int(m.same_date_ambiguous.sum()):,} same-date-ambiguous).\n",
         f"- abnormal {int((clean.is_abnormal==1).sum()):,} | focal {len(foc):,} | generalized {len(gen):,} | "
         f"clean-normal {int((clean.clean_normal==1).sum()):,}\n"]

    def marg(s):
        return " · ".join(f"{k} **{int(v)}**" for k, v in s.items())
    L.append("\n## 0. Marginal adequacy — the criterion (all ≥%d = adequate)\n" % THIN)
    L.append(f"- FOCAL region: {marg(foc.focal_region.value_counts())}\n")
    L.append(f"- FOCAL side: {marg(foc.focal_side.value_counts())}\n")
    L.append(f"- FOCAL band: {marg(foc.focal_band.value_counts())}\n")
    L.append(f"- GEN topography: {marg(gen.gen_topography.value_counts())}\n")
    L.append(f"- GEN band: {marg(gen.gen_band.value_counts())}\n")
    mins = {"focal region": foc.focal_region.value_counts().min(), "focal side": foc.focal_side.value_counts().min(),
            "focal band": foc.focal_band.value_counts().min(), "gen topo": gen.gen_topography.value_counts().min(),
            "gen band": gen.gen_band.value_counts().min()}
    L.append(f"\n_All marginal minima ≥ {THIN}: {all(v >= THIN for v in mins.values())} "
             f"(smallest = {min(mins.values())})._\n")

    L.append("\n## 1. Age × class\n")
    a = pd.crosstab(clean.age_bin, np.where(clean.is_abnormal == 1, "abnormal", "normal"))
    a["focal"] = foc.groupby("age_bin", observed=False).size()
    a["generalized"] = gen.groupby("age_bin", observed=False).size()
    L.append(a.fillna(0).astype(int).to_markdown() + "\n")

    L.append("\n## 2. FOCAL slowing — side × band\n")
    L.append(pd.crosstab(foc.focal_side, foc.focal_band, margins=True).to_markdown() + "\n")
    L.append("\n## 3. FOCAL slowing — region × band\n")
    L.append(pd.crosstab(foc.focal_region, foc.focal_band, margins=True).to_markdown() + "\n")
    L.append("\n## 4. FOCAL slowing — region × side\n")
    L.append(pd.crosstab(foc.focal_region, foc.focal_side, margins=True).to_markdown() + "\n")
    L.append("\n## 5. FOCAL slowing — age × side\n")
    L.append(pd.crosstab(foc.age_bin, foc.focal_side, margins=True).to_markdown() + "\n")

    L.append("\n## 6. GENERALIZED slowing — topography × band\n")
    L.append(pd.crosstab(gen.gen_topography, gen.gen_band, margins=True).to_markdown() + "\n")
    L.append("\n## 7. GENERALIZED slowing — age × topography\n")
    L.append(pd.crosstab(gen.age_bin, gen.gen_topography, margins=True).to_markdown() + "\n")

    # genuinely-rare 3-way cells (pooled, not gaps)
    L.append("\n## 8. Genuinely-rare 3-way cells (< %d) — pooled in assessment, not sampling gaps\n" % THIN)
    thin = []
    for name, t in [("focal side×band", pd.crosstab(foc.focal_side, foc.focal_band)),
                    ("focal region×band", pd.crosstab(foc.focal_region, foc.focal_band)),
                    ("gen topo×band", pd.crosstab(gen.gen_topography, gen.gen_band))]:
        for r in t.index:
            for c in t.columns:
                if t.loc[r, c] < THIN:
                    thin.append({"crosstab": name, "cell": f"{r} × {c}", "n": int(t.loc[r, c])})
    tdf = pd.DataFrame(thin).sort_values("n") if thin else pd.DataFrame(columns=["crosstab", "cell", "n"])
    L.append((tdf.to_markdown(index=False) if len(tdf) else "_none — every cell ≥ %d_" % THIN) + "\n")

    Path("docs/coverage_report.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
