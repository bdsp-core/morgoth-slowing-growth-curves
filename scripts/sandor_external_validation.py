"""EXTERNAL VALIDATION / full-pipeline test on the Sandor 60-EMU dataset (box: Datasets/Sandor_60EMU).

Runs OUR interpretable pipeline end-to-end on 60 external scalp-EEG EMU clips that the model has never
seen — a test of "can we run the whole pipeline on new data":
  EDF -> referential (harmonize the `EEG Fp1-AVGloro`, new-nomenclature montage) -> 18 bipolar ->
  per-15s multitaper features -> age (from EDF header) -> age-matched deviation z (grid_norm.json) ->
  per-recording slowing amount + focal descriptors + a generated description.

CAVEATS (read before interpreting):
  * SLEEP STAGING is approximated as WAKE (the Morgoth ss_hm_1 stager is available but not wired here);
    the event timepoints span day and night, so some clips contain sleep and their wake-referenced score
    is inflated. A crude sleep flag (high rel_delta + low rel_alpha) marks the likely-sleep clips.
  * LABEL TASK: the ratings are E/NE with marked event timepoints from 3 raters — almost certainly
    EPILEPTIFORM-discharge detection (Beniczky), NOT slowing. So the E/NE comparison below is an
    EXPLORATORY specificity check (does our slowing score spuriously track epileptiform E/NE?), NOT a
    slowing validation. The proper slowing labels ("AKS score"?) need confirming with the user.

Run: PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/sandor_external_validation.py [SANDOR_DIR]
"""
from __future__ import annotations
import os, sys, json, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import t as _tdist, norm as _norm
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SANDOR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/sandor")
EDF_DIR = SANDOR / "EDF"
RATINGS = SANDOR / "E-ratings TimepointsExtracted.xlsx"
OUT = Path("results/sandor"); OUT.mkdir(parents=True, exist_ok=True)
NORM_JSON = "data/derived/grid_norm.json"
A0 = 1.0 / 12.0

# --- fix the channel cleaner for `EEG Fp1-AVGloro` (split on '-' BEFORE stripping '-AVG') ---
from morgoth_slowing.io import edf as _edf
def _clean_sandor(name):
    n = name.upper().replace("EEG ", "").strip().split("-")[0].strip()
    return _edf.ALIAS.get(n, n)
_edf._clean = _clean_sandor
from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.features import extract as ex
from morgoth_slowing.features.recording import CH_NAMES              # 18 bipolar names

# --- deviation scoring (identical to scripts/43_segment_deviation) ---
UP = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR"]; DOWN = ["rel_alpha"]
ANT = ["Fp1-F7", "F7-T3", "Fp1-F3", "F3-C3", "Fp2-F8", "F8-T4", "Fp2-F4", "F4-C4", "Fz-Cz"]
POS = ["T3-T5", "T5-O1", "C3-P3", "P3-O1", "T4-T6", "T6-O2", "C4-P4", "P4-O2", "Cz-Pz"]
LOBES = {"L_temporal": ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"], "R_temporal": ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],
         "L_parasagittal": ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"], "R_parasagittal": ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"]}
REGIONS = {"whole_head": None, "anterior": ANT, "posterior": POS, **LOBES}
# 31-feature column indices from features_31: 0 delta,1 theta,6 d/tot(rel_delta),8 a/tot(rel_alpha),12 d/a(DAR),16 th/a(TAR)
COL = {"delta": 0, "theta": 1, "rel_delta": 6, "rel_alpha": 8, "DAR": 12, "TAR": 16}


