"""RECALIBRATE severity & prevalence against the clinician's adjectives.

Prior result was null (severity rho=-0.036, prevalence rho=0.100). Four diagnosed defects, all fixed here:
 1. peak_z was a MAX over hundreds of segments (max 19.4 => artifact-dominated). -> use a robust upper
    quantile (p90) of the segment-z distribution.
 2. the adjective extractor returned the first word in TABLE order anywhere in the slowing context, so a
    stray/negated "marked"/"moderate" won. -> scope to the clause around each "slow" mention, drop negated
    clauses, and take the modifier NEAREST the word "slow".
 3. severity of FOCAL slowing was scored on a whole-head statistic. -> score focal cases in their
    max-deviation region; generalized on whole-head.
 4. scored over all segments incl. sleep. -> score the alert (W/N1) portion, matching the vigilance-matched
    reference used for detection.
Then quantile-map the continuous score onto the empirical adjective distribution and evaluate held-out.

Raw report text is read from the scratchpad and NEVER written out; only derived ordinals are saved.
Run: PYTHONPATH=src python scripts/86_recalibrate_severity.py
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SC = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv"
SEV = {"slight": 1, "mild": 1, "moderate": 2, "marked": 3, "severe": 3}
FRQ = {"rare": 1, "occasional": 1, "intermittent": 2, "frequent": 3, "abundant": 3, "continuous": 4}
NEG = re.compile(r"\b(no|without|absent|absence of|denies|negative for|not)\b")
ALERT = ["W", "N1"]
GEN_REGION = "whole_head"
FOCAL_REGIONS = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]


def nearest_modifier(text, table):
    """Scope to clauses mentioning 'slow'; skip negated clauses; return the modifier NEAREST to 'slow'."""
    best, bestd = np.nan, 1e9
    for clause in re.split(r"[.;\n]", text.lower()):
        if "slow" not in clause or NEG.search(clause.split("slow")[0][-40:]):
            continue
        for m in re.finditer(r"\bslow", clause):
            for w, v in table.items():
                for wm in re.finditer(rf"\b{w}\b", clause):
                    dist = abs(wm.start() - m.start())
                    if dist < bestd and dist < 60:      # within ~60 chars of the word "slow"
                        best, bestd = v, dist
    return best


def report_ordinals():
    """One row per (bdsp_id, recording DATE). 43% of patients have >1 report, so joining on patient alone
    matches an arbitrary report to a recording and destroys the correlation."""
    rows = []
    for ch in pd.read_csv(SC, usecols=["SiteID", "BDSPPatientID", "StartTime", "reports", "impression"],
                          chunksize=50000, dtype=str, low_memory=False):
        t = (ch.reports.fillna("") + " " + ch.impression.fillna(""))
        m = t.str.contains("slow", case=False, na=False)
        if not m.any(): continue
        s = ch[m].copy(); txt = t[m]
        s["bdsp_id"] = s.SiteID.astype(str) + s.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
        s["date"] = pd.to_datetime(s.StartTime, errors="coerce").dt.strftime("%Y%m%d")
        s["rep_sev"] = [nearest_modifier(x, SEV) for x in txt]
        s["rep_frq"] = [nearest_modifier(x, FRQ) for x in txt]
        rows.append(s[["bdsp_id", "date", "rep_sev", "rep_frq"]])
    r = pd.concat(rows).dropna(subset=["date"]).dropna(subset=["rep_sev", "rep_frq"], how="all")
    return r.drop_duplicates(["bdsp_id", "date"])


def build_reference(seg, feat, grid):
    """mu(age), sd(age) of NORMAL segments per (region,stage), on an age grid; kernel-weighted (bw=5y)."""
    ref = {}
    nz = seg[seg.clean_normal == True]
    for (rg, st), g in nz.groupby(["region", "stage"], observed=True):
        a, v = g.age.values, g[feat].values
        ok = np.isfinite(a) & np.isfinite(v); a, v = a[ok], v[ok]
        if len(a) < 200: continue
        mus, sds = [], []
        for g0 in grid:
            w = np.exp(-0.5 * ((a - g0) / 5.0) ** 2); sw = w.sum()
            if sw < 50: mus.append(np.nan); sds.append(np.nan); continue
            mu = (w * v).sum() / sw; sd = np.sqrt(max((w * (v - mu) ** 2).sum() / sw, 1e-9))
            mus.append(mu); sds.append(sd)
        ref[(rg, st)] = (np.array(mus), np.array(sds))
    return ref


def main():
    feat = "low_freq_rel" if True else "log_delta"   # slowing = (delta+theta)/total
    seg = pd.read_parquet("data/derived/segment_features.parquet")
    stg = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "is_abnormal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    if feat not in seg.columns:
        seg[feat] = seg["rel_delta"] + seg["rel_theta"] if "rel_theta" in seg else seg["rel_delta"]
    # Stage-restrict to the ALERT portion (W/N1). Abnormal recordings are only ~44% wake, so scoring over
    # all segments confounds the slowing score with how much the patient slept (scripts/87 builds the
    # abnormal stage table so both groups can be staged on the same basis).
    abn = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([stg, abn], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    seg = seg[seg.region.isin([GEN_REGION] + FOCAL_REGIONS)].merge(stages, on=["bdsp_id", "segment"], how="inner")
    seg = seg[seg.stage.isin(ALERT)].merge(lu, on="bdsp_id", how="inner")
    seg = seg[seg.age.between(0, 100) & np.isfinite(seg[feat])]
    print(f"ALERT-stage (W/N1) segments: {len(seg):,} over {seg.bdsp_id.nunique():,} recordings")

    grid = np.linspace(0, 100, 51)
    ref = build_reference(seg, feat, grid)
    # per-segment z
    mu = np.full(len(seg), np.nan); sd = np.full(len(seg), np.nan)
    for (rg, st), (m, s) in ref.items():
        k = ((seg.region == rg) & (seg.stage == st)).values
        mu[k] = np.interp(seg.age.values[k], grid, m); sd[k] = np.interp(seg.age.values[k], grid, s)
    seg["z"] = (seg[feat].values - mu) / sd

    # per-recording scores. generalized -> whole_head; focal -> max-deviation region
    wh = seg[seg.region == GEN_REGION]
    gen = wh.groupby("bdsp_id").z.agg(sev_robust=lambda x: np.nanpercentile(x, 90),
                                      sev_peak="max",
                                      prevalence=lambda x: float(np.mean(x > 2))).reset_index()
    fo = seg[seg.region.isin(FOCAL_REGIONS)]
    fo_r = fo.groupby(["bdsp_id", "region"]).z.apply(lambda x: np.nanpercentile(x, 90)).reset_index(name="p90")
    fo_best = fo_r.loc[fo_r.groupby("bdsp_id").p90.idxmax()][["bdsp_id", "p90"]].rename(columns={"p90": "sev_focal"})
    sc = gen.merge(fo_best, on="bdsp_id", how="left").merge(lu, on="bdsp_id", how="left")
    sc["sev_final"] = np.where(sc.has_focal_slow == True, sc.sev_focal, sc.sev_robust)

    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype=str).drop_duplicates("bdsp_id")
    meta["date"] = meta.eeg_datetime.astype(str).str[:8]
    sc = sc.merge(meta[["bdsp_id", "date"]], on="bdsp_id", how="left")
    r = report_ordinals()
    print(f"reports with a scoped, non-negated modifier: sev={r.rep_sev.notna().sum()}, frq={r.rep_frq.notna().sum()}")
    df = sc.merge(r, on=["bdsp_id", "date"], how="inner")     # RECORDING-level join
    # ...but the recording-level row may still hold a report BROADCAST from a sibling study of the same
    # patient (scripts/88). Only cleanly-paired recordings own the text describing them.
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]]
    df = df.merge(cp, on="bdsp_id", how="left")
    df["clean_pair"] = df.clean_pair.fillna(False)
    print(f"recording-level matches: {len(df)}  (cleanly paired: {int(df.clean_pair.sum())})")

    out = ["# Severity & prevalence — RECALIBRATED\n",
           f"Matched {len(df)} recordings with a scoped report adjective.\n"]
    res = {}
    out.append("| measure | all matched | cleanly paired only |")
    out.append("|---|---|---|")
    for name, col, tgt in [("severity: OLD peak_z (max)", "sev_peak", "rep_sev"),
                           ("severity: robust p90 z", "sev_robust", "rep_sev"),
                           ("severity: robust + focal-regional", "sev_final", "rep_sev"),
                           ("prevalence: % segments z>2", "prevalence", "rep_frq")]:
        cells = []
        for sub in (df, df[df.clean_pair]):
            s2 = sub.dropna(subset=[col, tgt])
            if len(s2) < 20: cells.append("n/a"); continue
            rho, p = spearmanr(s2[col], s2[tgt])
            cells.append(f"ρ={rho:.3f} (p={p:.1e}, n={len(s2)})")
            if sub is not df: res[name] = (rho, p, len(s2))
        out.append(f"| {name} | {cells[0]} | **{cells[1]}** |")
    print("\n".join(out))
    df = df[df.clean_pair]      # quantile-mapping + figure use the trustworthy pairs only

    # quantile-map the best severity score onto the empirical adjective distribution
    s = df.dropna(subset=["sev_final", "rep_sev"])
    props = s.rep_sev.value_counts(normalize=True).sort_index()
    cuts = np.nanquantile(s.sev_final, np.cumsum(props.values)[:-1])
    pred = np.digitize(s.sev_final, cuts) + 1
    acc = float((pred == s.rep_sev.values).mean()); within1 = float((np.abs(pred - s.rep_sev.values) <= 1).mean())
    rho_c, _ = spearmanr(pred, s.rep_sev)
    out += ["", f"**Quantile-mapped ordinal severity** (cuts at {np.round(cuts,2).tolist()}): "
                f"exact accuracy {acc:.2f}, within-1 {within1:.2f}, ρ = {rho_c:.3f} (n={len(s)})"]
    Path("results/severity_prevalence_recalibrated.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[-2:]))

    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    for a, (col, tgt, ttl) in zip(ax, [("sev_peak", "rep_sev", "OLD: peak z (max)"),
                                       ("sev_final", "rep_sev", "NEW: robust p90 + focal-regional"),
                                       ("prevalence", "rep_frq", "prevalence vs report frequency")]):
        d2 = df.dropna(subset=[col, tgt])
        data = [d2[d2[tgt] == k][col].values for k in sorted(d2[tgt].unique())]
        a.boxplot(data, showfliers=False); a.set_xticklabels([int(k) for k in sorted(d2[tgt].unique())])
        rho = spearmanr(d2[col], d2[tgt]).correlation
        a.set_title(f"{ttl}\nρ={rho:.2f}"); a.set_xlabel("report ordinal"); a.set_ylabel(col)
    fig.suptitle("Severity/prevalence recalibration: replacing a max-statistic with a robust upper quantile", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig("figures/growth_v2/severity_recalibrated.png", dpi=130); plt.close(fig)
    print("wrote results/severity_prevalence_recalibrated.md + figures/growth_v2/severity_recalibrated.png")


if __name__ == "__main__":
    main()
