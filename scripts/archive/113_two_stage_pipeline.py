#!/usr/bin/env python3
"""THE TWO-STAGE SYSTEM, run end to end — gate, then describe, then audit the disagreements.

STAGE 1 — MORGOTH GATES (per recording). His two EEG-level heads are INDEPENDENT binary sigmoids, so a
recording lands in exactly one of four cells: neither / focal only / generalized only / BOTH. We never
describe slowing in a recording the gate did not flag.

STAGE 2 — OUR FEATURES DESCRIBE, and only along the axis the gate opened:
  gate says GENERALIZED -> amount (how slow), prevalence (how much of the record), persistence
                           (continuous vs intermittent: longest run, n episodes), and the
                           anterior-posterior gradient (frontally vs posteriorly predominant).
  gate says FOCAL       -> lateralization (which side) and region (which lobe).
Both are computed per SEGMENT against that segment's OWN (age, stage) normal curve, so the descriptors mean
the same thing in wake and in N3.

STAGE 3 — THE DISCORDANCE AUDIT (the point of the exercise). Of the recordings the gate flagged, what
fraction show NO feature evidence of the thing it flagged? Those are cases where Morgoth and our normative
field disagree, and an honest system reports that number instead of hiding it. Nobody publishes this.

Discordance is defined against the NORMAL population, not against a hand-picked cut:
  no generalized evidence  <- prevalence <= the rate clean-normals show BY CONSTRUCTION (5%: the z_crit is
                              the 95th centile of clean-normal segments in that stage) AND amount z < z_crit
  no focal evidence        <- every homologous asymmetry lies inside the clean-normal asymmetry range
                              (|asym z| < 1.645). Asymmetry is age-INVARIANT (P8a), so no age term is needed.

Run: PYTHONPATH=src python scripts/113_two_stage_pipeline.py
"""
from __future__ import annotations
from pathlib import Path
import glob, json, os, sys
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from sklearn.metrics import roc_curve

SM = "data/derived/segment_master"
STAGES = ["W", "N1", "N2", "N3", "REM"]
FEATS = ["log_delta", "log_TAR", "log_DAR"]          # higher = more slowing
SEG_STEP_S = 14.0                                     # segment step (15 s window, 14 s step)

# double-banana chains split front/back — 9 anterior vs 9 posterior
ANT = ["Fp1-F7", "F7-T3", "Fp1-F3", "F3-C3", "Fp2-F8", "F8-T4", "Fp2-F4", "F4-C4", "Fz-Cz"]
POS = ["T3-T5", "T5-O1", "C3-P3", "P3-O1", "T4-T6", "T6-O2", "C4-P4", "P4-O2", "Cz-Pz"]
LEFT = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp1-F3", "F3-C3", "C3-P3", "P3-O1"]
RIGHT = ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2"]
LOBES = {"L_temporal": ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"],
         "R_temporal": ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],
         "L_parasagittal": ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"],
         "R_parasagittal": ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"]}
REGIONS = {"whole_head": None, "anterior": ANT, "posterior": POS, "left": LEFT, "right": RIGHT, **LOBES}

NORM = None      # (stage, region, feat) -> (grid, mu, sd);  loaded per worker process


# ---------------------------------------------------------------------------- per-recording segment table
def seg_regions(f):
    """segment_master partition -> per-SEGMENT region means of the 3 slowing features."""
    d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel"] + FEATS)
    d = d[~d.artifact_flag.astype(bool)]
    if d.empty:
        return None
    out = {}
    for reg, chans in REGIONS.items():
        s = d if chans is None else d[d.channel.isin(chans)]
        if s.empty:
            continue
        g = s.groupby("segment", observed=True)[FEATS].mean()
        out[reg] = g
    if "whole_head" not in out:
        return None
    base = d.groupby("segment", observed=True).stage.first()
    return out, base


