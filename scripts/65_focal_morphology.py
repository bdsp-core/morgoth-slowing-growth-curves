"""Focal detection v3 — add MORPHOLOGY features (beyond band power) and test with the Sandor 50/50 split.

Diagnosis so far: spectral + spatial features cap ~0.75 AUROC / <10% experts-under on external focal, well
below the expert corner (71% sens @ 88% spec). Focal slowing is often POLYMORPHIC delta with a waveform/
field that band power misses. This adds per-channel morphology — time-domain (line length, Hjorth mobility/
complexity, RMS), aperiodic 1/f SLOPE, and RHYTHMICITY (slow-band peak prominence + spectral entropy) — turns
them into finer-than-lobe focal features (homologous-pair asymmetry + max-channel focality), and evaluates on
the Sandor_100 set with a 50/50 focal-stratified split (train 49 / test 49), vs SCORE-AI and Morgoth on the
SAME held-out half. Morphology is cached to data/derived/sandor_morph.parquet (slow to compute once).

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/65_focal_morphology.py
"""
from __future__ import annotations
import os, subprocess, tempfile, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

from morgoth_slowing.io.edf import load_edf_referential
from morgoth_slowing.features import extract as ex
from morgoth_slowing.features.recording import CH_NAMES
m55 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py"))
importlib.util.spec_from_file_location("m55", "scripts/55_recording_model.py").loader.exec_module(m55)
m54 = m55.m54; m46 = m54.m49.m46
m64 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m64", "scripts/64_focal_v2_experiment.py"))
importlib.util.spec_from_file_location("m64", "scripts/64_focal_v2_experiment.py").loader.exec_module(m64)

SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100"); MR = SB_DIR / "Morgoth_results"
MORPH_CACHE = Path("data/derived/sandor_morph.parquet")
MNAMES = ["ll", "mob", "comp", "rms", "slope", "peak", "ent"]
PAIRS = [("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"), ("T5-O1", "T6-O2"),
         ("Fp1-F3", "Fp2-F4"), ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("P3-O1", "P4-O2")]
PAIR_IDX = [(CH_NAMES.index(L), CH_NAMES.index(R)) for L, R in PAIRS]
EPS = 1e-12


def seg_morph(x, fs):
    """x (18, n_samp) one segment -> (18, 7) morphology features per channel."""
    dx = np.diff(x, axis=1); ddx = np.diff(dx, axis=1)
    v0 = x.var(1) + EPS; v1 = dx.var(1) + EPS; v2 = ddx.var(1) + EPS
    ll = np.abs(dx).sum(1); mob = np.sqrt(v1 / v0); comp = np.sqrt(v2 / v1) / mob; rms = np.sqrt(v0)
    fr, psd = ex.multitaper_psd(x, fs)
    m = (fr >= 2) & (fr <= 40) & ~((fr > 55) & (fr < 65))
    lf = np.log10(fr[m]); lp = np.log10(psd[:, m] + EPS)
    slope = np.array([np.polyfit(lf, lp[i], 1)[0] for i in range(x.shape[0])])       # aperiodic 1/f slope
    ms = (fr >= 1) & (fr <= 8); ps = psd[:, ms] + EPS
    peak = ps.max(1) / np.median(ps, 1)                                              # rhythmicity: slow peak prominence
    pn = ps / ps.sum(1, keepdims=True); ent = -(pn * np.log(pn)).sum(1)             # slow-band spectral entropy
    return np.stack([ll, mob, comp, rms, slope, peak, ent], axis=1)


def rec_morph(edf, age):
    with tempfile.TemporaryDirectory() as td:                                       # bounded copy off Box CloudStorage
        loc = os.path.join(td, "r.edf"); subprocess.run(["cp", str(edf), loc], check=True, timeout=300)
        data, chs, fs = load_edf_referential(loc)
    bip = ex.to_bipolar(ex.preprocess(data.astype(np.float32), fs), chs)            # (n_samp, 18)
    segs = ex.segment_indices(bip.shape[0])
    M = np.stack([seg_morph(bip[s:e].T, fs) for s, e in segs])                       # (n_seg, 18, 7)
    chan = np.nanpercentile(M, 90, axis=0)                                           # (18, 7) per-channel p90
    out = {"age": age}
    for fi, fn in enumerate(MNAMES):
        v = chan[:, fi]
        pa = [abs(v[iL] - v[iR]) for iL, iR in PAIR_IDX]
        out[f"m_asymmax_{fn}"] = float(max(pa)); out[f"m_asymcon_{fn}"] = float(max(pa) - np.median(pa))
        out[f"m_foc_{fn}"] = float(np.nanmax(v) - np.nanmedian(v)); out[f"m_mean_{fn}"] = float(np.nanmean(v))
    return out


