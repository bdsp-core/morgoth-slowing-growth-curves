#!/usr/bin/env python3
"""Per-recording descriptor GRID — the substrate for a two-level, per-feature, harmonisable firing rule.

WHY THIS REPLACES scripts/113's descriptor block. That version had three defects, all of MBW's diagnosis:

  1. INTERMITTENCY WASHOUT (a bug, not a choice). "Evidence" required `amount_z` — the median z over ALL
     segments — to be low. In a recording with intermittent slowing the normal segments outvote the abnormal
     ones, so amount_z is near zero BY CONSTRUCTION. 71.4% of the recordings it called "no evidence" in fact
     contained slow segments, at median severity +1.54 when present. The statistic answered "is this EEG slow
     ALL the time", which is the wrong question: intermittency is a thing to DESCRIBE, not a reason to say
     nothing is there.
     FIX: a two-level rule. A SEGMENT fires if a feature's z exceeds X. The RECORDING fires if at least Y% of
     its segments fire. Severity leaves the firing rule and becomes CONDITIONAL severity — the median z among
     the FIRING segments only. Prevalence / persistence / severity are descriptors, not gatekeepers.

  2. X AND Y WERE PICKED BY FIAT (the 95th centile). Both are free parameters. They are stored here on a GRID
     so scripts/116 can choose them to maximise agreement with Morgoth — fit on a patient-split train half,
     reported on a held-out test half. The residual discordance is then the BEST ACHIEVABLE agreement, not an
     artefact of an arbitrary threshold.

  3. FEATURES WERE AVERAGED TOGETHER. log_delta / log_TAR / log_DAR were collapsed into one z, so a recording
     with isolated delta excess and normal ratios was diluted. Each feature now gets its own z, its own firing
     decision, and its own line in the description. "Evidence" = ANY feature fires; the description says WHICH.

WHAT IS STORED, per recording, for every (feature x region x threshold X) on the grid:
    prev   fraction of usable segments whose z exceeds X          -> prevalence / ACNS word
    sev    median z among the FIRING segments only                -> conditional severity ("how much")
    run    longest consecutive firing run, in minutes             -> persistence
    eps    number of firing episodes                              -> intermittency
and for the homologous pairs, the same on the per-segment ASYMMETRY z (left-right), plus the signed side.

Directions: the slowing features fire on the UPPER tail; alpha/beta paucity fires on the LOWER tail. Both are
expressed as a single "abnormality z" (zz), so zz > X always means "abnormal in this feature's own direction".

Run: PYTHONPATH=src python scripts/115_descriptor_grid.py
"""
from __future__ import annotations
from pathlib import Path
import json, os
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor

SM = "data/derived/segment_master"
STAGES = ["W", "N1", "N2", "N3", "REM"]
SEG_STEP_S = 14.0

# A SMALL SET OF INDEPENDENT STATEMENTS about *how* the EEG is abnormal. Each is evaluated on its own.
UP = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR"]   # abnormal when HIGH
DOWN = ["rel_alpha"]                                                  # abnormal when LOW (paucity of alpha)
FEATS = UP + DOWN
LABEL = {"log_delta": "delta excess", "log_theta": "theta excess", "rel_delta": "relative delta excess",
         "log_DAR": "delta/alpha ratio", "log_TAR": "theta/alpha ratio", "rel_alpha": "paucity of alpha"}

ANT = ["Fp1-F7", "F7-T3", "Fp1-F3", "F3-C3", "Fp2-F8", "F8-T4", "Fp2-F4", "F4-C4", "Fz-Cz"]
POS = ["T3-T5", "T5-O1", "C3-P3", "P3-O1", "T4-T6", "T6-O2", "C4-P4", "P4-O2", "Cz-Pz"]
LOBES = {"L_temporal": ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"],
         "R_temporal": ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],
         "L_parasagittal": ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"],
         "R_parasagittal": ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"]}
REGIONS = {"whole_head": None, "anterior": ANT, "posterior": POS, **LOBES}
PAIRS = [("L_temporal", "R_temporal"), ("L_parasagittal", "R_parasagittal")]

# X grid: the SEGMENT threshold, in z units. scripts/116 picks one (and a Y) to match Morgoth.
XG = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

