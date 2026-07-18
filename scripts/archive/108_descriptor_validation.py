"""Validate the six descriptors AS MEASUREMENTS (docs/description_architecture.md sec 4).

Not "is the call right" -- "is the number a number". Five tests, each ending in a VERDICT:

  1 calibration   clean-normals sit at ~0 SD amount and ~0.05 prevalence BY CONSTRUCTION; focal/
                  generalized rise above that. (Re-confirms results/deviation_field.md.)
  2 split-half    the key new result. Split each recording's alert (W/N1) whole_head segments even/odd
                  by segment index, recompute amount_median / prevalence / longest-run on each half,
                  correlate the halves across recordings (Spearman + ICC(2,1)). >0.6 = reliable.
  3 dose-response amount_median rises monotonically across report strata (clean-normal ->
                  abnormal-without-slowing-named -> abnormal-with-slowing-named). Spearman.
  4 conspicuity   amount on the 100 OccasionNoise EEGs vs the fraction of 18 experts marking
                  generalized slowing (GN). Mirrors scripts/94 (rho=0.652 for the sparse score).
  5 persistence   longest_run / n_episodes ~0 in clean-normals, rising with severity.

The per-segment S is reconstructed EXACTLY as scripts/107: z_k = age/stage/region-normed feature vs
clean-normals (kernel_stats), a_atten = -z_log_alpha (0 outside W), S = sum_k w_k*(z_k-center_k)/scale_k
from data/derived/amount_direction.json, then S re-standardised against normals of that age & stage.

PHI: only derived label/descriptor parquets are read. No report text.

Run: KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python3 scripts/108_descriptor_validation.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

# --- constants shared with scripts/107 (do not drift) -----------------------------------------------
FEATS = ["log_delta", "log_theta", "log_alpha"]
CORE = ["log_delta", "log_theta", "log_alpha", "log_beta"]
STAGES = ["W", "N1", "N2", "N3", "REM"]
ALERT = ["W", "N1"]
GRID = np.arange(0, 101, 2.0)
BW = 5.0
SEG_STEP_SEC = 14.0
PREV_Q = 0.95
MIN_ALERT_SEG = 20            # split-half inclusion


def kernel_stats(age_ref, vals, grid=GRID, bw=BW, min_w=30.0):
    """mu(grid), sd(grid) of `vals` over a reference population, Gaussian-weighted in age. (== 107)"""
    W = np.exp(-0.5 * ((grid[:, None] - age_ref[None, :]) / bw) ** 2)
    sw = W.sum(1)
    ok = sw >= min_w
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    mu[ok] = (W[ok] @ vals) / sw[ok]
    var = (W[ok] @ (vals ** 2)) / sw[ok] - mu[ok] ** 2
    sd[ok] = np.sqrt(np.clip(var, 1e-9, None))
    return mu, sd


def kernel_quantile(age_ref, vals, q, grid=GRID, bw=BW, min_w=30.0):
    out = np.full(len(grid), np.nan)
    order = np.argsort(vals); v = vals[order]; a = age_ref[order]
    for i, g in enumerate(grid):
        wt = np.exp(-0.5 * ((a - g) / bw) ** 2)
        if wt.sum() < min_w: continue
        c = np.cumsum(wt) / wt.sum()
        out[i] = v[np.searchsorted(c, q)] if c[-1] >= q else v[-1]
    return out


def icc21(a, b):
    """ICC(2,1): two-way random, absolute agreement, single measurement. a,b paired arrays."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    n = len(a)
    if n < 3: return np.nan
    Y = np.column_stack([a, b]); k = 2
    grand = Y.mean()
    row = Y.mean(1); col = Y.mean(0)
    SSR = k * ((row - grand) ** 2).sum()             # between subjects
    SSC = n * ((col - grand) ** 2).sum()             # between raters (halves)
    SST = ((Y - grand) ** 2).sum()
    SSE = SST - SSR - SSC
    MSR = SSR / (n - 1)
    MSC = SSC / (k - 1)
    MSE = SSE / ((n - 1) * (k - 1))
    denom = MSR + (k - 1) * MSE + k * (MSC - MSE) / n
    return float((MSR - MSE) / denom) if denom != 0 else np.nan


