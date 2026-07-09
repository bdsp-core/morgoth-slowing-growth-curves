"""Is the NULL severity correlation our score's fault, or the adjective's?

scripts/86 leaves severity at rho ~= 0.05 (n.s.) after fixing the max-statistic, the negation-blind adjective
extractor, the whole-head-vs-focal mismatch, the sleep confound, AND the borrowed-report pairing (scripts/88).
Two hypotheses remain:

  H1  our score is the wrong quantitative axis  -> some other feature/statistic should track the adjective.
  H2  the reader's adjective is not a quantitative measurement -> NOTHING tracks it.

Sweep 7 features x 4 statistics x {raw, age/stage-normalised z}, within generalized-only and focal-only
strata, on cleanly-paired recordings in W/N1 only.

The decisive contrast is RAW vs Z. A clinician does not age-normalise; "moderate diffuse slowing" is judged
against an absolute expectation. If RAW tracks the adjective better than Z does, that is not a failure of the
normative model -- it is direct evidence for this paper's central claim (the reader conflates age-appropriate
slowing with pathology, and the normative model is what separates them).

Run: PYTHONPATH=src python scripts/89_severity_axis_sweep.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import importlib.util

spec = importlib.util.spec_from_file_location("m86", "scripts/86_recalibrate_severity.py")
m86 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m86)

FEATS = ["low_freq_rel", "rel_delta", "rel_theta", "log_delta", "DAR", "TAR", "DTR"]
STATS = {"mean": np.nanmean, "median": np.nanmedian,
         "p90": lambda x: np.nanpercentile(x, 90), "p99": lambda x: np.nanpercentile(x, 99)}
ALERT, GEN = ["W", "N1"], "whole_head"
FOC = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
GRID = np.linspace(0, 100, 51)


def zref(seg, f):
    """mu(age), sd(age) over clean-normal segments, per (region, stage); Gaussian age kernel bw=5y."""
    mu = np.full(len(seg), np.nan); sd = np.full(len(seg), np.nan)
    nz = seg[seg.clean_normal == True]
    for (rg, st), g in nz.groupby(["region", "stage"], observed=True):
        a, v = g.age.values, g[f].values
        ok = np.isfinite(a) & np.isfinite(v); a, v = a[ok], v[ok]
        if len(a) < 200: continue
        ms, ss = [], []
        for g0 in GRID:
            w = np.exp(-0.5 * ((a - g0) / 5.0) ** 2); sw = w.sum()
            if sw < 50: ms.append(np.nan); ss.append(np.nan); continue
            m = (w * v).sum() / sw
            ms.append(m); ss.append(np.sqrt(max((w * (v - m) ** 2).sum() / sw, 1e-9)))
        k = ((seg.region == rg) & (seg.stage == st)).values
        mu[k] = np.interp(seg.age.values[k], GRID, ms); sd[k] = np.interp(seg.age.values[k], GRID, ss)
    return (seg[f].values - mu) / sd


def main():
    seg = pd.read_parquet("data/derived/segment_features.parquet")
    stg = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    abn = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([stg, abn], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "is_abnormal", "has_focal_slow", "has_gen_slow"]].drop_duplicates("bdsp_id")

    seg = seg[seg.region.isin([GEN] + FOC)].merge(stages, on=["bdsp_id", "segment"], how="inner")
    seg = seg[seg.stage.isin(ALERT)].merge(lu, on="bdsp_id", how="inner")
    seg = seg[seg.age.between(0, 100)]
    print(f"alert segments: {len(seg):,} over {seg.bdsp_id.nunique():,} recordings")

    for f in FEATS:
        seg["z_" + f] = zref(seg, f)

    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype=str).drop_duplicates("bdsp_id")
    meta["date"] = meta.eeg_datetime.astype(str).str[:8]
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]]
    rep = m86.report_ordinals()

    rows = []
    for scale in ("raw", "z"):
        for f in FEATS:
            col = f if scale == "raw" else "z_" + f
            wh = seg[seg.region == GEN].groupby("bdsp_id")[col]
            fo = seg[seg.region.isin(FOC)].groupby(["bdsp_id", "region"])[col]
            for sname, fn in STATS.items():
                g = wh.apply(fn).rename("gen").reset_index()
                fr = fo.apply(fn).reset_index().rename(columns={col: "v"})
                fb = fr.loc[fr.groupby("bdsp_id").v.idxmax()][["bdsp_id", "v"]].rename(columns={"v": "foc"})
                sc = g.merge(fb, on="bdsp_id", how="left").merge(lu, on="bdsp_id", how="left")
                sc = sc.merge(meta[["bdsp_id", "date"]], on="bdsp_id", how="left").merge(cp, on="bdsp_id", how="left")
                d = sc[sc.clean_pair == True].merge(rep, on=["bdsp_id", "date"], how="inner").dropna(subset=["rep_sev"])
                for stratum, sub, vc in [
                        ("generalized", d[(d.has_gen_slow == 1) & (d.has_focal_slow != 1)], "gen"),
                        ("focal", d[d.has_focal_slow == 1], "foc"),
                        ("all", d, "gen")]:
                    s2 = sub.dropna(subset=[vc])
                    if len(s2) < 40: continue
                    rho, p = spearmanr(s2[vc], s2.rep_sev)
                    rows.append(dict(scale=scale, feature=f, stat=sname, stratum=stratum,
                                     rho=rho, p=p, n=len(s2)))

    R = pd.DataFrame(rows)
    R["absrho"] = R.rho.abs()
    Path("results").mkdir(exist_ok=True)
    R.sort_values("absrho", ascending=False).to_csv("results/severity_axis_sweep.csv", index=False)

    out = ["# Severity axis sweep — is the null our score, or the adjective?\n",
           f"{len(R)} combinations: {len(FEATS)} features x {len(STATS)} statistics x "
           f"{{raw, z}} x {{generalized, focal, all}}, cleanly-paired recordings, W/N1 only.\n"]
    out.append(f"**Largest |rho| anywhere in the sweep: {R.absrho.max():.3f}**\n")
    out.append("## Best 12 combinations\n")
    out.append("| scale | feature | stat | stratum | rho | p | n |"); out.append("|---|---|---|---|---|---|---|")
    for _, r in R.sort_values("absrho", ascending=False).head(12).iterrows():
        out.append(f"| {r.scale} | {r.feature} | {r['stat']} | {r.stratum} | {r.rho:.3f} | {r.p:.1e} | {int(r.n)} |")

    out.append("\n## RAW vs Z (the decisive contrast)\n")
    out.append("| stratum | best |rho| RAW | best |rho| Z |"); out.append("|---|---|---|")
    for st in ["generalized", "focal", "all"]:
        a = R[(R.stratum == st) & (R.scale == "raw")].absrho.max()
        b = R[(R.stratum == st) & (R.scale == "z")].absrho.max()
        out.append(f"| {st} | {a:.3f} | {b:.3f} |")
    txt = "\n".join(out) + "\n"
    Path("results/severity_axis_sweep.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
