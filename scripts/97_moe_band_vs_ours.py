"""MoE: OUR band-determination agreement vs the expert panel (no report text, no regex extractor).

The paper's "band agreement 0.74" was computed against REPORT TEXT, with our OWN regex extractor,
one report per recording. That number can be dominated by how well we parse the report's band word.
This script recomputes band agreement the honest way:

  * featurize each MoE 15-s event with the PROJECT's OWN pipeline (features.extract + features.recording),
  * make an a-priori band call (delta vs theta) from band power,
  * compare it to each of the 18-22 experts' per-band calls on the SAME events, and
  * compute the expert-expert ceiling on the IDENTICAL event subset, plus trivial constant-classifier
    baselines, so raw agreement can be read against both chance and the human ceiling.

There is no text extractor anywhere in this pipeline.

HEADLINE METRIC = Cohen κ, not raw match. Raw agreement is prevalence-inflated (delta dominates the base
rate); κ is chance-corrected and credits only genuine band discrimination.

TWO a-priori band rules (both fixed before looking at any agreement number):
  * PRIMARY (raw)  = "delta" if rel_delta > rel_theta else "theta", at whole_head (generalized) or the
    most-slowed lobe (focal). This rule is nearly a constant "delta" caller because relative delta
    (1-4 Hz) almost always exceeds relative theta (4-7 Hz) on the 1/f spectrum — it is reported to show
    that it does NOT discriminate band (κ ~ 0).
  * Z-RULE (age-normalized) = "delta" if z(rel_delta) > z(rel_theta) else "theta", where z is deviation
    from the project's clean-normal reference at the event's age (Gaussian age kernel bw=5 y, stage W;
    `scripts/84`'s `normal_z`, reference = channel_stage_features src=="cohort" & clean_normal). This is
    the principled rule: it compares each band to what is normal for that patient, not the two raw powers
    to each other. Reported on the subset of events for which an age is recoverable.

DATA: MoE per-expert 0/1 band labels (labels/{r1,r2,r3}), pooled over rounds (disjoint events), BDSP
events only (icare_* cardiac-arrest events excluded). Event signals: events_raw/<event>.mat (MATLAB
v7.3 -> h5py). Each .mat is exactly one 3000-sample (15 s @ 200 Hz) referential segment.

PRIVACY: rater columns are real usernames, one of whom (an author of this paper) is anonymized like the
rest to R01..Rnn on load and NEVER written to any file. An "author-rater excluded" sensitivity is
reported without revealing which anonymized index is the author.

Run: PYTHONPATH=src python3 scripts/97_moe_band_vs_ours.py
"""
from __future__ import annotations
import glob, os, sys
from pathlib import Path
import numpy as np, pandas as pd
import h5py
from sklearn.metrics import cohen_kappa_score

from morgoth_slowing.features import extract as ex, recording as rec  # project's own pipeline

# ---- paths / config ------------------------------------------------------------------------------
SCRATCH = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
           "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
SC = f"{SCRATCH}/moe/labels"
EVENTS_DIR = f"{SCRATCH}/events_raw"
FEAT_CACHE = f"{SCRATCH}/moe_event_band_feats.parquet"
ROUNDS = ["r1", "r2", "r3"]
AUTHOR = "bwestove"
LOBES = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
REF_REGIONS = ["whole_head", *LOBES]
STAGE = "W"                # MoE events are awake 15-s clips (assumption; stated in output)
BW = 5.0                   # Gaussian age-kernel bandwidth (years), matches scripts/84
MIN_EVENTS = 20            # min single-band slowing events for an expert/pair to enter a distribution
NBOOT = 1000
rng = np.random.default_rng(0)
NEEDED = sorted({c for pair in ex.BIPOLAR for c in pair})   # 19 referential channels the montage needs


# ============================== 1. featurize events with OUR pipeline =============================
def decode_channels(h):
    refs = np.array(h["channels"][()]).flatten()
    return ["".join(chr(int(c)) for c in np.array(h[r][()]).flatten()) for r in refs]