NORM = None      # (stage, region, feat) -> (grid, mu, sd)
ANORM = None     # (stage, pair, feat)   -> (mu, sd)   [asymmetry is age-INVARIANT — P8a]


def _cols(f):
    return list({*FEATS})


def seg_regions(f):
    d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel"] + FEATS)
    d = d[~d.artifact_flag.astype(bool)]
    if d.empty:
        return None
    out = {}
    for reg, chans in REGIONS.items():
        s = d if chans is None else d[d.channel.isin(chans)]
        if not s.empty:
            out[reg] = s.groupby("segment", observed=True)[FEATS].mean()
    if "whole_head" not in out:
        return None
    return out, d.groupby("segment", observed=True).stage.first()


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


def z_of(n, age, val):
    g, mu, sd = n
    return (np.asarray(val, float) - np.interp(age, g, mu)) / np.interp(age, g, sd)


# ------------------------------------------------------------------ PASS A
def _norm_one(args):
    f, age = args
    r = seg_regions(f)
    if r is None:
        return None
    out, base = r
    rows = []
    for reg, g in out.items():
        sub = g.join(base.rename("stage"))
        if len(sub) > 250:
            sub = sub.sample(250, random_state=0)
        for st, ss in sub.groupby("stage", observed=True):
            for ft in FEATS:
                v = ss[ft].values
                v = v[np.isfinite(v)]
                if len(v):
                    rows.append(("R", reg, st, ft, float(age), v))
    # asymmetries (L - R), per segment
    for a, b in PAIRS:
        if a not in out or b not in out:
            continue
        j = out[a].join(out[b], lsuffix="_L", rsuffix="_R").join(base.rename("stage"))
        if len(j) > 250:
            j = j.sample(250, random_state=0)
        for st, ss in j.groupby("stage", observed=True):
            for ft in FEATS:
                v = (ss[f"{ft}_L"] - ss[f"{ft}_R"]).values
                v = v[np.isfinite(v)]
                if len(v):
                    rows.append(("A", f"{a}|{b}", st, ft, float(age), v))
    return rows


