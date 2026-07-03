"""Phase B: fit age x sex percentile (growth) curves on the NORMAL set.

Outputs:
  data/derived/growth_curves.parquet   tidy: feature, region, sex, age, n_eff, p3..p97
  figures/curves/<feature>__<region>.png   with focal/general subjects overlaid
Run: python scripts/04_fit_reference_models.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

from morgoth_slowing.norms import growth
from morgoth_slowing.viz import growth_curves as gv

FEATURES = ["rel_delta", "rel_theta", "log_delta", "log_theta", "DAR", "TAR", "DTR", "low_freq_rel"]
REGIONS = ["whole_head", "L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
OUT = Path("data/derived"); FIG = Path("figures/curves"); FIG.mkdir(parents=True, exist_ok=True)


def main():
    df = pd.read_parquet(OUT / "recording_features.parquet")
    df = df[df.age.between(0, 120) & df.sex.isin(["M", "F"])]
    ages = np.arange(0, 91, 1.0)
    curves = []
    for region in REGIONS:
        sub = df[df.region == region]
        normal = sub[sub.label == "normal"]
        for feat in FEATURES:
            c = growth.fit_by_sex(normal, feat, ages_grid=ages, bandwidth=5.0, min_eff_n=25)
            c["region"] = region
            curves.append(c)
            subj = sub[["age", feat, "sex", "label"]].rename(columns={feat: "value"}).dropna()
            gv.growth_figure(c, feat, region, subjects=subj, out=FIG / f"{feat}__{region}.png")
        print("fitted", region)
    allc = pd.concat(curves, ignore_index=True)
    allc.to_parquet(OUT / "growth_curves.parquet")
    print("wrote growth_curves.parquet", allc.shape, "| figures ->", FIG)


if __name__ == "__main__":
    main()