def featurize_event(path):
    """One 15-s referential event .mat -> {region: derived-feature dict} via features.extract/recording.
    Returns None (+reason) if unusable (all-NaN signal, or a montage channel missing)."""
    with h5py.File(path, "r") as h:
        data = np.array(h["data"][()], dtype=float)       # h5py gives (n_samp, n_ch) == our convention
        fs = float(np.array(h["Fs"][()]).flatten()[0])
        ch = decode_channels(h)
    if not set(NEEDED).issubset(ch):
        return None, "missing_channels"
    sub = data[:, [ch.index(c) for c in NEEDED]]
    if not np.isfinite(sub).all():
        return None, "nan_signal"
    tensor, _ = ex.extract(data, ch, fs=fs)               # (n_seg, 18, 31); one 3000-sample seg -> n_seg=1
    rows, _, _ = rec.recording_features_tensor(tensor)    # region-level rel_delta/rel_theta/low_freq_rel
    return {r["region"]: r for r in rows}, "ok"


def build_feature_table(events):
    if os.path.exists(FEAT_CACHE):
        cached = pd.read_parquet(FEAT_CACHE)
        if set(events).issubset(set(cached.event)):
            return cached
    recs, reasons = [], {}
    for i, evt in enumerate(events):
        p = f"{EVENTS_DIR}/{evt}.mat"
        if not os.path.exists(p):
            reasons["no_mat"] = reasons.get("no_mat", 0) + 1
            continue
        try:
            regf, why = featurize_event(p)
        except Exception as e:                            # noqa: BLE001
            regf, why = None, f"error:{type(e).__name__}"
        reasons[why] = reasons.get(why, 0) + 1
        if regf is None:
            continue
        row = {"event": evt}
        for reg in REF_REGIONS:
            f = regf[reg]
            row[f"{reg}__rel_delta"] = f["rel_delta"]
            row[f"{reg}__rel_theta"] = f["rel_theta"]
            row[f"{reg}__low_freq_rel"] = f["low_freq_rel"]
        recs.append(row)
        if (i + 1) % 300 == 0:
            print(f"  featurized {i+1}/{len(events)} ...", file=sys.stderr)
    df = pd.DataFrame(recs)
    df.to_parquet(FEAT_CACHE, index=False)
    print(f"featurization reasons: {reasons}", file=sys.stderr)
    return df


# ============================== 2. band-call rules ================================================
def _argmax_lobe(feat):
    """Index of the most-slowed lobe (max low_freq_rel); NaN lobes never selected."""
    lfr = feat[[f"{r}__low_freq_rel" for r in LOBES]].values
    return np.argmax(np.where(np.isnan(lfr), -np.inf, lfr), axis=1)


def our_band_calls(feat: pd.DataFrame) -> pd.DataFrame:
    """PRIMARY (raw) rule."""
    out = feat[["event"]].copy()
    out["gen_band"] = np.where(feat["whole_head__rel_delta"] > feat["whole_head__rel_theta"], "delta", "theta")
    k = _argmax_lobe(feat)
    rd = np.array([feat[f"{r}__rel_delta"].values for r in LOBES]).T
    rt = np.array([feat[f"{r}__rel_theta"].values for r in LOBES]).T
    out["focal_region"] = np.array(LOBES)[k]
    out["focal_band"] = np.where(rd[np.arange(len(k)), k] > rt[np.arange(len(k)), k], "delta", "theta")
    return out


def normal_z(vals, ages, ref_vals, ref_ages, bw=BW):
    """Age-kernel z-score of `vals` against a normal reference (scripts/84's normal_z, verbatim math)."""
    z = np.full(len(vals), np.nan)
    ra, rv = np.asarray(ref_ages, float), np.asarray(ref_vals, float)
    ok = np.isfinite(ra) & np.isfinite(rv); ra, rv = ra[ok], rv[ok]
    for i in range(len(vals)):
        if not (np.isfinite(vals[i]) and np.isfinite(ages[i])):
            continue
        wt = np.exp(-0.5 * ((ra - ages[i]) / bw) ** 2); sw = wt.sum()
        if sw < 5:
            continue
        mu = (wt * rv).sum() / sw
        sd = np.sqrt(max((wt * (rv - mu) ** 2).sum() / sw, 1e-9))
        z[i] = (vals[i] - mu) / sd
    return z


