"""Focal detection v2 — FINER-than-lobe localization + de-confounded focal-specific target.

Diagnosis: the current focal head is amount-confounded (tracks
generalized), its 6-region focal-specific features are weak/domain-sensitive, and it catches only ~36% of
focal at the experts' operating point. This experiment tries:
  - PER-CHANNEL (18 bipolar / 8 homologous pairs) localization instead of 6 lobes — within-recording
    contrasts (|L-R| asymmetry, max-channel minus median-channel focality, spatial persistence), which are
    reference/scale/age-invariant, so they should transfer to an external site.
  - a FOCAL-SPECIFIC target (positive = focal; negatives = clean-normal + generalized-only) so the head
    cannot lean on overall slowing amount.
Trained on report labels; tested in-domain (OccasionNoise) and external (Sandor_100), vs the current head.

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/64_focal_v2_experiment.py
"""
from __future__ import annotations
import os, importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

m55 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py"))
importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py").loader.exec_module(m55)
m54 = m55.m54; m46 = m54.m49.m46
SM = "data/derived/segment_master"
# SANDOR_DIR must be settable: this defaulted to one developer's Box CloudStorage mount, so the SAI-100
# external validation could not be reproduced anywhere else. The default is the historical path purely
# so the old machine keeps working; everyone else exports SANDOR_DIR.
def _resolve_sandor_dir():
    """Locate the SAI-100 source, or say exactly how to point at it.

    This used to default to one developer's Box CloudStorage mount, so every other machine died with a
    FileNotFoundError deep inside pandas naming a stranger's home directory. The data is DUA-governed and
    cannot be committed, so a default is still needed -- but it must be a path that can plausibly exist
    here, and when it does not it must fail with an instruction rather than a stack trace.
    """
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("SANDOR_DIR")
    if env:
        return env
    for c in (_P.home() / "Desktop/GithubRepos/Sandor_100_local",
              _P.home() / "Sandor_100",
              _P("data/external/Sandor_100"),
              _P("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/"
                 "ChenXiSun/Morgoth1/Datasets/Sandor_100")):    # historical, so the original machine works
        if _P(c).is_dir():
            return str(c)
    raise SystemExit(
        "SAI-100 source not found. It is DUA-governed and not committed, so set SANDOR_DIR to the "
        "directory\nholding validation_study_excel_export.xlsx and Morgoth_results/, e.g.\n"
        "  export SANDOR_DIR=~/Desktop/GithubRepos/Sandor_100_local\n"
        "or run scripts/reproduce_story.sh, which skips this step cleanly when SANDOR_DIR is unset.")


SB_DIR = Path(os.environ.get("SANDOR_DIR") or
              _resolve_sandor_dir()); MR = SB_DIR / "Morgoth_results"
BANDS = ["log_delta", "log_theta", "log_TAR"]
PAIRS = [("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"), ("T5-O1", "T6-O2"),
         ("Fp1-F3", "Fp2-F4"), ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("P3-O1", "P4-O2")]


def feats(args):
    eid, age = args
    f = f"{SM}/eeg_id={eid}/part.parquet"
    if not os.path.exists(f):
        return None
    try:
        d = pd.read_parquet(f, columns=["segment", "channel", "artifact_flag"] + BANDS)
    except Exception:
        return None
    d = d[~d.artifact_flag.astype(bool)]
    if d.empty:
        return None
    out = {"eeg_id": eid, "age": age if np.isfinite(age) else 45.0}
    for b in BANDS:
        w = d.pivot_table(index="segment", columns="channel", values=b, aggfunc="mean")
        pa = [float(np.nanquantile(np.abs(w[L] - w[R]), .9)) for L, R in PAIRS if L in w and R in w]
        if pa:
            out[f"asymmax_{b}"] = max(pa); out[f"asymcon_{b}"] = max(pa) - float(np.median(pa)); out[f"asymmean_{b}"] = float(np.mean(pa))
        arr = w.values
        if arr.shape[1] >= 6:
            foc = np.nanmax(arr, 1) - np.nanmedian(arr, 1)
            out[f"focp90_{b}"] = float(np.nanquantile(foc, .9)); out[f"focmax_{b}"] = float(np.nanmax(foc))
    w = d.pivot_table(index="segment", columns="channel", values="log_delta", aggfunc="mean")
    pk = w.idxmax(axis=1)
    out["persist"] = float(pk.value_counts(normalize=True).max()) if len(pk) else np.nan   # spatial stability of the focus
    return out


CACHE = Path("data/derived/figure_cache/focal_channel_feats.parquet")
_CACHE_DF = None


def _cache():
    """Precomputed feats() output, if built (scripts/84).

    feats() is the one thing in the results tier that needs per-segment PER-CHANNEL band powers, i.e. the
    59 GB segment_master table. Its output is a handful of scalars per recording, so caching the RESULT --
    a couple of MB -- is what makes the focal chain runnable on a figure-loop install.
    """
    global _CACHE_DF
    if _CACHE_DF is None:
        _CACHE_DF = (pd.read_parquet(CACHE).set_index("eeg_id") if CACHE.exists()
                     else pd.DataFrame())
    return _CACHE_DF


def build(ids_ages):
    c = _cache()
    hit = [(i, age) for i, age in ids_ages if len(c) and i in c.index]
    miss = [(i, age) for i, age in ids_ages if not (len(c) and i in c.index)]
    rows = []
    if hit:
        got = c.loc[[i for i, _ in hit]].copy()
        got["age"] = [age if np.isfinite(age) else 45.0 for _, age in hit]   # caller-supplied, never cached
        rows.append(got.reset_index())
    if miss:
        with ThreadPoolExecutor(max_workers=14) as ex:
            r = [x for x in ex.map(feats, miss) if x is not None]
        if r:
            rows.append(pd.DataFrame(r))
    if not rows:
        return pd.DataFrame(columns=["eeg_id"]).set_index("eeg_id")
    return pd.concat(rows, ignore_index=True).set_index("eeg_id")


