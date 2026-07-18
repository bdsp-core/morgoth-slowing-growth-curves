"""PHASE A + B — our stage-matched deviation score vs the 18-expert panel (OccasionNoise).

Predictions P1-P10 were fixed in docs/phaseA_preregistration.md BEFORE any of this ran.
This script reports what happened, including where the predictions failed.

Inputs : data/derived/occasion_features.parquet          (scripts/93; external test set, no refitting)
         data/derived/channel_stage_features.parquet     (our cohort -> the normal reference)
         scratchpad Occasion.xlsx                        (expert votes)
         scratchpad Morgoth_results/*.xlsx               (the gate's predictions, for context)
Outputs: results/occasion_model_vs_experts.md, figures/growth_v2/occasion_roc_experts.png

Run: PYTHONPATH=src python scripts/94_phaseA_model_vs_experts.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, mannwhitneyu
from sklearn.metrics import roc_auc_score, roc_curve, cohen_kappa_score
from sklearn.linear_model import LogisticRegression
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SC = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
      "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/occ")
ALERT = ["W", "N1"]
# Pre-specified primary scores (docs/phaseA_preregistration.md). NOT chosen on these data.
PRIMARY = {"generalized": "gen_combo_WN1_routine", "focal": "foc_asym_TAR_routine"}
# expert-vs-consensus operating point, from results/occasion_human_ceiling.md
EXPERT_PT = {"generalized": (0.735, 0.884), "focal": (0.703, 0.899)}   # (sens, spec)
GEN, FOC = "whole_head", ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
rng = np.random.default_rng(0)


def normal_z(vals, ages, ref_vals, ref_ages, bw=5.0):
    z = np.full(len(vals), np.nan)
    ra, rv = np.asarray(ref_ages, float), np.asarray(ref_vals, float)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    for i in range(len(vals)):
        if not (np.isfinite(vals[i]) and np.isfinite(ages[i])): continue
        w = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = w.sum()
        if sw < 5: continue
        mu = (w * rv).sum() / sw
        sd = np.sqrt(max((w * (rv - mu) ** 2).sum() / sw, 1e-9))
        z[i] = (vals[i] - mu) / sd
    return z


def auc_ci(y, s, n=2000):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2: return np.nan, np.nan, np.nan, 0
    a = roc_auc_score(y, s); bs = []
    idx = np.arange(len(y))
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(m.sum())


def loo_youden(score, y):
    """Leave-one-out Youden threshold: the cut for EEG i is chosen on the other n-1. No self-information."""
    n = len(y); out = np.zeros(n, int)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        if y[m].sum() in (0, m.sum()): continue
        best, bt = -1, np.nanmedian(score[m])
        for t in np.unique(score[m][np.isfinite(score[m])]):
            p = (score[m] >= t).astype(int)
            se = p[y[m] == 1].mean(); sp = 1 - p[y[m] == 0].mean()
            if se + sp - 1 > best: best, bt = se + sp - 1, t
        out[i] = int(score[i] >= bt)
    return out


def bal(pred, y):
    return 0.5 * (pred[y == 1].mean() + 1 - pred[y == 0].mean())


def build_scores():
    occ = pd.read_parquet("data/derived/occasion_features.parquet")
    ref_all = pd.read_parquet("data/derived/channel_stage_features.parquet")
    routine = ref_all[(ref_all.src == "cohort") & (ref_all.clean_normal == True)]
    union = ref_all[ref_all.clean_normal == True]

    rows = []
    for refname, ref in [("routine", routine), ("union", union)]:
        for feat in ["TAR", "log_delta", "DAR", "rel_delta"]:
            for reg in [GEN] + FOC:
                o = occ[occ.region == reg]
                r = ref[ref.region == reg]
                for stg in ["W", "N1", "N2", "N3", "REM"]:
                    oo, rr = o[o.stage == stg], r[r.stage == stg]
                    if len(oo) == 0 or len(rr) < 50: continue
                    z = normal_z(oo[feat].values, oo.age.values, rr[feat].values, rr.age.values)
                    rows.append(pd.DataFrame({"fid": oo.fid.values, "ref": refname, "feature": feat,
                                              "region": reg, "stage": stg, "z": z,
                                              "n_seg": oo.n_seg.values}))
    Z = pd.concat(rows, ignore_index=True)

    def wide(ref, sel):
        d = Z[(Z.ref == ref) & sel(Z)]
        return d

    S = {}
    # --- generalized, W/N1 restricted (PRIMARY, routine reference) ---
    for ref in ["routine", "union"]:
        d = Z[(Z.ref == ref) & (Z.region == GEN)]
        tar_w = d[(d.feature == "TAR") & (d.stage == "W")].set_index("fid").z
        ld_n1 = d[(d.feature == "log_delta") & (d.stage == "N1")].set_index("fid").z
        combo = pd.concat([tar_w.rename("a"), ld_n1.rename("b")], axis=1).mean(axis=1, skipna=True)
        S[f"gen_TAR_W_{ref}"] = tar_w
        S[f"gen_logdelta_N1_{ref}"] = ld_n1
        S[f"gen_combo_WN1_{ref}"] = combo
        # all-stage: n_seg-weighted mean of each segment-stage's z against ITS OWN stage norm
        for feat in ["TAR", "log_delta"]:
            dd = d[d.feature == feat].dropna(subset=["z"])
            allst = dd.groupby("fid").apply(lambda g: np.average(g.z, weights=g.n_seg), include_groups=False)
            S[f"gen_{feat}_allstage_{ref}"] = allst
    # --- focal: max lobar deviation, and homologous asymmetry ---
    for ref in ["routine", "union"]:
        d = Z[(Z.ref == ref) & (Z.region.isin(FOC)) & (Z.stage.isin(ALERT))]
        for feat in ["TAR", "log_delta"]:
            dd = d[d.feature == feat]
            mx = dd.groupby("fid").z.max()
            S[f"foc_max_{feat}_{ref}"] = mx
            piv = dd.pivot_table(index="fid", columns="region", values="z", aggfunc="mean")
            asym = pd.DataFrame(index=piv.index)
            if {"L_temporal", "R_temporal"} <= set(piv.columns):
                asym["t"] = (piv.L_temporal - piv.R_temporal).abs()
            if {"L_parasagittal", "R_parasagittal"} <= set(piv.columns):
                asym["p"] = (piv.L_parasagittal - piv.R_parasagittal).abs()
            S[f"foc_asym_{feat}_{ref}"] = asym.max(axis=1)
    return pd.DataFrame(S)


def main():
    S = build_scores()
    # Prefer the PHI-free cache (scripts/100) so this figure regenerates without the scratchpad.
    cache = Path("data/derived/occasion_expert_votes.parquet")
    if cache.exists():
        db = pd.read_parquet(cache).rename(columns={"rater": "uid"})
    else:
        db = pd.ExcelFile(f"{SC}/Occasion.xlsx").parse("DB")
    tgt, prop, experts = {}, {}, {}
    for ax, nm in [("FN", "focal"), ("GN", "generalized")]:
        c = db.pivot_table(index="fid", columns="uid", values=f"r1.{ax}")
        tgt[nm] = (c.mean(1) >= 0.5).astype(int)
        prop[nm] = c.mean(1)
        experts[nm] = c
    ceiling = {"focal": 0.801, "generalized": 0.809}
    morgoth_auc = {"focal": 0.923, "generalized": 0.895}

    out = ["# Phase A/B — our normative score vs the 18-expert panel (external test set)\n",
           f"{S.shape[0]} of 100 EEGs scored. Pipeline unchanged; norms from our cohort; **no refitting, no "
           "threshold tuning on these data**. Predictions P1–P10 were fixed in "
           "`docs/phaseA_preregistration.md` before this ran.\n"]

    res = {}
    for nm in ["generalized", "focal"]:
        y = tgt[nm].reindex(S.index).dropna()
        idx = y.index
        out.append(f"\n## {nm} slowing (expert majority prevalence {y.mean():.2f}, n={len(y)})\n")
        out.append("| score | AUROC [95% CI] | n |")
        out.append("|---|---|---|")
        cols = [c for c in S.columns if c.startswith("gen_" if nm == "generalized" else "foc_")]
        aucs, best, bestauc = {}, None, -1
        for c in cols:
            sv = S.loc[idx, c].values.astype(float)
            a, lo, hi, n = auc_ci(y.values, sv)
            aucs[c] = a
            if np.isfinite(a):
                tag = " **(pre-specified primary)**" if c == PRIMARY[nm] else ""
                out.append(f"| `{c}`{tag} | {a:.3f} [{lo:.3f}, {hi:.3f}] | {n} |")
                if "routine" in c and a > bestauc and "allstage" not in c:
                    best, bestauc = c, a
        out.append(f"\n*Best-on-test is `{best}` ({bestauc:.3f}); it was selected using these labels and is "
                   f"therefore OPTIMISTIC. All pre-registered verdicts below use the pre-specified primary "
                   f"`{PRIMARY[nm]}` ({aucs[PRIMARY[nm]]:.3f}).*")
        res[nm] = (PRIMARY[nm], aucs[PRIMARY[nm]], y, idx, aucs, best, bestauc)

        # LOO-recalibrated operating point (P10) for the prespecified primary score
        prim = PRIMARY[nm]
        if prim in S.columns:
            s = S.loc[idx, prim].values.astype(float)
            m = np.isfinite(s)
            yv, sv = y.values[m], s[m]
            naive = (sv > 2).astype(int)                       # naive z>2 cut
            loo = loo_youden(sv, yv)
            kee = []
            E = experts[nm].reindex(idx).values[m]
            for i in range(E.shape[1]):
                for j in range(i + 1, E.shape[1]):
                    a_, b_ = E[:, i], E[:, j]
                    ok = ~(np.isnan(a_) | np.isnan(b_))
                    if ok.sum() > 20 and len(set(a_[ok])) > 1 and len(set(b_[ok])) > 1:
                        kee.append(cohen_kappa_score(a_[ok], b_[ok]))
            kae = [cohen_kappa_score(loo[~np.isnan(E[:, i])], E[~np.isnan(E[:, i]), i])
                   for i in range(E.shape[1]) if len(set(E[~np.isnan(E[:, i]), i])) > 1]
            out.append(f"\n**Operating point** for prespecified primary score `{prim}` (n={m.sum()}):\n")
            out.append("| calls | bal. accuracy | sens | spec | κ vs each expert (median) |")
            out.append("|---|---|---|---|---|")
            out.append(f"| naive z>2 | {bal(naive,yv):.3f} | {naive[yv==1].mean():.3f} | "
                       f"{1-naive[yv==0].mean():.3f} | — |")
            out.append(f"| **LOO Youden (P10)** | **{bal(loo,yv):.3f}** | {loo[yv==1].mean():.3f} | "
                       f"{1-loo[yv==0].mean():.3f} | {np.median(kae):.3f} |")
            out.append(f"| *average expert vs consensus* | *{ceiling[nm]:.3f}* | — | — | "
                       f"*{np.median(kee):.3f}* (expert–expert) |")
            out.append(f"\n- P10 (recalibration gain ≥ 0.05 over naive z>2): "
                       f"gain = **{bal(loo,yv)-bal(naive,yv):+.3f}** → "
                       f"{'HOLDS' if bal(loo,yv)-bal(naive,yv) >= 0.05 else 'FAILS'}")
            out.append(f"- κ_ae (median {np.median(kae):.3f}) vs κ_ee (median {np.median(kee):.3f}); "
                       f"attenuation benchmark √κ_ee = {np.sqrt(max(np.median(kee),0)):.3f}")

        # Phase B: consensus proportion (conspicuity)
        pr = prop[nm].reindex(idx).values
        if prim in S.columns:
            s = S.loc[idx, prim].values.astype(float)
            m = np.isfinite(s) & np.isfinite(pr)
            rho, pv = spearmanr(s[m], pr[m])
            out.append(f"\n**Phase B — consensus proportion (conspicuity):** Spearman ρ = **{rho:.3f}** "
                       f"(p={pv:.1e}, n={m.sum()}) using `{prim}`.")
            if nm == "generalized":
                out.append(f"- P6 (ρ ≥ 0.45; fails if < 0.30): {'HOLDS' if rho>=0.45 else ('PARTIAL' if rho>=0.30 else 'FAILS')}")
                out.append(f"- P7 (exceeds the report-adjective severity ρ = 0.050; fails if ≤ 0.15): "
                           f"{'HOLDS' if rho>0.15 else 'FAILS'}")

    # ---- pre-registered verdicts (ALL on pre-specified primaries; no test-set selection)
    out.append("\n## Pre-registered predictions\n")
    gb, ga, gy, gidx, gaucs, gbest, gbestauc = res["generalized"]
    fb, fa, fy, fidx, faucs, fbest, fbestauc = res["focal"]
    out.append(f"- **P1** generalized AUROC 0.85–0.93 (fails <0.80): `{gb}` = **{ga:.3f}** → "
               f"{'HOLDS' if 0.85<=ga<=0.93 else ('FAILS' if ga<0.80 else 'PARTIAL (above range)')}")
    out.append(f"- **P2** focal AUROC 0.70–0.85 and clearly < generalized: `{fb}` = **{fa:.3f}** → "
               f"{'FAILS (focal ≥ generalized)' if fa>=ga else ('HOLDS' if 0.70<=fa<=0.85 else 'PARTIAL')}")

    # P3: does the mean expert operating point lie below our ROC?
    for nm in ["generalized", "focal"]:
        c, a, y, idx = res[nm][0], res[nm][1], res[nm][2], res[nm][3]
        sv = S.loc[idx, c].values.astype(float); m = np.isfinite(sv)
        fpr, tpr, _ = roc_curve(y.values[m], sv[m])
        ese, esp = EXPERT_PT[nm]
        our_tpr = float(np.interp(1 - esp, fpr, tpr))       # our sensitivity at the expert's specificity
        out.append(f"- **P3** ({nm}) at the mean expert's specificity ({esp:.3f}) our sensitivity is "
                   f"**{our_tpr:.3f}** vs the expert's {ese:.3f} → "
                   f"{'our ROC passes ABOVE the mean expert point' if our_tpr>ese else 'the mean expert point lies ABOVE our ROC'}"
                   + (" → HOLDS" if (nm=='generalized' and our_tpr>ese) else (" → FAILS" if nm=='generalized' else "")))

    out.append(f"- **P4** we should not beat Morgoth's focal AUROC ({morgoth_auc['focal']:.3f}): ours "
               f"{fa:.3f} (primary) / {fbestauc:.3f} (best-on-test) → "
               f"{'HOLDS' if max(fa,fbestauc)<=morgoth_auc['focal'] else 'FAILS'}")

    # P5: like-for-like, per feature — W/N1-restricted vs all-stage (each segment vs its OWN stage norm)
    out.append("\n**P5 — W/N1 restriction vs all-stage, like-for-like (routine reference):**\n")
    out.append("| feature | W/N1-restricted | all-stage | winner |"); out.append("|---|---|---|---|")
    pairs = [("TAR", "gen_TAR_W_routine", "gen_TAR_allstage_routine"),
             ("log_delta", "gen_logdelta_N1_routine", "gen_log_delta_allstage_routine")]
    p5_wins = 0
    for feat, a_, b_ in pairs:
        va, vb = gaucs.get(a_, np.nan), gaucs.get(b_, np.nan)
        w = "W/N1" if va > vb else ("all-stage" if vb > va else "tie")
        p5_wins += int(va > vb)
        out.append(f"| {feat} | {va:.3f} | {vb:.3f} | {w} |")
    out.append(f"\n- **P5** predicted W/N1 beats all-stage for generalized slowing → "
               f"**{'HOLDS' if p5_wins==len(pairs) else 'FAILS'}** "
               f"({p5_wins}/{len(pairs)} features). The all-stage score already compares every segment to "
               f"*its own stage's* norm, so discarding sleep buys nothing here — and the experts read the whole "
               f"study. **What does matter is the REFERENCE POPULATION**, below.")

    # the routine-vs-union contrast: the actual vigilance-matching claim
    out.append("\n**The vigilance-matched REFERENCE is what carries the effect** (same scores, "
               "routine-alert vs union normals):\n")
    out.append("| score | routine (alert) ref | union ref | Δ |"); out.append("|---|---|---|---|")
    for base in ["gen_TAR_W", "gen_logdelta_N1", "gen_combo_WN1", "gen_TAR_allstage", "gen_log_delta_allstage"]:
        r_, u_ = gaucs.get(base + "_routine", np.nan), gaucs.get(base + "_union", np.nan)
        if np.isfinite(r_) and np.isfinite(u_):
            out.append(f"| `{base}` | {r_:.3f} | {u_:.3f} | **{r_-u_:+.3f}** |")

    # ---- figure: ROC with each expert overlaid
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax_, nm in zip(axes, ["generalized", "focal"]):
        y = tgt[nm].reindex(S.index).dropna(); idx = y.index
        c = PRIMARY[nm]
        s = S.loc[idx, c].values.astype(float); m = np.isfinite(s)
        fpr, tpr, _ = roc_curve(y.values[m], s[m])
        ax_.plot(fpr, tpr, lw=2, label=f"ours (pre-specified): {c}\nAUROC {res[nm][1]:.3f}")
        E = experts[nm].reindex(idx).values[m]
        for i in range(E.shape[1]):
            oth = np.delete(E, i, axis=1)
            cons = (np.nanmean(oth, 1) >= 0.5).astype(int)
            e = E[:, i]; ok = ~np.isnan(e)
            if cons[ok].sum() in (0, ok.sum()): continue
            se = e[ok][cons[ok] == 1].mean(); sp = 1 - e[ok][cons[ok] == 0].mean()
            ax_.plot(1 - sp, se, "o", ms=6, mfc="none", mec="crimson", mew=1.4,
                     label="individual expert" if i == 0 else None)
        ax_.plot([0, 1], [0, 1], "k:", lw=.8)
        ax_.set_title(f"{nm} slowing"); ax_.set_xlabel("1 − specificity"); ax_.set_ylabel("sensitivity")
        ax_.legend(loc="lower right", fontsize=8)
    fig.suptitle("Our stage-matched deviation score vs 18 electroencephalographers (external test set)")
    fig.tight_layout()
    Path("figures/growth_v2").mkdir(parents=True, exist_ok=True)
    fig.savefig("figures/growth_v2/occasion_roc_experts.png", dpi=140); plt.close(fig)

    txt = "\n".join(out) + "\n"
    Path("results/occasion_model_vs_experts.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
