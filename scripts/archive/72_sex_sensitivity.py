"""Test whether conditioning norms on SEX changes abnormality detection for central rel_delta.
Extracts the same central (C3/C4) per-(recording,stage) values as scripts/67, then runs
scripts/sex_sensitivity.R to compare sex-conditional vs sex-pooled z-scores. Also plots z_sex vs z_nosex.

Run: PYTHONPATH=src python scripts/72_sex_sensitivity.py [feature]
"""
from __future__ import annotations
import sys, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FEATURE = sys.argv[1] if len(sys.argv) > 1 else "rel_delta"
TABLE = "data/derived/channel_stage_features.parquet"
CENTRAL = ["F3-C3", "C3-P3", "F4-C4", "C4-P4"]
def A2T(age): return np.log10(np.asarray(age, float) + 1/12)


def main():
    df = pd.read_parquet(TABLE)
    c = df[df.region.isin(CENTRAL)].groupby(["bdsp_id", "stage"]).agg(
        val=(FEATURE, "mean"), age=("age", "first"), sex=("sex", "first")).reset_index()
    hi = 1.0 if FEATURE.startswith("rel") else 1e9
    c = c[c.sex.isin(["M", "F"]) & c.age.between(0, 100) & c.val.between(0, hi)]
    c["t"] = A2T(c.age)
    with tempfile.TemporaryDirectory() as td:
        inp, outp = f"{td}/in.csv", f"{td}/z.csv"
        c[["stage", "sex", "t", "val"]].to_csv(inp, index=False)
        r = subprocess.run(["Rscript", "scripts/sex_sensitivity.R", inp, outp], capture_output=True, text=True)
        print(r.stdout); print(r.stderr[-600:] if r.returncode else "")
        z = pd.read_csv(outp)

    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    ax.scatter(z.z_nosex, z.z_sex, s=3, alpha=0.15, color="#333")
    lim = [z[["z_sex", "z_nosex"]].min().min(), z[["z_sex", "z_nosex"]].max().max()]
    ax.plot(lim, lim, "r-", lw=1); [ax.axhline(v, color="b", lw=.6, ls=":") for v in (-1.96, 1.96)]
    [ax.axvline(v, color="b", lw=.6, ls=":") for v in (-1.96, 1.96)]
    ax.set_xlabel("z (sex-pooled norm)"); ax.set_ylabel("z (sex-conditional norm)")
    ax.set_title(f"Abnormality z-score: sex-conditional vs pooled\n{FEATURE} central; points on y=x => sex irrelevant")
    out = Path(f"figures/growth_v2/sex_sensitivity_{FEATURE}.png"); out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out, dpi=125); plt.close(fig); print("wrote", out)


if __name__ == "__main__":
    main()