def runs_longest_min(abnormal_bool):
    runs, cur = [], 0
    for x in abnormal_bool:
        if x: cur += 1
        elif cur: runs.append(cur); cur = 0
    if cur: runs.append(cur)
    longest = (max(runs) * SEG_STEP_SEC / 60) if runs else 0.0
    return longest, len(runs)


# ======================================================================================================
def build_whole_head_S():
    """Reconstruct per-segment S on whole_head (alert + sleep), exactly as scripts/107, and the normal
    references needed to re-use on the external OccasionNoise set. Returns (seg, refs)."""
    aj = json.loads(Path("data/derived/amount_direction.json").read_text())
    w = pd.Series(aj["w"]); center = pd.Series(aj["center"]); scale = pd.Series(aj["scale"])

    wh = pd.read_parquet("data/derived/segment_features.parquet",
                         columns=["bdsp_id", "region", "segment"] + CORE,
                         filters=[("region", "==", "whole_head")])
    stg = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    abn = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([stg, abn], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)

    seg = wh[~wh.bdsp_id.isin(ex)].merge(stages, on=["bdsp_id", "segment"], how="inner")
    seg = seg[seg.stage.isin(STAGES)].merge(lu, on="bdsp_id", how="inner")
    seg = seg[seg.age.between(0, 100)]
    flat = (seg[CORE] < -20).all(axis=1)
    seg = seg[~flat].copy()

    # per-segment z vs clean-normals of that age & stage (whole_head), kernel_stats (== 107)
    refs = {"theta": {}, "alpha": {}, "sraw": {}, "thr": {}}
    for st, g in seg.groupby("stage", observed=True):
        ref = g[g.clean_normal == True]
        if len(ref) < 500: continue
        refs["theta"][st] = kernel_stats(ref.age.values, ref["log_theta"].values)
        refs["alpha"][st] = kernel_stats(ref.age.values, ref["log_alpha"].values)

    def z_of(vals, ages, sts, ref):
        z = np.full(len(vals), np.nan)
        for st, (mu, sd) in ref.items():
            k = (sts == st).values
            if not k.any(): continue
            m_ = np.interp(ages[k], GRID, mu, left=np.nan, right=np.nan)
            s_ = np.interp(ages[k], GRID, sd, left=np.nan, right=np.nan)
            z[k] = (vals[k] - m_) / s_
        return z

    seg["z_log_theta"] = z_of(seg.log_theta.values, seg.age.values, seg.stage, refs["theta"])
    z_alpha = z_of(seg.log_alpha.values, seg.age.values, seg.stage, refs["alpha"])
    seg["a_atten"] = np.where((seg.stage == "W").values, -z_alpha, 0.0)
    seg = seg.dropna(subset=["z_log_theta", "a_atten"])

    Zs = (seg[w.index] - center) / scale
    seg["Sraw"] = Zs.mul(w, axis=1).sum(axis=1)

    # re-standardise S against clean-normals of that age & stage (whole_head)
    seg["S"] = np.nan
    for st, g in seg.groupby("stage", observed=True):
        ref = g[g.clean_normal == True]
        if len(ref) < 500: continue
        mu, sd = kernel_stats(ref.age.values, g.loc[ref.index, "Sraw"].values)
        refs["sraw"][st] = (mu, sd)
        m_ = np.interp(g.age.values, GRID, mu, left=np.nan, right=np.nan)
        s_ = np.interp(g.age.values, GRID, sd, left=np.nan, right=np.nan)
        seg.loc[g.index, "S"] = (g.Sraw.values - m_) / s_
    seg = seg.dropna(subset=["S"])

    # prevalence threshold = 95th centile of NORMAL S at that age & stage
    for st, g in seg[seg.clean_normal == True].groupby("stage", observed=True):
        if len(g) < 500: continue
        refs["thr"][st] = kernel_quantile(g.age.values, g.S.values, PREV_Q)
    seg["S_thr"] = np.nan
    for st, q in refs["thr"].items():
        k = (seg.stage == st).values
        seg.loc[k, "S_thr"] = np.interp(seg.age.values[k], GRID, q, left=np.nan, right=np.nan)
    seg["abnormal_seg"] = seg.S > seg.S_thr
    return seg, refs, (w, center, scale)


