"""The deviation field, and the six descriptors that are functionals of it.

See docs/description_architecture.md. Morgoth gates (whether/what). Everything here DESCRIBES, and every
descriptor is a measurement -- an aggregation or a contrast of one array:

    Z[segment, region, feature] = (x - mu(age, stage, region, feature)) / sd(age, stage, region, feature)

ONE learned direction `w` (L1, clean-normal vs any pathologic slowing, whole-head, over the five spectral
features). It is applied unchanged to every segment and every region:  S(seg, region) = w . Z[seg, region, :]

Descriptors, per (recording, stage):
  1 amount        median and p90 of S; centile against clinician-normals of that age and stage
  2 location      E(r) = S(r) - mean S over the OTHER lobes; argmax -> region + side; excess in SD
  3 band          BI = (z_theta - z_delta) / (|z_theta| + |z_delta|) over supra-threshold segments
  4 prevalence    fraction of segments with S above the 95th centile of normals at that age and stage
  5 persistence   longest run (min), number of episodes, median episode length
  6 accentuation  the stage maximising (1); whether slowing is present only in sleep

Writes data/derived/description_descriptors.parquet + data/derived/amount_direction.json
             + results/deviation_field.md

Run: PYTHONPATH=src python scripts/107_deviation_field.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

# The clinical trio. `a_atten` = -z_log_alpha, so "more" always means "more slowing".
# An unconstrained L1 fit over {delta, theta, TAR, DAR} returns a NEGATIVE theta weight, because
# TAR - z_theta is (corr 0.985) just alpha attenuation wearing a disguise. Naming the three axes
# explicitly gives all-positive weights, the same AUROC (0.804 vs TAR's 0.801), and a score that
# decomposes into exactly the clauses a neurophysiologist writes.
FEATS = ["log_delta", "log_theta", "log_alpha"]
AMOUNT = ["z_log_delta", "z_log_theta", "a_atten"]
LOBES = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
REGIONS = ["whole_head"] + LOBES
STAGES = ["W", "N1", "N2", "N3", "REM"]
ALERT = ["W", "N1"]
GRID = np.arange(0, 101, 2.0)
BW = 5.0
SEG_STEP_SEC = 14.0                 # 15-s segments stepping 14 s
PREV_Q = 0.95                       # a segment is "abnormal" above the 95th centile of normals
rng = np.random.default_rng(0)


def kernel_stats(age_ref, vals, grid=GRID, bw=BW, min_w=30.0):
    """mu(grid), sd(grid) of `vals` over a reference population, Gaussian-weighted in age."""
    W = np.exp(-0.5 * ((grid[:, None] - age_ref[None, :]) / bw) ** 2)
    sw = W.sum(1)
    ok = sw >= min_w
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    mu[ok] = (W[ok] @ vals) / sw[ok]
    var = (W[ok] @ (vals ** 2)) / sw[ok] - mu[ok] ** 2
    sd[ok] = np.sqrt(np.clip(var, 1e-9, None))
    return mu, sd


def kernel_quantile(age_ref, vals, q, grid=GRID, bw=BW, min_w=30.0):
    """Weighted q-quantile of `vals` at each grid age (used for the prevalence threshold)."""
    out = np.full(len(grid), np.nan)
    order = np.argsort(vals); v = vals[order]; a = age_ref[order]
    for i, g in enumerate(grid):
        wt = np.exp(-0.5 * ((a - g) / bw) ** 2)
        if wt.sum() < min_w: continue
        c = np.cumsum(wt) / wt.sum()
        out[i] = v[np.searchsorted(c, q)] if c[-1] >= q else v[-1]
    return out


def main():
    seg = pd.read_parquet("data/derived/segment_features.parquet")
    stg = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    abn = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([stg, abn], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]].drop_duplicates("bdsp_id")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)

    seg = seg[seg.region.isin(REGIONS) & ~seg.bdsp_id.isin(ex)]
    seg = seg.merge(stages, on=["bdsp_id", "segment"], how="inner")
    seg = seg[seg.stage.isin(STAGES)].merge(lu, on="bdsp_id", how="inner").merge(cp, on="bdsp_id", how="left")
    seg["clean_pair"] = seg.clean_pair.fillna(False)
    seg = seg[seg.age.between(0, 100)]
    # FIX (2026-07-10): drop FLAT segments -- all core bands at the 1e-12 eps floor (ln ~ -27.6). These are
    # suppressed / disconnected / dead epochs that survived artifact rejection; 22-32% of ABNORMAL wake vs
    # ~1% of normal wake. A flat segment has zero power in every band and carries no slowing information; left
    # in, it reads as extreme low power on every band and contaminates the wake descriptors and the amount fit.
    CORE = ["log_delta", "log_theta", "log_alpha", "log_beta"]
    flat = (seg[CORE] < -20).all(axis=1)
    print(f"deviation field: {len(seg):,} rows; dropping {int(flat.sum()):,} FLAT segments "
          f"({flat.mean():.1%}) -> {int((~flat).sum()):,}", flush=True)
    seg = seg[~flat]
    print(f"  over {seg.bdsp_id.nunique():,} recordings", flush=True)

    # ---------------- per-segment z, referenced to clinician-normals of that age, stage, region
    norm = seg.clean_normal == True
    ZC = {}
    for (rg, st), g in seg.groupby(["region", "stage"], observed=True):
        ref = g[g.clean_normal == True]
        if len(ref) < 500: continue
        for f in FEATS:
            mu, sd = kernel_stats(ref.age.values, ref[f].values)
            ZC[(rg, st, f)] = (mu, sd)
    zcols = {}
    for f in FEATS:
        z = np.full(len(seg), np.nan)
        for (rg, st, ff), (mu, sd) in ZC.items():
            if ff != f: continue
            k = ((seg.region == rg) & (seg.stage == st)).values
            if not k.any(): continue
            m_ = np.interp(seg.age.values[k], GRID, mu, left=np.nan, right=np.nan)
            s_ = np.interp(seg.age.values[k], GRID, sd, left=np.nan, right=np.nan)
            z[k] = (seg[f].values[k] - m_) / s_
        zcols["z_" + f] = z
    Z = pd.DataFrame(zcols, index=seg.index)
    Z["a_atten"] = -Z["z_log_alpha"]                       # alpha attenuation: "paucity of faster activity"
    # a_atten is a WAKE/N1 sign only: alpha (the posterior dominant rhythm) is expected there. In N2/N3/REM
    # alpha is normally gone, so low-vs-normal alpha is meaningless and high-vs-normal alpha reflects disrupted
    # sleep architecture, not health -- which is why the raw N1/N2 a_atten was reversed for abnormal recordings.
    Z.loc[(seg["stage"] != "W").values, "a_atten"] = 0.0   # alpha = posterior dominant rhythm; wake only
    seg = pd.concat([seg[["bdsp_id", "region", "segment", "stage", "age", "clean_normal",
                          "has_focal_slow", "gen_class", "clean_pair"]], Z], axis=1)
    seg = seg.dropna(subset=AMOUNT)
    print(f"  after z: {len(seg):,} rows", flush=True)

    # ---------------- the ONE learned direction w: how much slowing is here
    wh = seg[seg.region == "whole_head"]
    rec = wh[wh.stage == "W"].groupby("bdsp_id")[AMOUNT].mean()   # fit w where all three axes apply
    L = lu.set_index("bdsp_id").reindex(rec.index).join(cp.set_index("bdsp_id"))
    L["clean_pair"] = L.clean_pair.fillna(False)
    slow = ((L.gen_class == "pathologic") | (L.has_focal_slow == 1)) & L.clean_pair
    keep = (slow | (L.clean_normal == True)).values
    X = rec[keep]; y = slow[keep].astype(int).values
    mu_, sg_ = X.mean(), X.std().replace(0, 1)
    Xs = ((X - mu_) / sg_).values
    aucs = []
    for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=1).split(Xs, y, np.array(X.index)):
        m = LogisticRegression(penalty="l1", solver="liblinear", C=0.05, max_iter=3000,
                               class_weight="balanced").fit(Xs[tr], y[tr])
        aucs.append(roc_auc_score(y[te], m.decision_function(Xs[te])))
    mdl = LogisticRegression(penalty="l1", solver="liblinear", C=0.05, max_iter=3000,
                             class_weight="balanced").fit(Xs, y)
    w = pd.Series(mdl.coef_[0], index=AMOUNT)
    if (w < -1e-8).any():                                  # a negative weight on a slowing axis is a suppressor
        raise SystemExit(f"amount direction has a negative weight: {dict(w.round(3))}")
    w = w[w > 1e-8]
    print(f"  amount direction w: {dict(w.round(3))}  (5-fold AUROC {np.mean(aucs):.3f})", flush=True)
    Path("data/derived/amount_direction.json").write_text(json.dumps(
        {"w": w.to_dict(), "center": mu_[w.index].to_dict(), "scale": sg_[w.index].to_dict(),
         "cv_auroc": float(np.mean(aucs))}, indent=2))

    # S per segment per region
    Zs = (seg[w.index] - mu_[w.index]) / sg_[w.index]
    Sraw = Zs.mul(w, axis=1).sum(axis=1)

    # RE-STANDARDISE S against clinician-normals of that age and stage, per region, so that S is literally
    # "SD above the age- and stage-matched normal". Without this, S is centred on the mixed population and
    # "2.1 SD above normal" would be false.
    seg["S"] = np.nan
    for (rg, st), g in seg.groupby(["region", "stage"], observed=True):
        ref = g[g.clean_normal == True]
        if len(ref) < 500: continue
        mu, sd = kernel_stats(ref.age.values, Sraw.loc[ref.index].values)
        k = g.index
        m_ = np.interp(seg.loc[k, "age"].values, GRID, mu, left=np.nan, right=np.nan)
        s_ = np.interp(seg.loc[k, "age"].values, GRID, sd, left=np.nan, right=np.nan)
        seg.loc[k, "S"] = (Sraw.loc[k].values - m_) / s_
    seg = seg.dropna(subset=["S"])

    # prevalence threshold: the 95th centile of NORMAL segments at that age & stage (should be ~1.64)
    thr = {}
    for st, g in seg[(seg.clean_normal == True) & (seg.region == "whole_head")].groupby("stage", observed=True):
        if len(g) < 500: continue
        thr[st] = kernel_quantile(g.age.values, g.S.values, PREV_Q)
    seg["S_thr"] = np.nan
    for st, q in thr.items():
        k = (seg.stage == st).values
        seg.loc[k, "S_thr"] = np.interp(seg.age.values[k], GRID, q, left=np.nan, right=np.nan)
    seg["abnormal_seg"] = seg.S > seg.S_thr

    # ---------------- descriptors, per (recording, stage)
    rows = []
    whole = seg[seg.region == "whole_head"]
    lob = seg[seg.region.isin(LOBES)]
    lob_piv = lob.pivot_table(index=["bdsp_id", "stage", "segment"], columns="region", values="S")

    for (bid, st), g in whole.groupby(["bdsp_id", "stage"], observed=True):
        if len(g) < 5: continue
        g = g.sort_values("segment")
        S = g.S.values
        ab = g.abnormal_seg.values
        # 5 persistence: runs of consecutive abnormal segments
        runs, cur = [], 0
        for a in ab:
            if a: cur += 1
            elif cur: runs.append(cur); cur = 0
        if cur: runs.append(cur)
        # 3 band: over supra-threshold segments (fall back to all if none)
        m = ab if ab.any() else np.ones(len(g), bool)
        zt, zd = g.z_log_theta.values[m].mean(), g.z_log_delta.values[m].mean()
        bi = (zt - zd) / (abs(zt) + abs(zd) + 1e-6)
        aatt = float(g.a_atten.values[m].mean())          # "paucity of faster activity" 
        # 2 location: E(r) = S(r) - mean S over the OTHER lobes
        key = lob_piv.loc[lob_piv.index.get_level_values(0) == bid]
        key = key[key.index.get_level_values(1) == st]
        E = np.nan; argmax = None
        if len(key) >= 5 and key.notna().all(axis=1).any():
            mS = key.mean(axis=0)                     # per-lobe mean S in this stage
            if mS.notna().all():
                other = {r: mS.drop(r).mean() for r in LOBES}
                Ev = pd.Series({r: mS[r] - other[r] for r in LOBES})
                argmax = Ev.idxmax(); E = float(Ev.max())
        rows.append(dict(bdsp_id=bid, stage=st, n_seg=len(g),
                         amount_median=float(np.median(S)), amount_p90=float(np.percentile(S, 90)),
                         prevalence=float(ab.mean()),
                         longest_run_min=float(max(runs) * SEG_STEP_SEC / 60) if runs else 0.0,
                         n_episodes=len(runs),
                         median_episode_min=float(np.median(runs) * SEG_STEP_SEC / 60) if runs else 0.0,
                         band_index=float(bi), alpha_attenuation=aatt,
                         focal_excess=E, focal_region=argmax,
                         focal_side={"L": "left", "R": "right"}.get(argmax[0]) if argmax else None))
    D = pd.DataFrame(rows)

    # 6 stage-accentuation, per recording
    acc = D.loc[D.groupby("bdsp_id").amount_median.idxmax(), ["bdsp_id", "stage"]].rename(
        columns={"stage": "accentuated_stage"})
    alert_prev = D[D.stage.isin(ALERT)].groupby("bdsp_id").prevalence.max().rename("alert_prevalence")
    D = D.merge(acc, on="bdsp_id", how="left").merge(alert_prev, on="bdsp_id", how="left")
    D["sleep_only"] = (D.alert_prevalence.fillna(0) < 0.05) & (~D.stage.isin(ALERT)) & (D.prevalence > 0.10)
    D.to_parquet("data/derived/description_descriptors.parquet")

    # ---------------- report
    lab = lu.set_index("bdsp_id")
    D2 = D.merge(lu, on="bdsp_id", how="left")
    grp = np.where(D2.clean_normal == True, "clean-normal",
                   np.where(D2.has_focal_slow == 1, "focal", np.where(D2.gen_class == "pathologic",
                                                                      "generalized", "other")))
    D2["group"] = grp
    out = ["# The deviation field and its six descriptors\n",
           "**Fixes (2026-07-10):** flat segments (all bands at the eps floor; 22-32% of abnormal wake) are "
           "dropped as suppressed/dead epochs; the alpha-attenuation axis is restricted to W/N1 (alpha is the "
           "posterior dominant rhythm, meaningful only where it is expected). See results/n1_anomaly_diagnosis.md.\n",
           f"{len(seg):,} segment-region z-scores over {seg.bdsp_id.nunique():,} recordings. "
           f"One learned direction `w` = " + ", ".join(f"`{k}` {v:+.2f}" for k, v in w.items()) +
           f" (5-fold AUROC {np.mean(aucs):.3f}, split on patient). Everything below is an aggregation or a "
           "contrast of `S = w · z`; nothing else is fit.\n"]
    out.append("## Sanity: descriptors must be unremarkable in clinician-normals\n")
    out.append("| stage | group | n | amount (SD, median) | prevalence (mean) | longest run (min) | "
               "band index | alpha attenuation |")
    out.append("|---|---|---|---|---|---|---|---|")
    for st in ALERT:
        for g in ["clean-normal", "focal", "generalized"]:
            s = D2[(D2.stage == st) & (D2.group == g)]
            if len(s) < 20: continue
            out.append(f"| {st} | {g} | {len(s)} | {s.amount_median.median():+.2f} | "
                       f"{s.prevalence.mean():.3f} | {s.longest_run_min.median():.2f} | "
                       f"{s.band_index.median():+.3f} | {s.alpha_attenuation.median():+.2f} |")
    cn = D2[(D2.group == "clean-normal") & D2.stage.isin(ALERT)]
    out.append(f"\n**Calibration check.** The threshold is the {PREV_Q:.0%} centile of normal segments at that "
               f"age and stage, so clean-normals must average ~0.05 prevalence: observed **{cn.prevalence.mean():.3f}** "
               f"(median {cn.prevalence.median():.3f} — the distribution is right-skewed, so the mean is the "
               f"quantity to read). Their median amount must be ~0: observed "
               f"**{cn.amount_median.median():+.2f} SD**.\n")
    out.append("## Stage coverage\n")
    cov = D2[D2.group != "other"].groupby(["group", "stage"]).size().unstack(fill_value=0)
    out.append(cov.to_markdown())
    out.append("\n\nWritten: `data/derived/description_descriptors.parquet`, "
               "`data/derived/amount_direction.json`.")
    Path("results/deviation_field.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[:14]))


if __name__ == "__main__":
    main()