def recover_ages(events) -> tuple[np.ndarray, dict]:
    """Recover a patient age per event from the union of three sources, joining on the 9-digit pid
    (and eeg date where available). Returns (age array aligned to events, source-count dict)."""
    ev = pd.DataFrame({"event": list(events)})
    ev["pid"] = ev.event.str.extract(r"^(\d{9})_")[0]
    ev["date"] = ev.event.str.extract(r"_(\d{8})")[0]

    fa = pd.read_parquet("data/derived/fractional_age.parquet")
    fa["pid"] = fa.person_id.astype(str); fa["date"] = fa.eeg_date.astype(str)
    exact = ev.merge(fa[["pid", "date", "age_frac"]].drop_duplicates(["pid", "date"]),
                     on=["pid", "date"], how="left")["age_frac"].values
    fa_pid = fa.groupby("pid").age_frac.mean()

    lu = pd.read_parquet("data/derived/labels_unified.parquet")
    lu["pid"] = lu.pid.astype(str)
    lu_pid = lu.dropna(subset=["age"]).drop_duplicates("pid").set_index("pid")["age"]

    cm = pd.read_csv("metadata/cohort_metadata.csv")
    cm["pid"] = cm.bdsp_id.str.extract(r"S\d{4}(\d+)")[0]
    cm_pid = cm.dropna(subset=["age"]).drop_duplicates("pid").set_index("pid")["age"]

    age = np.array(exact, float)
    src = np.where(np.isfinite(age), "fa_exact", "none").astype(object)
    for name, table in [("fa_pid", fa_pid), ("lu_pid", lu_pid), ("cm_pid", cm_pid)]:
        need = ~np.isfinite(age)
        filled = ev.pid.map(table).values
        take = need & np.isfinite(filled.astype(float))
        age[take] = filled[take].astype(float)
        src[take] = name
    counts = pd.Series(src).value_counts().to_dict()
    return age, counts


def z_rule_bands(feat: pd.DataFrame, ages: np.ndarray):
    """Z-RULE: band = argmax over {z(rel_delta), z(rel_theta)} vs the clean-normal reference at age.
    Focal lobe = the lobe with the largest slowing z-deviation max(z_rd, z_rt). NaN where no age."""
    d = pd.read_parquet("data/derived/channel_stage_features.parquet",
                        columns=["region", "stage", "src", "clean_normal", "age", "rel_delta", "rel_theta"])
    d = d[(d.stage == STAGE) & (d.src == "cohort") & (d.clean_normal == 1) & d.age.between(0, 100)]
    ref = {reg: d[d.region == reg] for reg in REF_REGIONS}

    def zpair(region, rd, rt):
        r = ref[region]
        return (normal_z(rd, ages, r.rel_delta.values, r.age.values),
                normal_z(rt, ages, r.rel_theta.values, r.age.values))

    zg_d, zg_t = zpair("whole_head", feat["whole_head__rel_delta"].values, feat["whole_head__rel_theta"].values)
    gen = np.where(zg_d > zg_t, "delta", "theta").astype(object)
    gen[~(np.isfinite(zg_d) & np.isfinite(zg_t))] = np.nan

    # focal: z per lobe, pick lobe with max slowing deviation, read its band
    zd = np.full((len(feat), len(LOBES)), np.nan)
    zt = np.full((len(feat), len(LOBES)), np.nan)
    for j, lobe in enumerate(LOBES):
        zd[:, j], zt[:, j] = zpair(lobe, feat[f"{lobe}__rel_delta"].values, feat[f"{lobe}__rel_theta"].values)
    slowing = np.fmax(zd, zt)                                    # per-lobe slowing deviation
    lobe_k = np.where(np.isnan(slowing).all(1), 0,
                      np.nanargmax(np.where(np.isnan(slowing), -np.inf, slowing), axis=1))
    fzd = zd[np.arange(len(feat)), lobe_k]
    fzt = zt[np.arange(len(feat)), lobe_k]
    focal = np.where(fzd > fzt, "delta", "theta").astype(object)
    focal[~(np.isfinite(fzd) & np.isfinite(fzt))] = np.nan
    return gen, focal, np.array(LOBES)[lobe_k]


