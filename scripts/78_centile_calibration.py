#!/usr/bin/env python3
"""Held-out centile calibration of the GAMLSS normative curves (review item C198).

The curves claim to be percentiles. This checks that they are: for held-out normal data, the proportion of
observations falling below the model's predicted p-th centile should be p. Anything else means the deviation
z-scores are not the calibrated quantities the rest of the paper treats them as.

Two reference sets, neither used to fit the curves:

  internal  clean-normal recordings NOT in the seeded 3,000-recording sample that scripts/115 fits the norms
            on. The sample is drawn with a fixed seed, so the complement is recoverable exactly.
  external  ON-100 panel recordings the expert majority called neither focally nor generally slow — a
            different institution set entirely, and labelled by expert consensus rather than by report.

The predicted centile of an observation is Phi(z), because scripts/43 maps each value through its own cell's
BCT (or log-age normal) CDF and then through the standard-normal quantile function. So a calibrated model
puts Phi(z) uniform on (0,1), and "fraction below nominal p" should equal p.

Confidence bands are patient-clustered: segments within a recording, and recordings within a patient, are
strongly dependent, so patients (not segments) are the resampling unit.

Writes results/story/centile_calibration.md + figures/story/s9_centile_calibration.png
Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/78_centile_calibration.py
"""
from __future__ import annotations
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm as _norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SD = Path("data/derived/segment_deviation")
FIG = Path("figures/story")
RES = Path("results/story")

NOMINAL = [3, 10, 25, 50, 75, 90, 97]
STAGES = ["W", "N1", "N2", "N3", "REM"]
# Ganglberger named relative delta, TAR and DAR as the representative features.
CELLS = [("whole_head", "rel_delta", "relative delta"),
         ("whole_head", "log_TAR", "log TAR"),
         ("whole_head", "log_DAR", "log DAR")]

N_REC_INTERNAL = int(os.environ.get("N_REC", 1500))   # recordings sampled from the held-out normals
N_SEG_PER_REC = int(os.environ.get("N_SEG", 60))      # segments sampled per recording (bounds compute)
N_BOOT = int(os.environ.get("N_BOOT", 400))
RNG = np.random.default_rng(0)


def fitted_ids() -> set[str]:
    """The recordings scripts/115 fit the norms on — reproduced with its seed so the complement is exact."""
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    ref = lab[(lab.clean_normal == True) & (lab.clean_pair == True) & lab.age.notna()]   # noqa: E712
    ids = ref.eeg_id.tolist()
    return set(pd.Series(ids).sample(3000, random_state=0)) if len(ids) > 3000 else set(ids)


def reference_sets() -> tuple[pd.DataFrame, pd.DataFrame]:
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    used = fitted_ids()
    internal = lab[(lab.clean_normal == True) & (lab.clean_pair == True) & lab.age.notna()   # noqa: E712
                   & ~lab.eeg_id.isin(used)][["eeg_id", "patient_id"]].copy()

    panel = pd.read_parquet("data/derived/panel_v6_scores.parquet")
    neg = panel[(panel.FN_maj == 0) & (panel.GN_maj == 0)][["eeg_id"]].copy()
    neg["patient_id"] = neg.eeg_id                       # one recording per patient in the panel
    return internal, neg


CACHE = Path("data/derived/figure_cache/wholehead_z.parquet")
_CACHE_DF = None


def _cache(cols):
    """Whole-head deviation cache: 385 MB in place of 6.5 GB of hive partitions, same values.

    Every cell this figure uses is whole-head, so the cache is a faithful substitute rather than an
    approximation -- it carries every segment, not a sample, and the figure is bit-identical either way.
    """
    global _CACHE_DF
    if _CACHE_DF is None:
        if not CACHE.exists():
            return None
        _CACHE_DF = pd.read_parquet(CACHE, columns=["eeg_id", "segment", "stage"] + cols)
        _CACHE_DF["eeg_id"] = _CACHE_DF["eeg_id"].astype(str)
        _CACHE_DF = {k: v for k, v in _CACHE_DF.groupby("eeg_id", observed=True)}
    return _CACHE_DF


def load_cdf(ids: pd.DataFrame, n_rec: int | None, n_seg: int) -> pd.DataFrame:
    """Phi(z) per (patient, stage, cell) for the given recordings, subsampled to bound compute."""
    if n_rec is not None and len(ids) > n_rec:
        ids = ids.sample(n_rec, random_state=0)
    cols = [f"z__{r}__{f}" for r, f, _ in CELLS]
    cache = _cache(cols)
    out = []
    for eeg_id, pid in zip(ids.eeg_id, ids.patient_id):
        if cache is not None:
            d = cache.get(str(eeg_id))
            if d is None:
                continue
        else:
            p = SD / f"eeg_id={eeg_id}" / "part.parquet"
            if not p.exists():
                continue
            try:
                d = pd.read_parquet(p, columns=["segment", "stage"] + cols)
            except Exception:
                continue
        d = d[d.stage.isin(STAGES)]
        if d.empty:
            continue
        if len(d) > n_seg:
            d = d.sample(n_seg, random_state=0)
        d = d.melt(id_vars=["segment", "stage"], value_vars=cols, var_name="cell", value_name="z")
        d = d[np.isfinite(d.z)]
        d["patient_id"] = pid
        out.append(d)
    if not out:
        return pd.DataFrame(columns=["patient_id", "stage", "cell", "cdf"])
    d = pd.concat(out, ignore_index=True)
    d["cdf"] = _norm.cdf(d.z.values)
    return d[["patient_id", "stage", "cell", "cdf"]]