def fit_norm(age, val, bw=8.0, grid=np.arange(0, 91, 1.0)):
    ok = np.isfinite(age) & np.isfinite(val)
    a, v = np.asarray(age)[ok], np.asarray(val)[ok]
    if len(a) < 50:
        return None
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((a - g) / bw) ** 2); sw = w.sum()
        if sw < 20:
            continue
        m = (w * v).sum() / sw
        mu[j] = m
        sd[j] = np.sqrt(max((w * (v - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return (grid[good], mu[good], sd[good]) if good.sum() >= 10 else None


def z_of(nrm, age, val):
    g, mu, sd = nrm
    return (np.asarray(val, float) - np.interp(age, g, mu)) / np.interp(age, g, sd)


# ---------------------------------------------------------------------------- PASS A: build the norm
def _norm_one(args):
    f, age = args
    r = seg_regions(f)
    if r is None:
        return None
    out, base = r
    rows = []
    for reg, g in out.items():
        sub = g.join(base.rename("stage"))
        if len(sub) > 300:                      # cap overnight records so they don't dominate the norm
            sub = sub.sample(300, random_state=0)
        for st, ss in sub.groupby("stage", observed=True):
            for ft in FEATS:
                v = ss[ft].values
                v = v[np.isfinite(v)]
                if len(v):
                    rows.append((reg, st, ft, float(age), v))
    return rows


def build_norm(ref_ids, ages):
    files = [(f"{SM}/eeg_id={i}/part.parquet", ages[i]) for i in ref_ids
             if os.path.exists(f"{SM}/eeg_id={i}/part.parquet")]
    print(f"PASS A — normative reference from {len(files):,} clean-normal recordings ...", flush=True)
    acc = {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        for k, rows in enumerate(ex.map(_norm_one, files, chunksize=16)):
            if rows:
                for reg, st, ft, age, v in rows:
                    acc.setdefault((st, reg, ft), []).append((age, v))
            if (k + 1) % 500 == 0:
                print(f"   {k+1:,}/{len(files):,}", flush=True)
    norm = {}
    for key, lst in acc.items():
        ages_v = np.concatenate([np.full(len(v), a) for a, v in lst])
        vals = np.concatenate([v for _, v in lst])
        n = fit_norm(ages_v, vals)
        if n is not None:
            norm[key] = n
    print(f"   fitted {len(norm)} (stage x region x feature) normative curves")
    return norm


# ---------------------------------------------------------------------------- PASS B: describe a recording
def _init(norm_path, zcrit_path=None):
    """Worker initialiser. ProcessPoolExecutor does not inherit module globals set in the parent (fork
    aside, this must be explicit or the workers silently fall back to the 1.645 default)."""
    global NORM, Z_CRIT
    with open(norm_path) as fh:
        raw = json.load(fh)
    NORM = {tuple(k.split("|")): (np.array(v[0]), np.array(v[1]), np.array(v[2])) for k, v in raw.items()}
    if zcrit_path and os.path.exists(zcrit_path):
        Z_CRIT = json.load(open(zcrit_path))


def _slow_z(reg_tab, stages, age, reg):
    """mean z over the 3 slowing features, per segment, for one region."""
    acc, k = None, 0
    for ft in FEATS:
        z = np.full(len(reg_tab), np.nan)
        for st in np.unique(stages):
            key = (st, reg, ft)
            if key not in NORM:
                continue
            m = stages == st
            z[m] = z_of(NORM[key], age, reg_tab[ft].values[m])
        acc = z if acc is None else acc + z
        k += 1
    return acc / max(k, 1)


def _runs(mask):
    """longest consecutive run and number of episodes in a boolean segment mask."""
    if not mask.any():
        return 0, 0
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    lens = ends - starts
    return int(lens.max()), int(len(lens))


def _describe(args):
    f, eid, age = args
    try:
        r = seg_regions(f)
        if r is None:
            return None
        out, base = r
        stages = base.reindex(out["whole_head"].index).values.astype(object)
        rec = {"eeg_id": eid, "n_usable": int(len(out["whole_head"]))}

        zwh = _slow_z(out["whole_head"], stages, age, "whole_head")
        ok = np.isfinite(zwh)
        if ok.sum() < 5:
            return None
        rec["amount_z"] = float(np.median(zwh[ok]))

        # z_crit is per stage (95th centile of clean-normal segments) -> prevalence & persistence
        zc = np.array([Z_CRIT.get(s, 1.645) for s in stages], float)
        abn = np.zeros(len(zwh), bool)
        abn[ok] = zwh[ok] > zc[ok]
        rec["prevalence"] = float(abn[ok].mean())
        rec["severity_when_present"] = float(np.median(zwh[ok & abn])) if (ok & abn).any() else np.nan
        lr, ne = _runs(abn)
        rec["longest_run_min"] = round(lr * SEG_STEP_S / 60.0, 2)
        rec["n_episodes"] = ne
        rec["median_episode_min"] = round((abn.sum() / ne) * SEG_STEP_S / 60.0, 2) if ne else 0.0

        # anterior-posterior gradient (generalized branch)
        za = _slow_z(out["anterior"], stages, age, "anterior") if "anterior" in out else np.array([np.nan])
        zp = _slow_z(out["posterior"], stages, age, "posterior") if "posterior" in out else np.array([np.nan])
        rec["ap_gradient"] = float(np.nanmedian(za) - np.nanmedian(zp))

        # lateralisation + lobe (focal branch)
        zl = _slow_z(out["left"], stages, age, "left") if "left" in out else np.array([np.nan])
        zr = _slow_z(out["right"], stages, age, "right") if "right" in out else np.array([np.nan])
        rec["lr_diff"] = float(np.nanmedian(zl) - np.nanmedian(zr))
        for lobe in LOBES:
            rec[f"z_{lobe}"] = float(np.nanmedian(_slow_z(out[lobe], stages, age, lobe))) \
                if lobe in out else np.nan
        rec["asym_temporal"] = rec["z_L_temporal"] - rec["z_R_temporal"]
        rec["asym_parasag"] = rec["z_L_parasagittal"] - rec["z_R_parasagittal"]
        # per-stage amount, for the stage-accentuation descriptor
        for st in STAGES:
            m = (stages == st) & ok
            rec[f"amount_{st}"] = float(np.median(zwh[m])) if m.sum() >= 3 else np.nan
        return rec
    except Exception:
        return None


Z_CRIT = {}


def main():
    global Z_CRIT
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    ages = dict(zip(lab.eeg_id, lab.age))
    ref = lab[(lab.clean_normal == True) & (lab.clean_pair == True) & lab.age.notna()]   # noqa: E712
    ref_ids = ref.eeg_id.tolist()
    if len(ref_ids) > 3000:
        ref_ids = list(pd.Series(ref_ids).sample(3000, random_state=0))

    npath = "data/derived/seg_norm.json"
    if not os.path.exists(npath):
        norm = build_norm(ref_ids, ages)
        json.dump({"|".join(k): [v[0].tolist(), v[1].tolist(), v[2].tolist()] for k, v in norm.items()},
                  open(npath, "w"))
    _init(npath)
    print(f"normative curves: {len(NORM)}")

    # z_crit per stage = 95th centile of clean-normal WHOLE-HEAD segment z (empirical, not assumed Gaussian)
    zc_path = "data/derived/seg_zcrit.json"
    if os.path.exists(zc_path):
        Z_CRIT = json.load(open(zc_path))
    else:
        pool = {s: [] for s in STAGES}
        for i in ref_ids[:800]:
            f = f"{SM}/eeg_id={i}/part.parquet"
            if not os.path.exists(f):
                continue
            r = seg_regions(f)
            if r is None:
                continue
            out, base = r
            st = base.reindex(out["whole_head"].index).values.astype(object)
            z = _slow_z(out["whole_head"], st, ages[i], "whole_head")
            for s in STAGES:
                v = z[(st == s) & np.isfinite(z)]
                if len(v):
                    pool[s].append(v)
        Z_CRIT = {s: float(np.percentile(np.concatenate(v), 95)) for s, v in pool.items() if v}
        json.dump(Z_CRIT, open(zc_path, "w"))
    print("z_crit (95th centile of clean-normal segments):",
          {k: round(v, 2) for k, v in Z_CRIT.items()})

    # ---------------- PASS B: describe every recording
    dpath = "data/derived/two_stage_descriptors.parquet"
    if os.path.exists(dpath):
        D = pd.read_parquet(dpath)
    else:
        items = [(f"{SM}/eeg_id={i}/part.parquet", i, ages.get(i))
                 for i in lab.eeg_id if os.path.exists(f"{SM}/eeg_id={i}/part.parquet")
                 and pd.notna(ages.get(i))]
        print(f"\nPASS B — describing {len(items):,} recordings ...", flush=True)
        rows = []
        with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2),
                                 initializer=_init, initargs=(npath, zc_path)) as ex:
            for k, r in enumerate(ex.map(_describe, items, chunksize=16)):
                if r:
                    rows.append(r)
                if (k + 1) % 2500 == 0:
                    print(f"   {k+1:,}/{len(items):,}", flush=True)
        D = pd.DataFrame(rows)
        D.to_parquet(dpath, index=False)
    print(f"descriptors: {D.shape} -> {dpath}")


if __name__ == "__main__":
    main()