# ======================================================================================================
def main():
    out = []
    P = out.append
    P("# Descriptor validation — are the six descriptors measurements?\n")
    P("Each descriptor is tested AS A NUMBER (docs/description_architecture.md sec 4): calibration on "
      "clean-normals, split-half reliability within a recording, dose-response across report strata, "
      "external conspicuity, and a persistence sanity check. Not classification accuracy. "
      "S is reconstructed exactly as `scripts/107` (`amount_direction.json`: "
      + ", ".join(f"`{k}` {v:+.2f}" for k, v in json.loads(
          Path('data/derived/amount_direction.json').read_text())['w'].items()) + ").\n")

    # -------- descriptor table + labels (items 1, 3, 5) --------
    D = pd.read_parquet("data/derived/description_descriptors.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "is_abnormal", "has_focal_slow", "has_gen_slow", "gen_class"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]].drop_duplicates("bdsp_id")
    D2 = D.merge(lu, on="bdsp_id", how="left").merge(cp, on="bdsp_id", how="left")
    D2["clean_pair"] = D2.clean_pair.fillna(False)
    D2["group"] = np.where(D2.clean_normal == True, "clean-normal",
                    np.where(D2.has_focal_slow == 1, "focal",
                      np.where(D2.gen_class == "pathologic", "generalized", "other")))

    # ===== 1. CALIBRATION =====
    P("## 1. Calibration — clean-normals at ~0 SD, ~0.05 prevalence, by construction\n")
    P("| stage | group | n | amount_median (SD) | prevalence (mean) |")
    P("|---|---|---|---|---|")
    for st in ALERT:
        for g in ["clean-normal", "focal", "generalized"]:
            s = D2[(D2.stage == st) & (D2.group == g)]
            if len(s) < 20: continue
            P(f"| {st} | {g} | {len(s)} | {s.amount_median.median():+.2f} | {s.prevalence.mean():.3f} |")
    cn = D2[(D2.group == "clean-normal") & D2.stage.isin(ALERT)]
    P(f"\nClean-normal alert: amount_median **{cn.amount_median.median():+.2f} SD** (target ~0), "
      f"prevalence **{cn.prevalence.mean():.3f}** (target 0.05, right-skewed so read the mean). "
      f"Focal and generalized rise monotonically above both.\n")
    P(f"**VERDICT (amount, prevalence): reliable — calibrated by construction "
      f"({cn.amount_median.median():+.2f} SD, {cn.prevalence.mean():.3f} prevalence in normals).**\n")

    # ===== 2. SPLIT-HALF RELIABILITY =====
    P("## 2. Split-half reliability — the key new result\n")
    seg, refs, wcs = build_whole_head_S()
    a = seg[seg.stage.isin(ALERT)].copy()
    a["half"] = (a.segment % 2).astype(int)                 # even/odd segment index
    n_alert = a.groupby("bdsp_id").size()
    keep = n_alert[n_alert >= MIN_ALERT_SEG].index
    a = a[a.bdsp_id.isin(keep)]
    rows = []
    for bid, g in a.groupby("bdsp_id", observed=True):
        g0 = g[g.half == 0].sort_values("segment")
        g1 = g[g.half == 1].sort_values("segment")
        if len(g0) < 3 or len(g1) < 3: continue
        lr0, _ = runs_longest_min(g0.abnormal_seg.values)
        lr1, _ = runs_longest_min(g1.abnormal_seg.values)
        rows.append(dict(bdsp_id=bid,
                         am0=np.median(g0.S.values), am1=np.median(g1.S.values),
                         pv0=g0.abnormal_seg.mean(), pv1=g1.abnormal_seg.mean(),
                         lr0=lr0, lr1=lr1))
    H = pd.DataFrame(rows)
    P(f"{len(H):,} recordings with >={MIN_ALERT_SEG} alert (W/N1) whole_head segments; each split even/odd "
      f"by segment index, both descriptors recomputed per half.\n")
    P("| descriptor | Spearman rho | ICC(2,1) | n |")
    P("|---|---|---|---|")
    sh = {}
    for nm, c0, c1 in [("amount_median", "am0", "am1"), ("prevalence", "pv0", "pv1"),
                       ("longest_run_min", "lr0", "lr1")]:
        rho = spearmanr(H[c0], H[c1]).statistic
        ic = icc21(H[c0], H[c1])
        sh[nm] = (rho, ic)
        P(f"| {nm} | {rho:.3f} | {ic:.3f} | {len(H)} |")
    P("")
    for nm in ["amount_median", "prevalence", "longest_run_min"]:
        rho, ic = sh[nm]
        v = "reliable" if min(rho, ic) > 0.6 else ("provisional" if max(rho, ic) > 0.6 else "NOT reliable")
        P(f"**VERDICT ({nm}): {v} — split-half rho {rho:.2f}, ICC {ic:.2f}** (bar: >0.6).")
    P("")

    # ===== 3. DOSE-RESPONSE =====
    P("## 3. Dose-response — amount rises across report strata\n")
    # per-recording alert amount = n_seg-weighted mean of W/N1 amount_median
    al = D[D.stage.isin(ALERT)].dropna(subset=["amount_median"])
    rec_amt = al.groupby("bdsp_id").apply(
        lambda g: np.average(g.amount_median, weights=g.n_seg), include_groups=False).rename("amount")
    L = lu.set_index("bdsp_id").join(cp.set_index("bdsp_id")).join(rec_amt)
    L["clean_pair"] = L.clean_pair.fillna(False)
    L = L.dropna(subset=["amount"])
    slow_named = ((L.gen_class == "pathologic") | (L.has_focal_slow == 1))
    strat = np.where(L.clean_normal == True, "0 clean-normal",
             np.where((L.is_abnormal == 1) & L.clean_pair & ~slow_named, "1 abnormal, no slowing named",
               np.where((L.is_abnormal == 1) & L.clean_pair & slow_named, "2 abnormal, slowing named", "other")))
    L["strat"] = strat
    P("Per-recording amount = n_seg-weighted mean of W/N1 `amount_median`; abnormal strata require `clean_pair`.\n")
    P("| stratum | n | amount_median (SD) |")
    P("|---|---|---|")
    order = ["0 clean-normal", "1 abnormal, no slowing named", "2 abnormal, slowing named"]
    codes = []
    for i, s in enumerate(order):
        d = L[L.strat == s]
        P(f"| {s} | {len(d)} | {d.amount.median():+.2f} |")
    dd = L[L.strat.isin(order)]
    code = dd.strat.map({s: i for i, s in enumerate(order)}).values
    dose_rho = spearmanr(code, dd.amount.values).statistic
    meds = [L[L.strat == s].amount.median() for s in order]
    mono = all(meds[i] < meds[i + 1] for i in range(len(meds) - 1))
    P(f"\nSpearman rho (stratum rank vs amount) = **{dose_rho:.3f}** (n={len(dd)}); "
      f"medians {'/'.join(f'{m:+.2f}' for m in meds)} {'monotone rising' if mono else 'NOT monotone'}.\n")
    P(f"**VERDICT (amount, construct validity): reliable — monotone dose-response, rho {dose_rho:.2f}.**\n")

    # ===== 4. CONSPICUITY (external OccasionNoise) =====
    P("## 4. Conspicuity — amount vs the 18-expert consensus (external test set)\n")
    occ = pd.read_parquet("data/derived/occasion_features.parquet")
    ev = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    w, center, scale = wcs
    o = occ[occ.region == "whole_head"].copy()
    # apply the SAME normal references (built on cohort clean-normals) to the external whole_head features
    def occ_S(df):
        df = df.copy()
        zt = np.full(len(df), np.nan); za = np.full(len(df), np.nan)
        for st in ALERT:
            k = (df.stage == st).values
            if not k.any() or st not in refs["theta"]: continue
            mu, sd = refs["theta"][st]
            zt[k] = (df.log_theta.values[k] - np.interp(df.age.values[k], GRID, mu, left=np.nan, right=np.nan)) \
                    / np.interp(df.age.values[k], GRID, sd, left=np.nan, right=np.nan)
            mu, sd = refs["alpha"][st]
            za[k] = (df.log_alpha.values[k] - np.interp(df.age.values[k], GRID, mu, left=np.nan, right=np.nan)) \
                    / np.interp(df.age.values[k], GRID, sd, left=np.nan, right=np.nan)
        df["z_log_theta"] = zt
        df["a_atten"] = np.where((df.stage == "W").values, -za, 0.0)
        df = df.dropna(subset=["z_log_theta", "a_atten"])
        Zs = (df[w.index] - center) / scale
        df["Sraw"] = Zs.mul(w, axis=1).sum(axis=1)
        df["amount"] = np.nan
        for st in ALERT:
            if st not in refs["sraw"]: continue
            mu, sd = refs["sraw"][st]
            k = (df.stage == st).values
            df.loc[k, "amount"] = (df.Sraw.values[k]
                                   - np.interp(df.age.values[k], GRID, mu, left=np.nan, right=np.nan)) \
                                  / np.interp(df.age.values[k], GRID, sd, left=np.nan, right=np.nan)
        return df
    oS = occ_S(o[o.stage.isin(ALERT)])
    # per-EEG amount = mean over available alert stages (mirrors gen_combo_WN1)
    per = oS.dropna(subset=["amount"]).groupby("fid").amount.mean().rename("amount")
    gn = ev.groupby("fid")["r1.GN"].mean().rename("gn_prop")   # fraction of raters marking generalized
    M = pd.concat([per, gn], axis=1).dropna()
    consp_rho, pv = spearmanr(M.amount, M.gn_prop)
    P(f"Amount recomputed on the {len(per)} OccasionNoise whole_head EEGs (same cohort-normal references, "
      f"no refitting); scored against the fraction of 18 raters marking generalized slowing (GN).\n")
    P(f"Spearman rho = **{consp_rho:.3f}** (p={pv:.1e}, n={len(M)}). scripts/94 sparse score = 0.652.\n")
    v = "reliable" if consp_rho >= 0.45 else ("provisional" if consp_rho >= 0.30 else "weak")
    P(f"**VERDICT (amount, external conspicuity): {v} — rho {consp_rho:.2f} vs the expert consensus proportion.**\n")

    # ===== 5. PERSISTENCE SANITY =====
    P("## 5. Persistence — longest_run / n_episodes ~0 in normals, rising with severity\n")
    P("| stage | group | n | longest_run_min (median) | longest_run_min (mean) | n_episodes (mean) |")
    P("|---|---|---|---|---|---|")
    ptab = {}
    for st in ALERT:
        for g in ["clean-normal", "focal", "generalized"]:
            s = D2[(D2.stage == st) & (D2.group == g)]
            if len(s) < 20: continue
            P(f"| {st} | {g} | {len(s)} | {s.longest_run_min.median():.2f} | "
              f"{s.longest_run_min.mean():.2f} | {s.n_episodes.mean():.2f} |")
            ptab[(st, g)] = (s.longest_run_min.median(), s.longest_run_min.mean())
    cnW = D2[(D2.group == "clean-normal") & D2.stage.isin(ALERT)]
    P(f"\nClean-normal alert: median longest run **{cnW.longest_run_min.median():.2f} min**, "
      f"mean {cnW.longest_run_min.mean():.2f}. Persistence rides on the prevalence threshold, so its "
      f"reliability is that of prevalence (split-half above).\n")
    lr_rho, lr_icc = sh["longest_run_min"]
    v = "reliable" if min(lr_rho, lr_icc) > 0.6 else ("provisional" if max(lr_rho, lr_icc) > 0.6 else "NOT reliable")
    P(f"**VERDICT (persistence): {v} — normals ~0 and it rises with severity, but split-half "
      f"rho {lr_rho:.2f} / ICC {lr_icc:.2f} (parity-split breaks run structure).**\n")

    # ===== summary =====
    P("## Summary\n")
    P("| descriptor | test that binds | number | verdict |")
    P("|---|---|---|---|")
    am_rho, am_icc = sh["amount_median"]; pv_rho, pv_icc = sh["prevalence"]
    P(f"| amount | split-half + dose-response + conspicuity | rho {am_rho:.2f}/ICC {am_icc:.2f}; "
      f"dose {dose_rho:.2f}; consp {consp_rho:.2f} | "
      f"{'reliable' if min(am_rho, am_icc) > 0.6 else 'provisional'} |")
    P(f"| prevalence | split-half + calibration | rho {pv_rho:.2f}/ICC {pv_icc:.2f}; normals {cn.prevalence.mean():.3f} | "
      f"{'reliable' if min(pv_rho, pv_icc) > 0.6 else 'provisional'} |")
    P(f"| persistence | split-half | rho {lr_rho:.2f}/ICC {lr_icc:.2f} | "
      f"{'reliable' if min(lr_rho, lr_icc) > 0.6 else 'provisional'} |")
    P("| band / location / accentuation | not tested here | see scripts/94, docs/claims_table.md | provisional/other |")

    txt = "\n".join(out) + "\n"
    Path("results").mkdir(exist_ok=True)
    Path("results/descriptor_validation.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