def build_morph():
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    edfs = sorted((SB_DIR / "EDF").glob("ID-*.edf"), key=lambda p: int(p.stem.split("-")[1]))
    rows = pd.read_parquet(MORPH_CACHE).to_dict("records") if MORPH_CACHE.exists() else []
    done = {r["key"] for r in rows}
    for p in edfs:
        key = f"ID{int(p.stem.split('-')[1]):03d}"
        if key in done:
            continue
        try:
            r = rec_morph(p, age.get(key, np.nan)); r["key"] = key; rows.append(r); print(f"  morph {key}", flush=True)
        except Exception as e:
            print(f"  morph {key} FAIL {type(e).__name__}: {e}", flush=True)
        if len(rows) % 10 == 0:                                                      # checkpoint so a hang doesn't lose work
            pd.DataFrame(rows).to_parquet(MORPH_CACHE, index=False)
    df = pd.DataFrame(rows); df.to_parquet(MORPH_CACHE, index=False)
    return df


def evalset(name, y, scores, wide):
    pts = m46.expert_points(wide)
    for lab, s in scores.items():
        ok = np.isfinite(s) & np.isfinite(y)
        cur = m54.panel_curve(None, y[ok], np.asarray(s)[ok], pts, "#000", "x")
        print(f"  {name:14s} {lab:22s} AUROC {cur['auc']:.3f}  {cur['ur']:.0f}% under")


def main():
    morph = build_morph()
    # finer spectral features for Sandor (from segment_master, via scripts/64)
    SM = "data/derived/segment_master"
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    age = {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}
    sbn = lambda nm: int(nm.split("=")[1].split("_")[1])
    sb_ids = [(o.name.split("=")[1], age.get(f"ID{sbn(o.name):03d}", np.nan)) for o in sorted(Path(SM).glob("eeg_id=SB_*"))]
    spec = m64.build(sb_ids); spec["key"] = [f"ID{int(i.split('_')[1]):03d}" for i in spec.index]
    ff = pd.read_excel(MR / "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); ff["key"] = ff.file_name.astype(str).str.strip()
    R = spec.merge(morph, on="key", suffixes=("", "_m")).merge(ff, on="key")
    y = R.majority.astype(int).values
    wide = R.set_index("key")[[c for c in ff.columns if c.startswith("expert_")]].apply(pd.to_numeric, errors="coerce")
    SPEC = [c for c in spec.columns if c not in ("key",) and not c.endswith("_m")]
    MORPH = [c for c in morph.columns if c.startswith("m_")]

    # 50/50 focal-stratified split, evaluate on the held-out half (vs SCORE-AI/Morgoth on the same half)
    rng = np.random.default_rng(0); idx = np.arange(len(R))
    pos, neg = idx[y == 1], idx[y == 0]; rng.shuffle(pos); rng.shuffle(neg)
    te = np.concatenate([pos[:len(pos)//2], neg[:len(neg)//2]]); tr = np.setdiff1d(idx, te)
    print(f"Sandor 50/50: train {len(tr)} ({int(y[tr].sum())} focal) | test {len(te)} ({int(y[te].sum())} focal)")
    for fset, cs in [("spectral finer", SPEC), ("morphology", MORPH), ("spectral+morphology", SPEC + MORPH)]:
        cs = [c for c in cs if c in R.columns]; med = R.iloc[tr][cs].median()
        h = m54.Head().fit(R.iloc[tr][cs].fillna(med).values, y[tr])
        s = h.score(R.iloc[te][cs].fillna(med).values)
        wte = wide.iloc[te]
        print(f"\n[{fset}] on held-out Sandor half:")
        evalset("Sandor-test", y[te], {"ours": s, "Morgoth": R.iloc[te].M_pred.values, "SCORE-AI": R.iloc[te].S_pred.values}, wte)


if __name__ == "__main__":
    main()