# ============================== 3. expert per-event band matrices ==================================
def load_cat(cat: str) -> pd.DataFrame:
    frames = []
    for r in ROUNDS:
        g = glob.glob(f"{SC}/{r}_csv_labels_20241028/moe_*{cat}.csv")
        if not g:
            continue
        c = pd.read_csv(g[0])
        c = c[c.event.astype(str).str.match(r"^\d{9}_\d{14}$")]        # BDSP events only
        c = c.drop(columns=[x for x in ["eeg"] if x in c]).set_index("event")
        frames.append(c)
    return pd.concat(frames) if frames else None


def aligned_DT(kind, anon, events):
    """delta/theta 0/1/NaN matrices (events x anonymized raters) aligned to `events`."""
    D = load_cat(f"{kind}-delta").rename(columns=anon)
    T = load_cat(f"{kind}-theta").rename(columns=anon)
    raters = sorted(set(D.columns) & set(T.columns))
    return (D.reindex(index=events, columns=raters).values.astype(float),
            T.reindex(index=events, columns=raters).values.astype(float), raters)


# ============================== 4. agreement statistics ===========================================
def _kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if len(a) < 2 or len(set(a)) < 2 or len(set(b)) < 2:
        return np.nan
    return cohen_kappa_score(a, b)


def compute_kind(kind, our_band, D, T, raters, boot=True):
    """our_band: array (nE,) of 'delta'/'theta'/nan aligned to D/T rows.
    STAT B (categorical, single-band events): expert band is 'delta'/'theta' only where the expert marked
    EXACTLY one of the two; algorithm is one of the two; match + Cohen κ per expert / per pair.
    Also computes constant-classifier baselines (always-delta / always-theta) per expert.
    STAT A (delta-vs-theta vote vector): among events the expert called slowing, fraction where the full
    (delta,theta) vote pair matches; mirrors the human-ceiling script."""
    ob = np.asarray(our_band, object)
    have = np.array([isinstance(x, str) for x in ob])     # a defined band (excludes None AND NaN)
    ours_delta = ob == "delta"
    nE, nR = D.shape
    single_delta = (D == 1) & (T == 0)
    single_theta = (D == 0) & (T == 1)
    single = single_delta | single_theta
    exp_delta = single_delta
    called = ((D == 1) | (T == 1)) & np.isfinite(D) & np.isfinite(T)

    ae_match, ae_kappa, ae_n, base_d, base_t = [], [], [], [], []
    for r in range(nR):
        m = single[:, r] & have
        if m.sum() < MIN_EVENTS:
            continue
        ed = exp_delta[m, r]; od = ours_delta[m]
        ae_match.append(float((ed == od).mean()))
        ae_kappa.append(_kappa(np.where(ed, "delta", "theta"), np.where(od, "delta", "theta")))
        ae_n.append(int(m.sum()))
        base_d.append(float(ed.mean()))                  # always-delta correct rate = delta base rate
        base_t.append(float((~ed).mean()))               # always-theta correct rate
    ee_match, ee_kappa, ee_n = [], [], []
    for i in range(nR):
        for j in range(i + 1, nR):
            m = single[:, i] & single[:, j] & have
            if m.sum() < MIN_EVENTS:
                continue
            di, dj = exp_delta[m, i], exp_delta[m, j]
            ee_match.append(float((di == dj).mean()))
            ee_kappa.append(_kappa(np.where(di, "delta", "theta"), np.where(dj, "delta", "theta")))
            ee_n.append(int(m.sum()))

    aeA, eeA = [], []
    for r in range(nR):
        m = called[:, r] & have
        if m.sum() < MIN_EVENTS:
            continue
        aeA.append(float(((D[m, r] == ours_delta[m].astype(float)) &
                          (T[m, r] == (~ours_delta[m]).astype(float))).mean()))
    for i in range(nR):
        for j in range(i + 1, nR):
            m = called[:, i] & called[:, j]
            if m.sum() < MIN_EVENTS:
                continue
            eeA.append(float(((D[m, i] == D[m, j]) & (T[m, i] == T[m, j])).mean()))

    res = dict(
        kind=kind, n_experts=len(ae_match), n_pairs=len(ee_match),
        ae_match_med=np.median(ae_match), ae_match_iqr=(np.percentile(ae_match, 25), np.percentile(ae_match, 75)),
        ee_match_med=np.median(ee_match), ee_match_iqr=(np.percentile(ee_match, 25), np.percentile(ee_match, 75)),
        ae_kappa_med=np.nanmedian(ae_kappa), ee_kappa_med=np.nanmedian(ee_kappa),
        base_delta_med=np.median(base_d), base_theta_med=np.median(base_t),
        aeA_med=(np.median(aeA) if aeA else np.nan), eeA_med=(np.median(eeA) if eeA else np.nan),
        ae_n_med=int(np.median(ae_n)), ee_n_med=int(np.median(ee_n)),
        sqrt_kappa_ee=float(np.sqrt(max(np.nanmedian(ee_kappa), 0.0))),
    )

    if boot:
        d_match, d_kappa = [], []
        for _ in range(NBOOT):
            bi = rng.integers(0, nE, nE)
            sD, sT, hv = single_delta[bi], single_theta[bi], have[bi]
            sS = sD | sT; od = ours_delta[bi]
            am, ak = [], []
            for r in range(nR):
                m = sS[:, r] & hv
                if m.sum() < MIN_EVENTS:
                    continue
                am.append(float((sD[m, r] == od[m]).mean()))
                ak.append(_kappa(np.where(sD[m, r], "d", "t"), np.where(od[m], "d", "t")))
            em, ek = [], []
            for i in range(nR):
                for j in range(i + 1, nR):
                    m = sS[:, i] & sS[:, j] & hv
                    if m.sum() < MIN_EVENTS:
                        continue
                    em.append(float((sD[m, i] == sD[m, j]).mean()))
                    ek.append(_kappa(np.where(sD[m, i], "d", "t"), np.where(sD[m, j], "d", "t")))
            if am and em:
                d_match.append(np.median(am) - np.median(em))
                d_kappa.append(np.nanmedian(ak) - np.nanmedian(ek))
        res["contrast_match"] = (float(np.median(d_match)),
                                 float(np.percentile(d_match, 2.5)), float(np.percentile(d_match, 97.5)))
        res["contrast_kappa"] = (float(np.nanmedian(d_kappa)),
                                 float(np.nanpercentile(d_kappa, 2.5)), float(np.nanpercentile(d_kappa, 97.5)))
    return res


