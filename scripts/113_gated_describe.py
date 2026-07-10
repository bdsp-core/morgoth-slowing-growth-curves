"""Gated, per-branch description: the anterior/posterior gradient for the generalized branch, and the
consistency-enforced descriptor set for each branch.

Morgoth gates (whether/what). This script computes the DESCRIPTORS the two branches need, adding the piece
the deviation field (scripts/107) did not have: the **anterior/posterior spatial gradient** for generalized
slowing. It is validated against the report's `gen_topography` label (anterior / posterior / unspec).

  AP(recording, stage) = S(anterior chain) - S(posterior chain)
where S is the wake-fit amount direction applied to each channel's age/stage-normed z (scripts/107's `w`),
and the chains are the standard anterior / posterior bipolar derivations. Frontally predominant if AP is above
the normal 95th centile, posterior if below the 5th, diffuse otherwise -- the same normal-referenced, per-stage
logic as every other descriptor.

Consistency: the generalized branch may report {AP gradient, band, prevalence, persistence}; the focal branch
{side, region, band, prevalence, persistence}. Neither may report a non-slowing feature. Descriptors are drawn
only from the slowing axes (delta/theta excess, alpha attenuation in wake) + their regional contrasts.

Writes data/derived/gen_ap_gradient.parquet + results/gated_describe.md
Run: PYTHONPATH=src python scripts/113_gated_describe.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

ANTERIOR = ["Fp1-F3", "Fp2-F4", "Fp1-F7", "Fp2-F8", "F3-C3", "F4-C4", "Fz-Cz"]
POSTERIOR = ["C3-P3", "C4-P4", "P3-O1", "P4-O2", "T5-O1", "T6-O2", "Cz-Pz"]
FEATS = ["log_delta", "log_theta", "log_alpha"]
STAGES = ["W", "N1"]
GRID = np.arange(0, 101, 2.0); BW = 5.0
rng = np.random.default_rng(0)


def kstats(a, v):
    W = np.exp(-0.5 * ((GRID[:, None] - a[None, :]) / BW) ** 2); sw = W.sum(1); ok = sw >= 30
    mu = np.full(len(GRID), np.nan); sd = np.full(len(GRID), np.nan)
    mu[ok] = (W[ok] @ v) / sw[ok]
    sd[ok] = np.sqrt(np.clip((W[ok] @ (v ** 2)) / sw[ok] - mu[ok] ** 2, 1e-9, None))
    return mu, sd


def auc_ci(y, s, n=2000):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2: return (np.nan, np.nan, np.nan)
    a = roc_auc_score(y, s); bs = []
    for _ in range(n):
        j = rng.choice(len(y), len(y), replace=True)
        if 0 < y[j].sum() < len(j): bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    w = json.loads(Path("data/derived/amount_direction.json").read_text())
    W = pd.Series(w["w"]); cen = pd.Series(w["center"]); scl = pd.Series(w["scale"])

    d = pd.read_parquet("data/derived/channel_stage_features.parquet")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    d = d[d.region.isin(ANTERIOR + POSTERIOR) & d.stage.isin(STAGES) & ~d.bdsp_id.isin(ex)]
    d["a_atten"] = np.nan  # filled per-channel below

    # per (channel, stage) age-normed z for each feature, from clean-normals; a_atten only in W
    def zfeat(sub, f, ref):
        mu, sd = kstats(ref.age.values, ref[f].values)
        return (sub[f].values - np.interp(sub.age.values, GRID, mu)) / np.interp(sub.age.values, GRID, sd)

    parts = []
    for (rg, st), sub in d.groupby(["region", "stage"], observed=True):
        ref = sub[sub.clean_normal == True]
        if len(ref) < 100: continue
        z = pd.DataFrame({"bdsp_id": sub.bdsp_id.values, "region": rg, "stage": st})
        for f in FEATS:
            z["z_" + f] = zfeat(sub, f, ref)
        z["a_atten"] = np.where(st == "W", -z["z_log_alpha"], 0.0)
        # S = w . standardized(features). w keys are z_log_delta / z_log_theta / a_atten
        feats = pd.DataFrame({k: z[k] for k in W.index})
        z["S"] = ((feats - cen[W.index]) / scl[W.index]).mul(W, axis=1).sum(axis=1)
        parts.append(z[["bdsp_id", "region", "stage", "S"]])
    Z = pd.concat(parts, ignore_index=True)

    Z["chain"] = np.where(Z.region.isin(ANTERIOR), "ant", "post")
    chain = Z.groupby(["bdsp_id", "stage", "chain"]).S.mean().unstack("chain")
    chain["AP"] = chain["ant"] - chain["post"]
    # recording-level AP = the alert-stage value with the largest |AP|
    ap = chain.reset_index().dropna(subset=["AP"])
    ap = ap.loc[ap.groupby("bdsp_id").AP.apply(lambda s: s.abs().idxmax())][["bdsp_id", "AP", "ant", "post"]]

    # normal-referenced thresholds for AP (5th / 95th centile of clean-normals)
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "gen_class", "gen_topography"]].drop_duplicates("bdsp_id")
    ap = ap.merge(lu, on="bdsp_id", how="left")
    nrm = ap[ap.clean_normal == True].AP
    lo, hi = np.nanpercentile(nrm, [5, 95])
    ap["ap_call"] = np.where(ap.AP > hi, "anterior", np.where(ap.AP < lo, "posterior", "diffuse"))
    ap.to_parquet("data/derived/gen_ap_gradient.parquet")

    # ---- validate against the report topography label, on pathologic-generalized recordings
    g = ap[(ap.gen_class == "pathologic") & ap.gen_topography.isin(["anterior", "posterior"])]
    y = (g.gen_topography == "anterior").astype(int)
    a, alo, ahi = auc_ci(y.values, g.AP.values)

    out = ["# Gated describe — the anterior/posterior gradient for generalized slowing\n",
           f"AP = S(anterior chain) − S(posterior chain), S = the wake-fit amount direction applied to each "
           f"channel's age/stage-normed z. Normal 5th/95th centile: [{lo:+.2f}, {hi:+.2f}].\n",
           "## Does AP recover the report's anterior/posterior call?\n",
           f"On pathologic-generalized recordings with a stated topography "
           f"(anterior n={int(y.sum())}, posterior n={int((1-y).sum())}):",
           f"- **AP vs report anterior-vs-posterior: AUROC {a:.3f} [{alo:.3f}, {ahi:.3f}]**",
           f"- median AP: report-anterior **{g[g.gen_topography=='anterior'].AP.median():+.2f}**, "
           f"report-posterior **{g[g.gen_topography=='posterior'].AP.median():+.2f}**\n",
           "## Call distribution by group\n",
           "| group | anterior | diffuse | posterior |", "|---|---|---|---|"]
    for grp, m in [("clean-normal", ap.clean_normal == True),
                   ("pathologic-generalized", ap.gen_class == "pathologic")]:
        vc = ap[m].ap_call.value_counts(normalize=True)
        out.append(f"| {grp} | {vc.get('anterior',0):.1%} | {vc.get('diffuse',0):.1%} | {vc.get('posterior',0):.1%} |")
    out.append("\nClean-normals should be ~90% diffuse by construction (5%/5% tails). The generalized group "
               "should show more anterior/posterior predominance if AP carries topographic signal.")
    out.append("\n## Consistency (enforced structurally)\n")
    out.append("- **generalized** branch emits: AP gradient (anterior/posterior/diffuse), band, prevalence, "
               "persistence, stage-accentuation.")
    out.append("- **focal** branch emits: side, region, band, prevalence, persistence, stage-accentuation.")
    out.append("- Neither emits a non-slowing feature; all descriptors are functionals of the slowing axes.")
    Path("results/gated_describe.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