FCOL = None
def fcols(R):
    global FCOL
    if FCOL is None:
        FCOL = [c for c in R.columns if c != "eeg_id"]
    return [c for c in FCOL if c in R.columns]


def panel_eval(name, R, y, wide, morg=None, sai=None):
    pts = m46.expert_points(wide)
    for lab, s in [("ours-v2 (finer)", R["score"].values)] + ([("Morgoth", morg)] if morg is not None else []) + ([("SCORE-AI", sai)] if sai is not None else []):
        ok = np.isfinite(s) & np.isfinite(y)
        cur = m54.panel_curve(None, y[ok], np.asarray(s)[ok], pts, "#000", "x")
        lo, hi = m54.boot_ci(y[ok], np.asarray(s)[ok])
        print(f"  {name:12s} {lab:16s} AUROC {cur['auc']:.3f} [{lo:.2f}-{hi:.2f}]  {cur['ur']:.0f}% under")


def main():
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = lab[(lab.clean_pair == True) & lab.age.notna()].copy()                                   # noqa: E712
    foc = d.slowing_focal.fillna(False); gen = d.slowing_gen_pathologic.fillna(False); cn = d.clean_normal.fillna(False)
    # FOCAL-SPECIFIC target: positive=focal; negatives=clean-normal + generalized-only (NOT focal); drop the rest
    keep = foc | cn | (gen & ~foc)
    d = d[keep & (~d.eeg_id.astype(str).str.startswith(("MOE_", "ON_")))].copy()
    d["y"] = foc[d.index].astype(int).values
    _c = _cache()
    # same canonical rule as scripts/66: when the cache is installed it defines the eligible set
    d = (d[[i in _c.index for i in d.eeg_id]] if len(_c)
         else d[[os.path.exists(f"{SM}/eeg_id={i}") for i in d.eeg_id]])
    # balanced-ish training sample
    tr = pd.concat([d[d.y == 1].sample(min(3000, int((d.y == 1).sum())), random_state=0),
                    d[d.y == 0].sample(min(3000, int((d.y == 0).sum())), random_state=0)])
    print(f"training on {len(tr)} report recordings (focal-specific: {int(tr.y.sum())} focal vs {int((tr.y==0).sum())} normal+gen)")
    Rtr = build(list(zip(tr.eeg_id, tr.age)))
    C = list(Rtr.columns)                                    # feature columns only (before joining the label)
    Rtr = Rtr.join(tr.set_index("eeg_id").y); med = Rtr[C].median()
    head = m54.Head().fit(Rtr[C].fillna(med).values, Rtr.y.values)

    # OccasionNoise (in-domain)
    V = pd.read_parquet("data/derived/occasion_expert_votes.parquet")
    occ = pd.read_parquet("data/derived/occasion_features.parquet")
    oage = occ[(occ.stage == "W") & (occ.region == "whole_head")].drop_duplicates("fid").set_index("fid").age
    wide = V.dropna(subset=["r1.FN"]).pivot_table(index="fid", columns="rater", values="r1.FN")
    wide.index = [f"ON_{int(i)}" for i in wide.index]
    on_ids = [(e, float(oage.get(int(e.split('_')[1]), np.nan))) for e in wide.index if os.path.exists(f"{SM}/eeg_id={e}")]
    Ron = build(on_ids); keep = wide.index.intersection(Ron.index)
    Ron = Ron.loc[keep]; Ron["score"] = head.score(Ron[C].fillna(med).values)
    yon = (wide.loc[keep].mean(axis=1) >= 0.5).astype(int).values
    MP = pd.read_parquet("data/derived/occasion_morgoth_preds.parquet"); mm = MP[MP.axis == "FN"].set_index("fid").M_pred
    mm.index = [f"ON_{int(i)}" for i in mm.index]
    print("\nFOCAL — OccasionNoise (in-domain):")
    panel_eval("OccasionN", Ron, yon, wide.loc[keep], morg=mm.reindex(keep).values)

    # Sandor (external)
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    sage = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    sbn = lambda nm: int(nm.split("=")[1].split("_")[1])
    sb_ids = [(o.name.split("=")[1], sage.get(f"ID{sbn(o.name):03d}", np.nan))
              for o in sorted(Path(SM).glob("eeg_id=SB_*"))]
    Rsb = build(sb_ids); Rsb["key"] = [f"ID{int(i.split('_')[1]):03d}" for i in Rsb.index]
    ff = pd.read_excel(MR / "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); ff["key"] = ff.file_name.astype(str).str.strip()
    Rsb = Rsb.merge(ff, on="key"); Rsb["score"] = head.score(Rsb[C].fillna(med).values)
    ysb = Rsb.majority.astype(int).values
    wsb = Rsb.set_index("key")[[c for c in ff.columns if c.startswith("expert_")]].apply(pd.to_numeric, errors="coerce")
    print("\nFOCAL — Sandor_100 (external):")
    panel_eval("Sandor", Rsb, ysb, wsb, morg=Rsb.M_pred.values, sai=Rsb.S_pred.values)
    print("\n(baseline for reference — current 6-region head: OccasionNoise 0.923/47% under; Sandor 0.736/0% under)")


if __name__ == "__main__":
    main()
