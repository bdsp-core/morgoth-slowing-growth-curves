"""Phase D: per-recording scoring -> burden, patient-z, topography, verbal phrase.

Combines:
  - recording-level age/sex-adjusted z per region (data/derived/adjusted_z.parquet, from Phase E)
  - segment-level prevalence/burden of delta slowing vs the normal curve (segment_features)
  - hemisphere asymmetry z (recording_asymmetry vs normals)
Then classifies topography and renders a phrase. Validates topo class vs the true label.

Outputs: data/derived/scores.parquet, results/example_reports.md
Run: python scripts/06_discrimination.py first (writes adjusted_z), then this.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm

from morgoth_slowing.scoring import topography
from morgoth_slowing.report import phrase as ph

OUT = Path("data/derived"); RES = Path("results"); RES.mkdir(exist_ok=True)
REGION_LABEL = {"L_temporal": "left temporal", "R_temporal": "right temporal",
                "L_parasagittal": "left parasagittal", "R_parasagittal": "right parasagittal",
                "whole_head": "generalized"}


def robust_sd(p10, p90):
    return (p90 - p10) / 2.5631


def main():
    az = pd.read_parquet(OUT / "adjusted_z.parquet")           # bdsp_id,label,z,feature,region
    curves = pd.read_parquet(OUT / "growth_curves.parquet")
    feats = pd.read_parquet(OUT / "recording_features.parquet")[
        ["bdsp_id", "age", "sex", "label", "region"]].drop_duplicates()

    # --- recording-level delta z per region (burden proxy) ---
    dz = az[az.feature == "log_delta"].pivot_table(index="bdsp_id", columns="region", values="z")
    tz = az[(az.feature == "log_theta") & (az.region == "whole_head")].groupby("bdsp_id").z.mean()

    # --- segment-level prevalence/burden of delta slowing vs normal curve (whole_head) ---
    seg = pd.read_parquet(OUT / "segment_features.parquet",
                          columns=["bdsp_id", "region", "log_delta"])
    seg = seg[seg.region == "whole_head"]
    ages = feats[feats.region == "whole_head"].set_index("bdsp_id")[["age", "sex", "label"]]
    seg = seg.join(ages, on="bdsp_id").dropna(subset=["age", "sex"])
    # normal p50 & sd interpolators per sex
    prev, burd = {}, {}
    for sex in ["M", "F"]:
        cw = curves[(curves.feature == "log_delta") & (curves.region == "whole_head") & (curves.sex == sex)]
        cw = cw.dropna(subset=["p50"]).sort_values("age")
        s = seg[seg.sex == sex]
        p50 = np.interp(s.age, cw.age, cw.p50)
        sd = np.interp(s.age, cw.age, robust_sd(cw.p10, cw.p90))
        z = (s.log_delta.values - p50) / sd
        tmp = pd.DataFrame({"bdsp_id": s.bdsp_id.values, "z": z})
        g = tmp.groupby("bdsp_id").z
        prev.update((g.apply(lambda x: float((x > 2).mean()))).to_dict())
        burd.update((g.apply(lambda x: float(np.maximum(x - 2, 0).mean()))).to_dict())

    # --- hemisphere asymmetry z (temporal delta) vs normals ---
    asym = pd.read_parquet(OUT / "recording_asymmetry.parquet")
    a = asym[["bdsp_id", "label", "asym_temporal_delta"]].copy()
    nmask = a.label == "normal"
    mu, sd = a.loc[nmask, "asym_temporal_delta"].mean(), a.loc[nmask, "asym_temporal_delta"].std()
    a["asym_z"] = (a.asym_temporal_delta - mu) / sd
    asym_z = a.groupby("bdsp_id").asym_z.mean()

    # --- assemble per-recording scores ---
    rows = []
    meta = feats[feats.region == "whole_head"].drop_duplicates("bdsp_id").set_index("bdsp_id")
    for bid, m in meta.iterrows():
        region_z = {r: dz.loc[bid, r] for r in dz.columns if bid in dz.index and r != "whole_head"}
        wh_z = dz.loc[bid, "whole_head"] if bid in dz.index and "whole_head" in dz.columns else np.nan
        th_z = tz.get(bid, np.nan)
        az_t = asym_z.get(bid, np.nan)
        topo = topography.classify(region_z, az_t if np.isfinite(az_t) else 0.0)
        # location + band for phrase
        if topo in ("focal", "lateralized") and region_z:
            loc_region = max(region_z, key=lambda r: (region_z[r] if np.isfinite(region_z[r]) else -9))
            location = REGION_LABEL.get(loc_region, loc_region)
        else:
            location = "generalized"
        band = "delta slowing" if not (np.isfinite(th_z) and th_z > (wh_z or 0)) else "theta slowing"
        pz = wh_z if np.isfinite(wh_z) else 0.0
        rows.append({"bdsp_id": bid, "true_label": m.label, "age": m.age, "sex": m.sex,
                     "patient_z_delta": wh_z, "patient_z_theta": th_z, "asym_temporal_z": az_t,
                     "prevalence": prev.get(bid, np.nan), "burden": burd.get(bid, np.nan),
                     "topo_class": topo, "location": location, "band": band,
                     "severity": ph.severity_word(pz)})
    scores = pd.DataFrame(rows)
    scores.to_parquet(OUT / "scores.parquet")

    # validation: predicted topo vs true label
    xt = pd.crosstab(scores.true_label, scores.topo_class)
    print("=== topo_class vs true_label ===\n", xt.to_string())

    # example generated report sentences (a few per true label)
    with open(RES / "example_reports.md", "w") as fh:
        fh.write("# Example generated report sentences (v1, stage-agnostic)\n\n")
        fh.write("Phrase = severity + location + band + quantitative parenthetical, generated from the "
                 "scoring table (docs/feature_spec.md §8). State is omitted (set is unstaged).\n\n")
        for lab in ["focal_slow", "general_slow", "normal"]:
            fh.write(f"## true label: {lab}\n\n")
            ex = scores[(scores.true_label == lab) & scores.patient_z_delta.notna()]
            # most-slowing examples (highest positive z), not extreme-negative outliers
            ex = ex.sort_values("patient_z_delta", ascending=False).head(4)
            for _, r in ex.iterrows():
                f = ph.StateFinding(state="Record", prevalence=r.prevalence or 0, patient_z=max(r.patient_z_delta, 0),
                                    location=r.location, band=r.band, burden=r.burden or 0,
                                    median_abn_z=r.patient_z_delta, max_run_min=float("nan"),
                                    asymmetry_z=r.asym_temporal_z)
                fh.write(f"- (age {r.age:.0f} {r.sex}, pred **{r.topo_class}**) {ph.render(f)}\n")
            fh.write("\n")
    print("wrote data/derived/scores.parquet and results/example_reports.md")


if __name__ == "__main__":
    main()
