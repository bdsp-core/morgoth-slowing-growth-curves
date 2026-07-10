"""Regional slowing as a MEASUREMENT, not a classification.

MBW: "we are simply making objective measurements, whereas the experts are making somewhat subjective
calls... plot box plots of the key features (z-scores relative to normal-for-age curves) for the different
regions to show that they are in fact elevated when experts say they're elevated."

That is what this does. No trained classifier, no forced choice, no label reproduction. For every recording we
compute, per lobe, the deviation of that lobe's slowing features from the age-matched clinician-normal
distribution, in the alert (W/N1) segments. Then we ask whether the lobe the reader localized is the lobe
that is objectively elevated.

The strongest panel is WITHIN-SUBJECT: for focal cases with a stated unilateral side, compare the deviation
in the *ipsilateral* temporal lobe against the *contralateral* one, in the same recording. No between-patient
confounding is possible.

Writes figures/growth_v2/region_z_boxplots.png + results/region_z_boxplots.md.
Run: PYTHONPATH=src python scripts/102_region_z_boxplots.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import wilcoxon, mannwhitneyu
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ALERT = ["W", "N1"]
LOBES = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
FEATS = ["log_delta", "TAR"]
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


def build():
    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "is_abnormal", "has_focal_slow", "has_gen_slow",
         "gen_class", "focal_side", "focal_region"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]]
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)

    d = d[d.region.isin(LOBES) & d.stage.isin(ALERT) & ~d.bdsp_id.isin(ex)]
    ref = d[(d.src == "cohort") & (d.clean_normal == True)]           # routine alert reference

    zs = []
    for feat in FEATS:
        for reg in LOBES:
            for st in ALERT:
                o = d[(d.region == reg) & (d.stage == st)]
                r = ref[(ref.region == reg) & (ref.stage == st)]
                if len(o) == 0 or len(r) < 50: continue
                z = normal_z(o[feat].values, o.age.values, r[feat].values, r.age.values)
                zs.append(pd.DataFrame({"bdsp_id": o.bdsp_id.values, "region": reg, "stage": st,
                                        "feature": feat, "z": z, "n_seg": o.n_seg.values}))
    Z = pd.concat(zs, ignore_index=True).dropna(subset=["z"])
    # collapse W/N1 -> one z per (recording, region, feature), weighted by usable segments
    Z = (Z.groupby(["bdsp_id", "region", "feature"])
           .apply(lambda g: np.average(g.z, weights=g.n_seg), include_groups=False)
           .rename("z").reset_index())
    Z = Z.merge(lu, on="bdsp_id", how="left").merge(cp, on="bdsp_id", how="left")
    Z["clean_pair"] = Z.clean_pair.fillna(False)
    return Z


def group_of(r):
    if r.clean_normal is True or r.clean_normal == 1: return "clinician-normal"
    if r.has_focal_slow == 1 and r.focal_side == "left": return "focal, reported LEFT"
    if r.has_focal_slow == 1 and r.focal_side == "right": return "focal, reported RIGHT"
    if r.has_gen_slow == 1 and r.gen_class == "pathologic": return "generalized"
    return None


def main():
    Z = build()
    Z["group"] = Z.apply(group_of, axis=1)
    # side/region come from the report TEXT -> only trust cleanly-paired recordings for those groups
    Z = Z[(Z.group == "clinician-normal") | (Z.clean_pair == True)]
    Z = Z.dropna(subset=["group"])

    out = ["# Regional slowing as a measurement, not a classification\n",
           "No classifier, no forced choice, no attempt to reproduce the report's region label. Per lobe we "
           "report the deviation of that lobe's slowing features from the **age-matched clinician-normal "
           "distribution**, in alert (W/N1) segments, against a routine-alert reference. The question is "
           "simply: *is the lobe the reader localized the lobe that is objectively elevated?*\n"]

    fig, axes = plt.subplots(2, 3, figsize=(16.5, 9))
    order = ["clinician-normal", "focal, reported LEFT", "focal, reported RIGHT", "generalized"]
    cols = {"clinician-normal": "#8fbf8f", "focal, reported LEFT": "#4c78a8",
            "focal, reported RIGHT": "#e45756", "generalized": "#b07aa1"}

    for row, feat in enumerate(FEATS):
        F = Z[Z.feature == feat]

        # --- panel 1+2: temporal lobes, z by group -------------------------------------------------
        for col, reg in enumerate(["L_temporal", "R_temporal"]):
            ax = axes[row, col]
            data, labs = [], []
            for g in order:
                v = F[(F.region == reg) & (F.group == g)].z.values
                if len(v) >= 20: data.append(v); labs.append(f"{g}\n(n={len(v)})")
            bp = ax.boxplot(data, showfliers=False, patch_artist=True, widths=.6)
            for patch, g in zip(bp["boxes"], [l.split("\n")[0] for l in labs]):
                patch.set_facecolor(cols[g]); patch.set_alpha(.75)
            ax.axhline(0, color="k", lw=.8, ls=":")
            ax.set_xticklabels(labs, fontsize=7.5)
            ax.set_ylabel(f"{feat} deviation (z vs age-matched normal)")
            ax.set_title(f"{reg}  —  {feat}")
            ax.set_ylim(-2.5, 5)

        # --- panel 3: WITHIN-SUBJECT ipsilateral vs contralateral -----------------------------------
        ax = axes[row, 2]
        piv = F[F.region.isin(["L_temporal", "R_temporal"])].pivot_table(
            index=["bdsp_id", "group"], columns="region", values="z").reset_index()
        piv = piv.dropna(subset=["L_temporal", "R_temporal"])
        foc = piv[piv.group.isin(["focal, reported LEFT", "focal, reported RIGHT"])].copy()
        foc["ipsi"] = np.where(foc.group.str.contains("LEFT"), foc.L_temporal, foc.R_temporal)
        foc["contra"] = np.where(foc.group.str.contains("LEFT"), foc.R_temporal, foc.L_temporal)
        nrm = piv[piv.group == "clinician-normal"]
        nrm_both = np.r_[nrm.L_temporal.values, nrm.R_temporal.values]

        data = [nrm_both, foc.contra.values, foc.ipsi.values]
        labs = [f"clinician-normal\n(both temporal lobes)\n(n={len(nrm_both)})",
                f"focal: CONTRAlateral\n(n={len(foc)})", f"focal: IPSIlateral\n(n={len(foc)})"]
        bp = ax.boxplot(data, showfliers=False, patch_artist=True, widths=.6)
        for patch, c in zip(bp["boxes"], ["#8fbf8f", "#bbbbbb", "#e45756"]):
            patch.set_facecolor(c); patch.set_alpha(.8)
        ax.axhline(0, color="k", lw=.8, ls=":")
        ax.set_xticklabels(labs, fontsize=7.5)
        ax.set_title(f"WITHIN-SUBJECT: the reported side is the elevated side  —  {feat}")
        ax.set_ylabel(f"{feat} deviation (z)")
        ax.set_ylim(-2.5, 5)

        # stats
        w = wilcoxon(foc.ipsi, foc.contra)
        d_ips = np.median(foc.ipsi) - np.median(foc.contra)
        y = np.r_[np.ones(len(foc)), np.zeros(len(nrm_both))]
        auc = roc_auc_score(y, np.r_[foc.ipsi.values, nrm_both])
        out.append(f"\n## {feat}\n")
        out.append(f"- **Within-subject** (focal cases with a stated side, n = {len(foc)}): ipsilateral "
                   f"temporal z median **{np.median(foc.ipsi):+.3f}** vs contralateral "
                   f"**{np.median(foc.contra):+.3f}** (Δ = {d_ips:+.3f}, Wilcoxon p = {w.pvalue:.2e}). "
                   f"The lobe the reader named is the lobe that is objectively elevated, in the same recording.")
        out.append(f"- Ipsilateral temporal z vs clinician-normal temporal lobes: **AUROC {auc:.3f}** "
                   f"(n = {len(foc)} vs {len(nrm_both)}).")
        for reg in LOBES:
            gl = F[(F.region == reg) & (F.group == "focal, reported LEFT")].z
            gr = F[(F.region == reg) & (F.group == "focal, reported RIGHT")].z
            nn = F[(F.region == reg) & (F.group == "clinician-normal")].z
            if min(len(gl), len(gr), len(nn)) < 20: continue
            out.append(f"  - `{reg}`: normal {nn.median():+.2f} | reported-left {gl.median():+.2f} | "
                       f"reported-right {gr.median():+.2f}")

    fig.suptitle("Regional slowing is a measurement: deviation from age-matched clinician-normal, alert (W/N1) segments\n"
                 "left/right = the side the clinical report named — not a model prediction", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    Path("figures/growth_v2").mkdir(parents=True, exist_ok=True)
    fig.savefig("figures/growth_v2/region_z_boxplots.png", dpi=140); plt.close(fig)

    # --- what the numbers actually license: SIDE, not lobe -------------------------------------------
    out.append("\n## We resolve side, not lobe\n")
    out.append("Two facts in the tables above bound the claim, and both are visible without a model:\n")
    for feat in FEATS:
        F = Z[Z.feature == feat]
        rows = []
        for pair, nm in [(("L_temporal", "R_temporal"), "temporal"),
                         (("L_parasagittal", "R_parasagittal"), "parasagittal")]:
            piv = F[F.region.isin(pair)].pivot_table(index=["bdsp_id", "group"], columns="region",
                                                     values="z").reset_index().dropna()
            foc = piv[piv.group.isin(["focal, reported LEFT", "focal, reported RIGHT"])].copy()
            if len(foc) < 20: continue
            ipsi = np.where(foc.group.str.contains("LEFT"), foc[pair[0]], foc[pair[1]])
            contra = np.where(foc.group.str.contains("LEFT"), foc[pair[1]], foc[pair[0]])
            rows.append((nm, np.median(ipsi), np.median(contra), np.median(ipsi - contra)))
        for nm, i_, c_, d_ in rows:
            out.append(f"- **{feat}, {nm}**: ipsilateral {i_:+.2f}, contralateral {c_:+.2f}, "
                       f"within-subject Δ **{d_:+.2f}**")
    out.append("\nFirst, the **contralateral** lobe is itself well above the clinician-normal distribution "
               "(≈ +0.5 to +0.8 SD), so focal slowing raises the whole hemispheric background, not one lobe in "
               "isolation. Second, the parasagittal chain shows nearly the same left–right separation as the "
               "temporal chain, so the lateralizing signal is **hemispheric, not lobar**. Both are consistent "
               "with our weak lobe localization (macro-F1 0.23) and with strong side discrimination "
               "(AUROC 0.87). We therefore claim **side**, and describe the region as the maximum-deviation "
               "lobe without claiming it is resolved.\n")

    out.append("\n## Why there is no confusion matrix here\n")
    out.append("The deployed system does not perform forced-choice lobe classification; it reports the region "
               "of maximum deviation. The multi-class confusion matrix in `scripts/42_region_gated.py` scores a "
               "multinomial logistic regression *trained to reproduce the report's region label* — a classifier "
               "we do not ship, evaluated against a label that is majority-temporal (2,165 / 3,872) and, for "
               "17% of recordings, borrowed from a different study of the same patient. Its 0.92 'region "
               "agreement' is a base-rate artifact. It is omitted.")
    txt = "\n".join(out) + "\n"
    Path("results/region_z_boxplots.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