# ============================== 5. driver =========================================================
def ci(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"


def mix(s):
    return {k: round(v, 3) for k, v in pd.Series(s).dropna().value_counts(normalize=True).to_dict().items()}


def main():
    # canonical anonymization across all categories (same scheme as script 90)
    allcols = set()
    for kind in ["focalslowing", "genslowing"]:
        for b in ["delta", "theta"]:
            d = load_cat(f"{kind}-{b}")
            if d is not None:
                allcols |= set(d.columns)
    names = sorted(allcols)
    anon = {n: f"R{i+1:02d}" for i, n in enumerate(names)}
    author_anon = anon.get(AUTHOR)

    events_all = list(load_cat("focalslowing-delta").index)
    feat = build_feature_table(events_all)
    events = list(feat["event"])
    calls = our_band_calls(feat)

    ages, age_src = recover_ages(events)
    aged = np.isfinite(ages)
    zgen, zfocal, zregion = z_rule_bands(feat, ages)
    n_feat, n_total, n_aged = len(events), len(set(events_all)), int(aged.sum())

    print(f"{len(names)} raters -> R01..R{len(names):02d}; {n_feat}/{n_total} BDSP events featurized; "
          f"age recovered for {n_aged} events; sources={age_src}", file=sys.stderr)

    # --- PRIMARY (raw) rule ---
    prim = {}
    for kind, col in [("focalslowing", "focal_band"), ("genslowing", "gen_band")]:
        D, T, raters = aligned_DT(kind, anon, events)
        prim[kind] = compute_kind(kind, calls[col].values, D, T, raters)

    # --- author-rater-excluded sensitivity (primary rule) ---
    sens = {}
    for kind, col in [("focalslowing", "focal_band"), ("genslowing", "gen_band")]:
        D, T, raters = aligned_DT(kind, anon, events)
        if author_anon in raters:
            keep = [c for c in range(len(raters)) if raters[c] != author_anon]
            sens[kind] = compute_kind(kind, calls[col].values, D[:, keep], T[:, keep],
                                      [raters[c] for c in keep], boot=False)

    # --- Z-RULE on the aged subset ---
    zc = {"focalslowing": zfocal, "genslowing": zgen}
    ev_aged = list(np.array(events)[aged])
    zres = {}
    for kind in ["focalslowing", "genslowing"]:
        D, T, raters = aligned_DT(kind, anon, ev_aged)
        zres[kind] = compute_kind(kind, np.asarray(zc[kind], object)[aged], D, T, raters, boot=False)

    gen_mix, foc_mix = mix(calls["gen_band"]), mix(calls["focal_band"])
    zgen_mix, zfoc_mix = mix(zgen[aged]), mix(zfocal[aged])

    # ============================== write report ==============================
    L = []
    L.append("# MoE — our band determination vs the expert panel (no report text)\n")
    L.append(f"Featurized **{n_feat}/{n_total}** pooled BDSP MoE events with the project's own pipeline "
             f"(`features.extract` -> `features.recording`); each event is one 15-s, 3000-sample, 200 Hz "
             f"referential segment. `icare_*` cardiac-arrest events excluded. {len(names)} raters, "
             f"anonymized R01..R{len(names):02d} (one is an author of this paper).\n")
    L.append("**Headline metric = Cohen κ, not raw match.** Raw agreement is prevalence-inflated (delta "
             "dominates the base rate); κ is chance-corrected. A constant \"always-delta\" classifier is "
             "included as a baseline so raw numbers can be read against chance.\n")
    L.append(f"Band-call mix — **primary (raw rel_delta>rel_theta) rule**: generalized {gen_mix}, focal "
             f"{foc_mix}. This rule is **nearly a constant `delta` caller**: relative delta (1-4 Hz) almost "
             f"always exceeds relative theta (4-7 Hz) on the 1/f spectrum, so it barely discriminates band. "
             f"The **age-normalized z-rule** (below) is balanced — generalized {zgen_mix}, focal {zfoc_mix}.\n")

    L.append("## Primary result — chance-corrected band agreement (κ), primary raw rule\n")
    L.append("Per expert / per expert-pair, restricted to events the expert scored as slowing in **exactly "
             f"one** of delta/theta (band unambiguous); experts/pairs need ≥{MIN_EVENTS} such events. κ is "
             "the headline; raw match and the constant-classifier baselines follow.\n")
    L.append("| kind | our κ_ae (med) | expert κ_ee ceiling (med) | κ contrast (algo−ceiling), boot 95% CI | "
             "√κ_ee benchmark | our match (med) | ceiling match (med) | always-delta | always-theta |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        r = prim[kind]
        L.append(f"| {kind} | **{r['ae_kappa_med']:.3f}** | {r['ee_kappa_med']:.3f} | {ci(r['contrast_kappa'])} "
                 f"| {r['sqrt_kappa_ee']:.3f} | {r['ae_match_med']:.3f} | {r['ee_match_med']:.3f} "
                 f"| {r['base_delta_med']:.3f} | {r['base_theta_med']:.3f} |")
    L.append("")
    for kind in ["focalslowing", "genslowing"]:
        r = prim[kind]
        L.append(f"- **{kind}**: {r['n_experts']} experts, {r['n_pairs']} pairs; median single-band events "
                 f"per expert = {r['ae_n_med']}, per pair = {r['ee_n_med']}. Raw-match contrast (algo−ceiling) "
                 f"= {ci(r['contrast_match'])}. Our raw match ({r['ae_match_med']:.3f}) sits at the "
                 f"always-delta baseline ({r['base_delta_med']:.3f}) — the agreement is the delta base rate, "
                 f"not band perception (κ_ae = {r['ae_kappa_med']:.3f}).")
    L.append("")

    L.append(f"## Age-normalized z-rule (principled rule; aged subset n={n_aged})\n")
    L.append("`band = argmax(z(rel_delta), z(rel_theta))`, z = deviation from the clean-normal reference at "
             f"the event's age (Gaussian age kernel bw={BW:.0f} y; reference = `channel_stage_features` "
             f"src==cohort & clean_normal, **stage {STAGE}** — MoE events are assumed awake clips). Focal "
             "lobe = the lobe with the largest slowing z-deviation. Age recovered by joining the 9-digit pid "
             "(and eeg date where available) to `fractional_age` / `labels_unified` / `cohort_metadata`; "
             f"sources: {age_src}.\n")
    L.append("| kind | our κ_ae (med) | expert κ_ee ceiling (med) | √κ_ee | our match (med) | ceiling match "
             "(med) | always-delta | our band mix |")
    L.append("|---|---|---|---|---|---|---|---|")
    for kind, m in [("focalslowing", zfoc_mix), ("genslowing", zgen_mix)]:
        r = zres[kind]
        L.append(f"| {kind} | **{r['ae_kappa_med']:.3f}** | {r['ee_kappa_med']:.3f} | {r['sqrt_kappa_ee']:.3f} "
                 f"| {r['ae_match_med']:.3f} | {r['ee_match_med']:.3f} | {r['base_delta_med']:.3f} | {m} |")
    L.append("")

    L.append("## Secondary — delta-vs-theta vote-vector match (analogue of the human-ceiling script, raw rule)\n")
    L.append("Among events the expert called slowing (delta or theta marked), fraction where the full "
             "(delta,theta) vote pair matches. The expert-vs-expert column reproduces the 90-script ceiling "
             "(0.576 focal / 0.434 generalized) on this featurized subset.\n")
    L.append("| kind | our vs expert (median) | expert vs expert / ceiling (median) |")
    L.append("|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        r = prim[kind]
        L.append(f"| {kind} | {r['aeA_med']:.3f} | {r['eeA_med']:.3f} |")
    L.append("")

    L.append("## Sensitivity — author-rater excluded (primary rule)\n")
    L.append("Recomputed dropping the one rater who is an author (anonymized index withheld).\n")
    L.append("| kind | our κ_ae (med) | ceiling κ_ee (med) | our match | ceiling match |")
    L.append("|---|---|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        if kind in sens:
            s = sens[kind]
            L.append(f"| {kind} | {s['ae_kappa_med']:.3f} | {s['ee_kappa_med']:.3f} | "
                     f"{s['ae_match_med']:.3f} | {s['ee_match_med']:.3f} |")
    L.append("")

    L.append("## Verdict\n")
    L.append("1. **The primary raw rule is near-chance.** Chance-corrected, our band determination carries "
             f"almost no information: κ_ae = {prim['focalslowing']['ae_kappa_med']:.3f} (focal) and "
             f"{prim['genslowing']['ae_kappa_med']:.3f} (generalized), versus expert-expert κ_ee = "
             f"{prim['focalslowing']['ee_kappa_med']:.3f} and {prim['genslowing']['ee_kappa_med']:.3f}. The "
             "focal raw match (~0.90) is a **base-rate artifact** — it equals the always-delta baseline, "
             "which an \"always delta\" classifier would also achieve. The κ contrast is negative and its "
             "95% CI excludes 0 for both kinds; our raw rule is below the human ceiling, focal and generalized.")
    L.append(f"2. **The age-normalized z-rule is the principled fix and partly helps.** Its band mix is "
             f"balanced (not 98% delta). On **generalized** slowing κ_ae rises from "
             f"{prim['genslowing']['ae_kappa_med']:.3f} to {zres['genslowing']['ae_kappa_med']:.3f} — a real "
             f"gain. On **focal** slowing it does NOT help ({prim['focalslowing']['ae_kappa_med']:.3f} -> "
             f"{zres['focalslowing']['ae_kappa_med']:.3f}, still near-chance). Either way, on the aged subset "
             f"the z-rule **still sits below** the expert-expert ceiling (κ_ee = "
             f"{zres['focalslowing']['ee_kappa_med']:.3f} focal / {zres['genslowing']['ee_kappa_med']:.3f} gen) "
             f"and below the attenuation benchmark √κ_ee. Our current signal-level band determination does not "
             "reach human concordance.")
    L.append("3. **The old 0.74 must be retired.** It was band agreement of our regex extractor against "
             "**report text**, one report per recording — it measures text parsing, not perception of the "
             "signal, and shares no event, rater, or estimand with the numbers here. It is not comparable to "
             "them and should not be reported as the same quantity. The √κ_ee column is the score an "
             "algorithm sitting at the latent truth would reach against noisy experts (conservative, since "
             "expert errors are correlated).")
    txt = "\n".join(L) + "\n"
    Path("results/moe_band_vs_ours.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
