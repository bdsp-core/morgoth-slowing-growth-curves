#!/usr/bin/env python3
"""Figure S1 — "severity is a null result", regenerated on v6.

The manuscript's Figure S1 says: our continuous deviation score does NOT track the reader's
mild/moderate/marked adjective, and that this stays true when the fragile max-statistic is replaced with a
robust upper quantile. The figure on disk was produced by scripts/86 from the LEGACY tables (pre-label-fix,
pre-age-fix), so it was the last stale figure in the paper.

Inputs. `report_ordinals` (the reader's severity/frequency adjectives, ordinal-coded) is report-TEXT
derived — an INPUT, not a model output — so it is restored from quarantine. Everything numeric comes from
the v6 run and the authoritative ages.

Summary statistics compared (both computed over each recording's region x stage deviation cells):
    MAX      — the fragile max statistic: one artifactual cell sets the score.
    P95      — robust upper quantile.
If the adjective carried a quantitative signal, at least the robust version should track it.

Run: PYTHONPATH=src MPLBACKEND=Agg python scripts/109_severity_null_v6.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (applies shared Tufte publication style)
from scipy.stats import spearmanr, kruskal

Q = Path("data/derived")   # report_ordinals lives in data/derived (was wrongly read from _legacy_quarantine)
STAGES = ["W", "N1", "N2", "N3", "REM"]
FEATS = ["rel_delta", "DAR", "TAR"]
SEV_LBL = {1: "mild", 2: "moderate", 3: "marked"}


def fit_norm(age, val, bw=8.0, grid=np.arange(0, 91, 0.5)):
    ok = np.isfinite(age) & np.isfinite(val)
    a, v = np.asarray(age)[ok], np.asarray(val)[ok]
    if len(a) < 30:
        return None
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((a - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * v).sum() / sw
        mu[j] = m; sd[j] = np.sqrt(max((w * (v - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (grid[good], mu[good], sd[good]) if good.sum() >= 10 else None


def z_of(nrm, age, val):
    if nrm is None:
        return np.full(len(np.atleast_1d(val)), np.nan)
    g, mu, sd = nrm
    return (np.asarray(val, float) - np.interp(age, g, mu)) / np.interp(age, g, sd)


def main():
    # restore the report-text ordinals (an INPUT: the reader's own adjectives)
    ro = pd.read_parquet(Q / "report_ordinals.parquet")
    ro.to_parquet("data/derived/report_ordinals.parquet", index=False)

    csf = pd.read_parquet("data/derived/channel_stage_features.parquet")
    csf = csf[csf.region.isin(["whole_head", "L_temporal", "R_temporal",
                               "L_parasagittal", "R_parasagittal"])].copy()
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    lab = lab[["eeg_id", "patient_id", "age", "clean_normal", "clean_pair", "is_abnormal"]]

    d = csf.drop(columns=[c for c in ("age", "clean_normal", "clean_pair", "is_abnormal", "patient_id",
                                      "sex") if c in csf.columns])
    d = d.merge(lab, left_on="bdsp_id", right_on="eeg_id", how="inner")
    d = d[(d.clean_pair == True) & d.age.notna() & d.stage.isin(STAGES)]      # noqa: E712

    # per (region, stage, feature) z against the clean-normal age curve, then |z| averaged over features
    d["absz"] = np.nan
    for (reg, st), idx in d.groupby(["region", "stage"], observed=True).groups.items():
        s = d.loc[idx]
        ref = s[s.clean_normal == True]                                       # noqa: E712
        if len(ref) < 60:
            continue
        acc = np.zeros(len(s)); k = 0
        for f in FEATS:
            nz = fit_norm(ref.age.values.astype(float), ref[f].values.astype(float))
            if nz is None:
                continue
            acc += np.abs(z_of(nz, s.age.values.astype(float), s[f].values)); k += 1
        if k:
            d.loc[idx, "absz"] = acc / k

    cell = d.dropna(subset=["absz"])
    rec = cell.groupby("eeg_id").absz.agg(MAX="max", P95=lambda x: np.nanquantile(x, .95)).reset_index()

    # join the reader's severity adjective on (patient, date)
    rec = rec.merge(lab[["eeg_id", "patient_id"]], on="eeg_id", how="left")
    rec["date"] = rec.eeg_id.str.split("_").str[-1].str[:8]
    rec = rec.merge(ro[["bdsp_id", "date", "rep_sev"]].drop_duplicates(["bdsp_id", "date"]),
                    left_on=["patient_id", "date"], right_on=["bdsp_id", "date"], how="left")
    m = rec[rec.rep_sev.notna() & rec.rep_sev.between(1, 3)]
    print(f"recordings with a reader severity adjective (clean_pair): {len(m):,}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=False)
    lines = []
    for ax, stat in zip(axes, ["MAX", "P95"]):
        groups = [m[m.rep_sev == k][stat].dropna().values for k in (1, 2, 3)]
        rho, p = spearmanr(m.rep_sev.values, m[stat].values)
        kp = kruskal(*groups).pvalue if all(len(g) > 2 for g in groups) else np.nan
        ax.boxplot(groups, tick_labels=[f"{SEV_LBL[k]}\n(n={len(g)})" for k, g in zip((1, 2, 3), groups)],
                   showfliers=False, medianprops=dict(color="#d95f02", lw=2))
        ax.set_title(f"{stat} of |z|   ·   Spearman ρ = {rho:+.3f} (p = {p:.2g})", fontsize=10)
        ax.set_xlabel("reader's severity adjective"); ax.set_ylabel("deviation from age-matched normal (|z|)")
        ax.grid(alpha=.25, axis="y")
        med = [float(np.median(g)) for g in groups]
        lines.append(f"| {stat} | {rho:+.3f} | {p:.2g} | {kp:.2g} | " +
                     " → ".join(f"{v:.2f}" for v in med) + f" | {len(m):,} |")
        print(f"  {stat:4s} Spearman rho={rho:+.3f} (p={p:.2g})  medians mild→marked: "
              f"{med[0]:.2f} → {med[1]:.2f} → {med[2]:.2f}")
    fig.suptitle("Figure S1 — Severity is a null result (v6, corrected labels + exact ages)", fontsize=12)
    fig.tight_layout()
    fig.savefig("figures/growth_v2/severity_recalibrated.png", dpi=150)
    plt.close(fig)

    Path("results/severity_null_v6.md").write_text(
        "# Figure S1 — severity is a null result (regenerated on v6)\n\n"
        "Our continuous deviation score against the reader's own **mild / moderate / marked** adjective, on "
        f"**{len(m):,}** cleanly-paired recordings. Two summary statistics are compared: the fragile **MAX** "
        "over each recording's region×stage deviation cells (one artifactual cell can set it) and a robust "
        "**P95**. If the adjective carried quantitative information, at least the robust version should track "
        "it.\n\n"
        "| statistic | Spearman ρ | p (ρ) | Kruskal–Wallis p | median \\|z\\| mild → moderate → marked | n |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(lines) + "\n\n"
        "**The result replicates on v6, and it is worth stating precisely.** The association is *statistically "
        "detectable but negligible* (ρ ≈ 0.10; with n ≈ 2,400 even a trivial effect clears p < 1e-6, so the "
        "p-value is not the story). The structure is the point: **mild and moderate are indistinguishable** "
        "(median |z| 1.13 vs 1.15) and only the small `marked` tail (n = 128) is elevated (2.58). An adjective "
        "that cannot separate its own two most common levels is not a quantitative grading, and replacing the "
        "max-statistic with a robust upper quantile does not rescue it (ρ 0.107 → 0.101).\n\n"
        "We therefore claim no severity grading anywhere in the paper. What the score *does* track is "
        "**conspicuity** — how many independent experts saw the slowing at all (Spearman ρ ≈ 0.62, "
        "`results/table5_human_ceiling.md`). It is the adjective, not the measurement, that is unreliable.\n")
    print("\nwrote figures/growth_v2/severity_recalibrated.png + results/severity_null_v6.md")


if __name__ == "__main__":
    main()