def build_norms(ref_ids, ages):
    files = [(f"{SM}/eeg_id={i}/part.parquet", ages[i]) for i in ref_ids
             if os.path.exists(f"{SM}/eeg_id={i}/part.parquet")]
    print(f"PASS A — norms from {len(files):,} clean-normal recordings ...", flush=True)
    accR, accA = {}, {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        for k, rows in enumerate(ex.map(_norm_one, files, chunksize=16)):
            if not rows:
                continue
            for kind, key, st, ft, age, v in rows:
                (accR if kind == "R" else accA).setdefault((st, key, ft), []).append((age, v))
            if (k + 1) % 750 == 0:
                print(f"   {k+1:,}/{len(files):,}", flush=True)
    norm = {}
    for key, lst in accR.items():
        a = np.concatenate([np.full(len(v), ag) for ag, v in lst])
        v = np.concatenate([x for _, x in lst])
        n = fit_norm(a, v)
        if n is not None:
            norm[key] = n
    anorm = {}
    for key, lst in accA.items():
        v = np.concatenate([x for _, x in lst])
        # asymmetry is age-INVARIANT (P8a): a single mean/sd, no age term
        anorm[key] = (float(np.mean(v)), float(np.std(v) or 1.0))
    print(f"   fitted {len(norm)} regional curves + {len(anorm)} asymmetry norms")
    return norm, anorm


# ------------------------------------------------------------------ PASS B
def _init(np_, ap_):
    global NORM, ANORM
    raw = json.load(open(np_))
    NORM = {tuple(k.split("|")): (np.array(v[0]), np.array(v[1]), np.array(v[2])) for k, v in raw.items()}
    ra = json.load(open(ap_))
    ANORM = {tuple(k.split("~")): tuple(v) for k, v in ra.items()}


def _zz(tab, stages, age, reg, ft):
    """abnormality z: high = abnormal, in this feature's OWN direction."""
    z = np.full(len(tab), np.nan)
    for st in np.unique(stages):
        key = (st, reg, ft)
        if key not in NORM:
            continue
        m = stages == st
        z[m] = z_of(NORM[key], age, tab[ft].values[m])
    return -z if ft in DOWN else z


def _runs(mask):
    if not mask.any():
        return 0, 0
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    lens = np.where(d == -1)[0] - np.where(d == 1)[0]
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
        if rec["n_usable"] < 5:
            return None

        for reg in REGIONS:
            if reg not in out:
                continue
            for ft in FEATS:
                zz = _zz(out[reg], stages, age, reg, ft)
                ok = np.isfinite(zz)
                if ok.sum() < 5:
                    continue
                z = zz[ok]
                for X in XG:
                    fire = z > X
                    tag = f"{ft}|{reg}|{X}"
                    rec[f"prev|{tag}"] = float(fire.mean())
                    if reg == "whole_head":
                        rec[f"sev|{tag}"] = float(np.median(z[fire])) if fire.any() else np.nan
                        lr, ne = _runs(fire)
                        rec[f"run|{tag}"] = float(lr * SEG_STEP_S / 60.0)
                        rec[f"eps|{tag}"] = float(ne)

        for a, b in PAIRS:
            if a not in out or b not in out:
                continue
            pk = f"{a}|{b}"
            for ft in FEATS:
                d_ = (out[a][ft] - out[b][ft]).values
                az = np.full(len(d_), np.nan)
                for st in np.unique(stages):
                    key = (st, pk, ft)
                    if key not in ANORM:
                        continue
                    mu, sd = ANORM[key]
                    m = stages == st
                    az[m] = (d_[m] - mu) / (sd or 1.0)
                ok = np.isfinite(az)
                if ok.sum() < 5:
                    continue
                z = az[ok]
                for X in XG:
                    fire = np.abs(z) > X
                    tag = f"{ft}|{pk}|{X}"
                    rec[f"aprev|{tag}"] = float(fire.mean())
                    # signed side among the firing segments: + = LEFT worse, - = RIGHT worse
                    rec[f"aside|{tag}"] = float(np.mean(np.sign(z[fire]))) if fire.any() else np.nan
        return rec
    except Exception:
        return None


def main():
    lab = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    ages = dict(zip(lab.eeg_id, lab.age))
    ref = lab[(lab.clean_normal == True) & (lab.clean_pair == True) & lab.age.notna()]   # noqa: E712
    ref_ids = ref.eeg_id.tolist()
    if len(ref_ids) > 3000:
        ref_ids = list(pd.Series(ref_ids).sample(3000, random_state=0))

    NP_, AP_ = "data/derived/grid_norm.json", "data/derived/grid_anorm.json"
    if not (os.path.exists(NP_) and os.path.exists(AP_)):
        norm, anorm = build_norms(ref_ids, ages)
        json.dump({"|".join(k): [v[0].tolist(), v[1].tolist(), v[2].tolist()] for k, v in norm.items()},
                  open(NP_, "w"))
        json.dump({"~".join(k): list(v) for k, v in anorm.items()}, open(AP_, "w"))
    _init(NP_, AP_)
    print(f"norms: {len(NORM)} regional, {len(ANORM)} asymmetry")

    items = [(f"{SM}/eeg_id={i}/part.parquet", i, ages.get(i)) for i in lab.eeg_id
             if os.path.exists(f"{SM}/eeg_id={i}/part.parquet") and pd.notna(ages.get(i))]
    print(f"\nPASS B — descriptor grid for {len(items):,} recordings "
          f"({len(FEATS)} features x {len(REGIONS)} regions x {len(XG)} thresholds) ...", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2),
                             initializer=_init, initargs=(NP_, AP_)) as ex:
        for k, r in enumerate(ex.map(_describe, items, chunksize=16)):
            if r:
                rows.append(r)
            if (k + 1) % 2500 == 0:
                print(f"   {k+1:,}/{len(items):,}", flush=True)
    D = pd.DataFrame(rows)
    for c in D.columns:
        if c != "eeg_id":
            D[c] = D[c].astype("float32")
    D.to_parquet("data/derived/descriptor_grid.parquet", index=False)
    print(f"\nwrote data/derived/descriptor_grid.parquet  {D.shape}")


if __name__ == "__main__":
    main()