def a2t(age): return np.log10(np.asarray(age, float) + A0)
def bct_z(y, mu, sigma, nu, tau):
    y = np.asarray(y, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(np.abs(nu) > 1e-8, ((y / mu) ** nu - 1.0) / (nu * sigma), np.log(y / mu) / sigma)
    F = _tdist.cdf(z, df=tau); F0 = np.where(nu > 0, _tdist.cdf(-1.0 / (sigma * np.abs(nu)), df=tau), 0.0)
    Ft = np.where(nu < 0, _tdist.cdf(1.0 / (sigma * np.abs(nu)), df=tau), 1.0)
    return _norm.ppf(np.clip((F - F0) / (Ft - F0), 1e-12, 1 - 1e-12))
def z_of(n, age, val):
    tg, mu, sg, nu, ta, fam = n; t = a2t(age)
    mu_i, sg_i = np.interp(t, tg, mu), np.interp(t, tg, sg)
    val = np.asarray(val, float)
    return (val - mu_i) / sg_i if fam == "NO" else bct_z(val, mu_i, sg_i, np.interp(t, tg, nu), np.interp(t, tg, ta))


def load_norm():
    raw = json.load(open(NORM_JSON))
    return {tuple(k.split("|")): tuple(np.array(a) if i < 5 else a for i, a in enumerate(v)) for k, v in raw.items()}


def edf_age(path):
    import pyedflib
    f = pyedflib.EdfReader(str(path))
    try:
        b = f.getBirthdate(); sd = f.getStartdatetime()
    finally:
        f._close()
    if not b:
        return np.nan
    try:
        bd = dt.datetime.strptime(b, "%d %b %Y") if isinstance(b, str) else b
    except Exception:
        return np.nan
    return round((sd - bd).days / 365.25, 1)


def feats_per_region(feat):
    """feat (n_seg,18,31) -> dict region -> dict FEAT -> (n_seg,) region-mean value (for the 6 norm feats)."""
    ci = {c: [CH_NAMES.index(x) for x in (chs or CH_NAMES)] for c, chs in REGIONS.items()}
    out = {}
    for reg, idx in ci.items():
        sub = feat[:, idx, :]                                       # (n_seg, |reg|, 31)
        vals = {}
        vals["log_delta"] = np.log(np.nanmean(sub[:, :, COL["delta"]], 1) + 1e-12)
        vals["log_theta"] = np.log(np.nanmean(sub[:, :, COL["theta"]], 1) + 1e-12)
        vals["rel_delta"] = np.nanmean(sub[:, :, COL["rel_delta"]], 1)
        vals["rel_alpha"] = np.nanmean(sub[:, :, COL["rel_alpha"]], 1)
        vals["log_DAR"] = np.log(np.nanmean(sub[:, :, COL["DAR"]], 1) + 1e-12)
        vals["log_TAR"] = np.log(np.nanmean(sub[:, :, COL["TAR"]], 1) + 1e-12)
        out[reg] = vals
    return out


def persistence_word(p): return "intermittent" if p < .10 else "frequent" if p < .50 else "abundant" if p < .90 else "nearly continuous"


def describe(rec):
    """A minimal wake-referenced slowing sentence from the recording's descriptors (self-contained;
    does NOT import the D6 generator, which Fable may be editing)."""
    if rec["amount_z"] < 0.7 and rec["prevalence"] < 0.1:
        return "No significant background slowing beyond age-matched expectation (wake-referenced)."
    side = "left" if rec["lat_signed"] > 0.25 else "right" if rec["lat_signed"] < -0.25 else "bilateral"
    focal = abs(rec["lat_signed"]) >= 0.5 or rec["focality"] >= 0.6
    loc = f"{side} {rec['peak_lobe'].replace('_', ' ')}" if focal else "diffuse"
    band = "delta" if rec["z_delta"] - rec["z_theta"] >= 0.7 else "theta" if rec["z_theta"] - rec["z_delta"] >= 0.7 else "theta-delta"
    sl = " (some segments appear sleep-like; wake-referenced score provisional)" if rec["sleep_like_frac"] > 0.3 else ""
    return (f"{persistence_word(rec['prevalence']).capitalize()} {loc} {band} slowing, "
            f"{rec['amount_z']:.1f} SD above age-matched wake norm{sl}.")


def main():
    NORM = load_norm()
    edfs = sorted(EDF_DIR.glob("EC*.edf"), key=lambda p: int(p.stem[2:]))
    print(f"scoring {len(edfs)} Sandor EDFs (wake-referenced)...", flush=True)
    rows = []
    for p in edfs:
        ecn = int(p.stem[2:])
        try:
            data, ch, fs = load_edf_referential(str(p))
            feat, segs = ex.extract(data, ch, fs)                  # (n_seg,18,31)
        except Exception as e:
            print(f"  {p.stem}: FAIL {type(e).__name__}: {e}"); continue
        age = edf_age(p)
        fr = feats_per_region(feat)
        # wake-referenced z per region per feat
        Z = {}
        for reg, vals in fr.items():
            for ft in UP + DOWN:
                key = ("W", reg, ft)
                if key in NORM:
                    Z[f"{reg}|{ft}"] = z_of(NORM[key], age if np.isfinite(age) else 45.0, vals[ft])
        wh = lambda ft: Z.get(f"whole_head|{ft}", np.full(feat.shape[0], np.nan))
        # amount = mean over segments of the mean of the 4 "excess" whole-head z's
        amt_seg = np.nanmean(np.vstack([wh("log_delta"), wh("log_theta"), wh("log_DAR"), wh("log_TAR")]), axis=0)
        z_delta = np.nanmedian(wh("log_delta")); z_theta = np.nanmedian(wh("log_theta"))
        prevalence = float(np.nanmean(amt_seg > 1.5))
        # laterality (temporal + parasagittal L-R on log_delta), peak lobe, focality
        latT = np.nanmean(Z.get("L_temporal|log_delta", np.nan) - Z.get("R_temporal|log_delta", np.nan))
        latP = np.nanmean(Z.get("L_parasagittal|log_delta", np.nan) - Z.get("R_parasagittal|log_delta", np.nan))
        lat = latT if abs(np.nan_to_num(latT)) >= abs(np.nan_to_num(latP)) else latP
        lobe_z = {lb: np.nanmedian(Z.get(f"{lb}|log_delta", np.nan)) for lb in LOBES}
        peak_lobe = max(lobe_z, key=lambda k: np.nan_to_num(lobe_z[k], nan=-9))
        focality = float(np.nan_to_num(lobe_z[peak_lobe]) - np.nanmedian(list(lobe_z.values())))
        # crude sleep flag: high whole-head rel_delta z AND low rel_alpha (rel_alpha z very negative)
        sleep_like = (wh("rel_delta") > 1.0) & (Z.get("whole_head|rel_alpha", np.zeros(feat.shape[0])) < -0.5)
        rec = dict(ec=ecn, age=age, n_seg=int(feat.shape[0]), dur_min=round(feat.shape[0] * 14 / 60, 1),
                   amount_z=float(np.nanmedian(amt_seg)), amount_p90=float(np.nanquantile(amt_seg, .9)),
                   prevalence=prevalence, z_delta=float(z_delta), z_theta=float(z_theta),
                   lat_signed=float(np.nan_to_num(lat)), peak_lobe=peak_lobe, focality=focality,
                   sleep_like_frac=float(np.nanmean(sleep_like)))
        rec["description"] = describe(rec)
        rows.append(rec)
        print(f"  {p.stem}: age {age} n_seg {rec['n_seg']} amount_z {rec['amount_z']:+.2f} "
              f"prev {prevalence:.2f} sleep~ {rec['sleep_like_frac']:.2f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "sandor_scores.parquet", index=False)

    # --- gold standard E/NE (majority of the 3 raters) + exploratory eval ---
    md = ["# Sandor 60-EMU — external pipeline run (OUR interpretable slowing model)\n",
          f"Ran the full front-end + age-matched deviation scoring on **{len(df)}/60** external EMU scalp-EEG "
          "clips the model never saw. Proves the pipeline ingests and scores brand-new EDFs (harmonizing the "
          "`EEG Fp1-AVGloro`, new-nomenclature average-reference montage). **Sleep staging approximated as "
          "wake** (stager available, not wired); **labels are E/NE epileptiform-style, not slowing** — the "
          "comparison below is an exploratory specificity check, not a slowing validation. See script header.\n",
          f"- recordings scored: {len(df)}; median age {df.age.median():.0f} y; median duration {df.dur_min.median():.0f} min",
          f"- our slowing amount_z: median {df.amount_z.median():+.2f} [IQR {df.amount_z.quantile(.25):+.2f}, {df.amount_z.quantile(.75):+.2f}]",
          f"- clips flagged sleep-like (>30% segments): {int((df.sleep_like_frac>0.3).sum())}/{len(df)}\n"]
    try:
        xl = pd.ExcelFile(RATINGS); gs = {}
        for sh in xl.sheet_names:
            d = xl.parse(sh); d = d[d["Samples"].notna()]
            for _, r in d.iterrows():
                s = str(r["Samples"]).strip()
                if s.upper().startswith("L") and s[1:].strip().isdigit():
                    gs.setdefault(int(s[1:].strip()), []).append(str(r["Gold Standard"]).strip().upper())
        goldE = {k: (sum(v.count("E") for v in [vs]) if False else vs.count("E")) > (len(vs) / 2) for k, vs in gs.items()}
        df["gold_E"] = df.ec.map(goldE)                            # assume L{n} <-> EC{n}
        ev = df.dropna(subset=["gold_E"])
        if ev.gold_E.nunique() == 2:
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(ev.gold_E.astype(int), ev.amount_z)
            mE, mN = ev[ev.gold_E].amount_z.median(), ev[~ev.gold_E].amount_z.median()
            md += ["## Exploratory: does our SLOWING score track the epileptiform E/NE gold standard?",
                   f"- amount_z median: **E {mE:+.2f}** vs **NE {mN:+.2f}**; AUROC(E) = **{auc:.3f}** "
                   f"(n={len(ev)}; E={int(ev.gold_E.sum())}, NE={int((~ev.gold_E).sum())})",
                   "- Interpretation: a value near 0.5 is the EXPECTED, reassuring result — our slowing score "
                   "should NOT strongly separate an epileptiform-discharge label (specificity). A large value "
                   "would suggest E clips also carry more background slowing (plausible) or a confound.\n"]
            fig, ax = plt.subplots(figsize=(6, 4.4))
            for lab, sub, c in [("E (epileptiform)", ev[ev.gold_E], "#c8443c"), ("NE", ev[~ev.gold_E], "#2c7fb8")]:
                ax.hist(sub.amount_z, bins=15, alpha=.6, label=lab, color=c)
            ax.axvline(0, ls="--", color="#666"); ax.set_xlabel("our slowing amount_z (wake-referenced)")
            ax.set_ylabel("recordings"); ax.set_title(f"Sandor 60-EMU: our slowing score by gold E/NE (AUROC {auc:.2f})", fontsize=10)
            ax.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(OUT / "sandor_amount_by_gold.png", dpi=140); plt.close(fig)
    except Exception as e:
        md += [f"\n*(gold-standard eval skipped: {type(e).__name__}: {e})*\n"]

    md += ["## Example generated descriptions (highest slowing)"]
    for r in df.sort_values("amount_z", ascending=False).head(6).itertuples():
        md.append(f"- **EC{r.ec}** (age {r.age}): {r.description}")
    (OUT / "sandor_external.md").write_text("\n".join(md))
    print("\nwrote results/sandor/sandor_scores.parquet + sandor_external.md" +
          (" + sandor_amount_by_gold.png" if (OUT / "sandor_amount_by_gold.png").exists() else ""))


if __name__ == "__main__":
    main()