def observed(d: pd.DataFrame) -> np.ndarray:
    """Fraction of observations below each nominal centile."""
    c = d.cdf.values
    return np.array([(c < p / 100.0).mean() for p in NOMINAL]) * 100.0


def boot_band(d: pd.DataFrame, n_boot: int) -> tuple[np.ndarray, np.ndarray]:
    """Patient-clustered bootstrap percentile band for the observed curve."""
    pats = d.patient_id.unique()
    by = {p: g.cdf.values for p, g in d.groupby("patient_id")}
    reps = []
    for _ in range(n_boot):
        pick = RNG.choice(pats, len(pats), replace=True)
        c = np.concatenate([by[p] for p in pick])
        reps.append(np.array([(c < p / 100.0).mean() for p in NOMINAL]) * 100.0)
    reps = np.vstack(reps)
    return np.percentile(reps, 2.5, axis=0), np.percentile(reps, 97.5, axis=0)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    internal_ids, external_ids = reference_sets()
    print(f"held-out internal normals: {len(internal_ids):,} recordings "
          f"({internal_ids.patient_id.nunique():,} patients)")
    print(f"external panel no-slowing : {len(external_ids):,} recordings")

    arms = {}
    arms["internal held-out normals"] = load_cdf(internal_ids, N_REC_INTERNAL, N_SEG_PER_REC)
    arms["external no-slowing (ON-100)"] = load_cdf(external_ids, None, N_SEG_PER_REC)
    for k, v in arms.items():
        print(f"  {k}: {len(v):,} observations, {v.patient_id.nunique():,} patients")

    style = {"internal held-out normals": dict(color="#1b6ca8", marker="o"),
             "external no-slowing (ON-100)": dict(color="#c1440e", marker="s")}

    ncol, nrow = len(CELLS), len(STAGES)
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.35 * ncol, 2.15 * nrow),
                             sharex=True, sharey=True, squeeze=False)
    rows = []
    for ri, stage in enumerate(STAGES):
        for ci, (region, feat, nice) in enumerate(CELLS):
            ax = axes[ri][ci]
            ax.plot([0, 100], [0, 100], ls="--", lw=1.0, color="#888888", zorder=1)
            for arm, d in arms.items():
                sub = d[(d.stage == stage) & (d.cell == f"z__{region}__{feat}")]
                if len(sub) < 200 or sub.patient_id.nunique() < 10:
                    continue
                obs = observed(sub)
                lo, hi = boot_band(sub, N_BOOT)
                st = style[arm]
                ax.fill_between(NOMINAL, lo, hi, color=st["color"], alpha=0.18, lw=0, zorder=2)
                ax.plot(NOMINAL, obs, color=st["color"], marker=st["marker"], ms=3.4, lw=1.5,
                        zorder=3, label=arm)
                for p, o, l, h in zip(NOMINAL, obs, lo, hi):
                    rows.append(dict(stage=stage, feature=nice, arm=arm, nominal=p,
                                     observed=round(float(o), 2), lo=round(float(l), 2),
                                     hi=round(float(h), 2), n_obs=len(sub),
                                     n_patients=int(sub.patient_id.nunique())))
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.set_xticks([3, 25, 50, 75, 97])
            ax.set_yticks([3, 25, 50, 75, 97])
            ax.tick_params(labelsize=8)
            ax.grid(alpha=0.18)
            if ri == 0:
                ax.set_title(nice, fontsize=10)
            if ci == 0:
                ax.set_ylabel(f"{stage}\nobserved %", fontsize=9)
            if ri == nrow - 1:
                ax.set_xlabel("nominal centile", fontsize=9)
    h, l = axes[0][0].get_legend_handles_labels()
    if h:
        fig.legend(h, l, loc="upper center", ncol=2, fontsize=9, frameon=False,
                   bbox_to_anchor=(0.5, 1.005))
    fig.suptitle("Held-out centile calibration of the normative curves\n"
                 "(dashed = perfect; bands are patient-clustered bootstrap 95% CIs)",
                 fontsize=11, y=1.055)
    fig.tight_layout()
    out = FIG / "s9_centile_calibration.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    t = pd.DataFrame(rows)
    t.to_csv(RES / "centile_calibration.csv", index=False)
    # worst absolute deviation from nominal, per arm — the headline number
    lines = ["# Held-out centile calibration (review item C198)", "",
             "Fraction of held-out observations below each model-predicted centile. A calibrated model puts "
             "the observed value on the nominal one. Bands are patient-clustered bootstrap 95% CIs.", ""]
    for arm in arms:
        a = t[t.arm == arm]
        if a.empty:
            lines += [f"**{arm}** — insufficient data.", ""]
            continue
        a = a.assign(err=(a.observed - a.nominal).abs())
        lines += [f"**{arm}** — max |observed − nominal| = **{a.err.max():.1f} points** "
                  f"(median {a.err.median():.1f}); "
                  f"{a.n_obs.max():,} observations, {a.n_patients.max():,} patients.", ""]
    lines += ["| stage | feature | arm | nominal | observed | 95% CI |", "|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        lines.append(f"| {r.stage} | {r.feature} | {r.arm} | {r.nominal} | {r.observed} | "
                     f"{r.lo}–{r.hi} |")
    (RES / "centile_calibration.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out} and {RES/'centile_calibration.md'} ({len(t)} rows)")


if __name__ == "__main__":
    main()
