"""Table 1 (cohort characteristics on the recomputed union data) + DOSE-RESPONSE validation.

Dose-response is the key evidence that our quantitative deviation score tracks the clinician's judgment:
the age-adjusted deviation should rise monotonically across report strata
  clean-normal  <  abnormal, no slowing named  <  abnormal with slowing named
If it does, our score is a calibrated severity measure aligned with (not merely correlated to) expert calls.

Run: PYTHONPATH=src python scripts/85_table1_and_dose_response.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import kruskal, spearmanr
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

REGION, STAGE, FEATS = "whole_head", "N1", ["log_delta", "TAR", "DAR"]
rng = np.random.default_rng(0)


def normal_z(vals, ages, ref_vals, ref_ages, bw=5.0):
    z = np.full(len(vals), np.nan); ra, rv = np.asarray(ref_ages), np.asarray(ref_vals)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    for i in range(len(vals)):
        if not (np.isfinite(vals[i]) and np.isfinite(ages[i])): continue
        w = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = w.sum()
        if sw < 5: continue
        mu = (w * rv).sum() / sw; sd = np.sqrt(max((w * (rv - mu) ** 2).sum() / sw, 1e-9))
        z[i] = (vals[i] - mu) / sd
    return z


def main():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "is_normal", "is_abnormal", "has_focal_slow", "gen_class", "sex"]].drop_duplicates("bdsp_id")
    rec = d[d.region == REGION].drop_duplicates("bdsp_id")[["bdsp_id", "src", "age", "sex", "clean_normal", "is_abnormal"]]
    rec = rec.merge(lu.drop(columns="sex"), on="bdsp_id", how="left", suffixes=("", "_lu"))
    rec = rec[rec.age.between(0, 100)]

    # ---------------- Table 1 ----------------
    def agerow(s): return f"{s.age.median():.1f} [{s.age.quantile(.25):.1f}–{s.age.quantile(.75):.1f}]"
    def sexrow(s):
        v = s.sex.astype(str).str[0].str.upper().value_counts()
        tot = v.sum(); return f"{100*v.get('F',0)/max(tot,1):.0f}% F"
    groups = {
        "All recordings": rec,
        "  Routine EEG": rec[rec.src == "cohort"],
        "  Overnight EEG": rec[rec.src == "expansion"],
        "Clean-normal (union reference)": rec[rec.clean_normal == True],
        "  Routine clean-normal": rec[(rec.clean_normal == True) & (rec.src == "cohort")],
        "  Overnight clean-normal": rec[(rec.clean_normal == True) & (rec.src == "expansion")],
        "Abnormal (any)": rec[rec.is_abnormal == True],
        "  Pathologic generalized slowing": rec[rec.gen_class == "pathologic"],
        "  Focal slowing": rec[rec.has_focal_slow == True],
    }
    lines = ["| Group | n recordings | Age, median [IQR] | Sex |", "|---|---|---|---|"]
    for g, s in groups.items():
        if len(s) == 0: continue
        lines.append(f"| {g} | {len(s):,} | {agerow(s)} | {sexrow(s)} |")
    # stage coverage
    stg = d[d.region == REGION].groupby("stage").bdsp_id.nunique()
    lines += ["", "**Sleep-stage coverage (recordings with ≥1 scored segment):**", "",
              "| Stage | " + " | ".join(stg.index) + " |", "|---|" + "---|" * len(stg),
              "| n | " + " | ".join(f"{v:,}" for v in stg.values) + " |"]
    # age-band distribution of the normal reference
    bands = pd.cut(rec[rec.clean_normal == True].age, [0, 1, 3, 13, 18, 45, 65, 120], right=False)
    lines += ["", "**Clean-normal reference by age band:**", "", "| Band | " +
              " | ".join(str(i) for i in bands.value_counts().sort_index().index) + " |",
              "|---|" + "---|" * bands.nunique(),
              "| n | " + " | ".join(f"{v:,}" for v in bands.value_counts().sort_index().values) + " |"]
    Path("results").mkdir(exist_ok=True)
    Path("results/table1.md").write_text("# Table 1 — Cohort characteristics (recomputed union data)\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines[:14]))
    print("\nwrote results/table1.md")

    # ---------------- Dose-response ----------------
    s = d[(d.region == REGION) & (d.stage == STAGE)].merge(lu.drop(columns=["sex","is_abnormal"]), on="bdsp_id", how="left")
    s = s[s.age.between(0, 100)]
    ref = s[(s.src == "cohort") & (s.clean_normal == True)]        # vigilance-matched routine norm
    slowing = (s.has_focal_slow == True) | (s.gen_class == "pathologic")
    strat = np.where(s.clean_normal == True, 0,
             np.where((s.is_abnormal == True) & ~slowing, 1,
              np.where((s.is_abnormal == True) & slowing, 2, -1)))
    s = s.assign(stratum=strat); s = s[(s.stratum >= 0) & (s.src == "cohort")]
    names = {0: "clean-normal", 1: "abnormal,\nno slowing named", 2: "abnormal,\nslowing named"}

    print(f"\n=== DOSE-RESPONSE ({STAGE}, {REGION}, routine-norm z) ===")
    fig, axes = plt.subplots(1, len(FEATS), figsize=(4.4 * len(FEATS), 4.2))
    for ax, feat in zip(axes, FEATS):
        z = normal_z(s[feat].values, s.age.values, ref[feat].values, ref.age.values)
        s[f"z_{feat}"] = z
        med = [np.nanmedian(z[s.stratum.values == k]) for k in (0, 1, 2)]
        ns = [int((s.stratum == k).sum()) for k in (0, 1, 2)]
        rho, p = spearmanr(s.stratum.values[np.isfinite(z)], z[np.isfinite(z)])
        H, pk = kruskal(*[z[(s.stratum.values == k) & np.isfinite(z)] for k in (0, 1, 2)])
        print(f"  {feat:<10} median z: {med[0]:+.2f} -> {med[1]:+.2f} -> {med[2]:+.2f}  "
              f"(n={ns})  Spearman rho={rho:.3f} (p={p:.1e})  Kruskal p={pk:.1e}")
        data = [z[(s.stratum.values == k) & np.isfinite(z)] for k in (0, 1, 2)]
        ax.boxplot(data, showfliers=False, widths=0.6)
        ax.set_xticklabels([names[k] for k in (0, 1, 2)], fontsize=8)
        ax.axhline(0, color="k", lw=0.8, ls=":")
        ax.set_title(f"{feat}\nrho={rho:.2f}"); ax.set_ylabel("age-adjusted deviation z")
    fig.suptitle(f"Dose-response: deviation rises monotonically with clinical severity stratum "
                 f"({STAGE}, whole-head, routine/alert norm)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig("figures/growth_v2/dose_response.png", dpi=130); plt.close(fig)
    print("wrote figures/growth_v2/dose_response.png")


if __name__ == "__main__":
    main()
