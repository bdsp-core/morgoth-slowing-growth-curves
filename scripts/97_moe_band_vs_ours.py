"""MoE: OUR band-determination agreement vs the expert panel (no report text, no regex extractor).

The paper's "band agreement 0.74" was computed against REPORT TEXT, with our OWN regex extractor,
one report per recording. That number can be dominated by how well we parse the report's band word.
This script recomputes band agreement the honest way:

  * featurize each MoE 15-s event with the PROJECT's OWN pipeline (features.extract + features.recording),
  * make an a-priori band call (delta vs theta) from relative band power,
  * compare it to each of the 18-21 experts' per-band calls on the SAME events,
  * and compute the expert-expert ceiling on the IDENTICAL event subset, so algorithm-vs-expert and
    expert-vs-expert are the same statistic on the same data.

There is no text extractor anywhere in this pipeline.

A-PRIORI band rules (fixed before looking at any agreement number):
  * GENERALIZED band  = argmax(rel_delta, rel_theta) at whole_head. "delta" if rel_delta > rel_theta else "theta".
  * FOCAL band        = same rule, evaluated at the MOST-SLOWED lobar region, defined a priori as the
    region in {L_temporal, R_temporal, L_parasagittal, R_parasagittal} with the largest low-frequency
    relative power low_freq_rel = rel_delta + rel_theta (the max-deviation lobe).
  * ALT (age-matched) = "delta" if rel_delta is more elevated above its age-matched normal median than
    rel_theta is above its own, else "theta"; elevation scaled by (p90-p50) of the normative curve.
    Reported only on the ~1/3 of events for which an age is recoverable.

DATA: MoE per-expert 0/1 band labels (labels/{r1,r2,r3}), pooled over rounds (disjoint events),
BDSP events only (icare_* cardiac-arrest events excluded). Event signals: events_raw/<event>.mat
(MATLAB v7.3 -> h5py). Each .mat is exactly one 3000-sample (15 s @ 200 Hz) referential segment.

PRIVACY: rater columns are real usernames, one of whom (an author of this paper) is anonymized like the
rest to R01..Rnn on load and NEVER written to any file. An "author-rater excluded" sensitivity is
reported without revealing which anonymized index is the author.

Run: PYTHONPATH=src python3 scripts/97_moe_band_vs_ours.py
"""
from __future__ import annotations
import glob, os, re, sys
from pathlib import Path
import numpy as np, pandas as pd
import h5py
from scipy.interpolate import interp1d
from sklearn.metrics import cohen_kappa_score

from morgoth_slowing.features import extract as ex, recording as rec  # project's own pipeline

# ---- paths ---------------------------------------------------------------------------------------
SCRATCH = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
           "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
SC = f"{SCRATCH}/moe/labels"
EVENTS_DIR = f"{SCRATCH}/events_raw"
FEAT_CACHE = f"{SCRATCH}/moe_event_band_feats.parquet"
ROUNDS = ["r1", "r2", "r3"]
AUTHOR = "bwestove"
LOBES = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
MIN_EVENTS = 20            # min single-band slowing events for an expert / pair to enter a distribution
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
    """Featurize every event once, cache to parquet. Columns: rel_delta/rel_theta/low_freq_rel per region."""
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
        for reg in ["whole_head", *LOBES]:
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


# ============================== 2. our a-priori band calls ========================================
def our_band_calls(feat: pd.DataFrame) -> pd.DataFrame:
    out = feat[["event"]].copy()
    # generalized: whole_head
    out["gen_band"] = np.where(feat["whole_head__rel_delta"] > feat["whole_head__rel_theta"], "delta", "theta")
    # focal: most-slowed lobe (max low_freq_rel), then delta-vs-theta there
    lfr = feat[[f"{r}__low_freq_rel" for r in LOBES]].values
    sel = np.array(LOBES)[np.argmax(lfr, axis=1)]
    rd = np.array([feat[f"{r}__rel_delta"].values for r in LOBES]).T
    rt = np.array([feat[f"{r}__rel_theta"].values for r in LOBES]).T
    k = np.argmax(lfr, axis=1)
    focal_rd = rd[np.arange(len(k)), k]
    focal_rt = rt[np.arange(len(k)), k]
    out["focal_region"] = sel
    out["focal_band"] = np.where(focal_rd > focal_rt, "delta", "theta")
    return out


def add_age_alt_bands(calls: pd.DataFrame, feat: pd.DataFrame) -> pd.DataFrame:
    """ALT rule: band = whichever of rel_delta/rel_theta is more elevated above the age-matched normal
    median (elevation scaled by p90-p50 of the sex-pooled normative growth curve). Needs an age."""
    lab = pd.read_parquet("data/derived/labels_unified.parquet")
    lab["pid_str"] = lab["pid"].astype(str)
    age_by_pid = lab.dropna(subset=["age"]).drop_duplicates("pid_str").set_index("pid_str")["age"]
    pid = calls["event"].str.extract(r"^(\d{9})_")[0]
    age = pid.map(age_by_pid).values                                   # NaN where no age
    calls["age"] = age

    gc = pd.read_parquet("data/derived/growth_curves.parquet")
    gcp = gc.groupby(["age", "feature", "region"])[["p50", "p90"]].mean().reset_index()  # pool sex

    def interp(feature, region, col):
        s = gcp[(gcp.feature == feature) & (gcp.region == region)].sort_values("age")
        return interp1d(s.age, s[col], bounds_error=False, fill_value=(s[col].iloc[0], s[col].iloc[-1]))

    def alt_for(region, rd, rt, ages):
        d50, d90 = interp("rel_delta", region, "p50")(ages), interp("rel_delta", region, "p90")(ages)
        t50, t90 = interp("rel_theta", region, "p50")(ages), interp("rel_theta", region, "p90")(ages)
        dev_d = (rd - d50) / np.maximum(d90 - d50, 1e-6)
        dev_t = (rt - t50) / np.maximum(t90 - t50, 1e-6)
        return np.where(dev_d > dev_t, "delta", "theta")

    fe = feat.set_index("event").loc[calls["event"]]
    calls["gen_band_alt"] = alt_for("whole_head", fe["whole_head__rel_delta"].values,
                                    fe["whole_head__rel_theta"].values, age)
    # focal alt uses the same selected lobe as the primary focal call
    fr = calls["focal_region"].values
    rd = np.array([fe[f"{r}__rel_delta"].values for r in LOBES])
    rt = np.array([fe[f"{r}__rel_theta"].values for r in LOBES])
    lidx = {r: i for i, r in enumerate(LOBES)}
    ki = np.array([lidx[r] for r in fr])
    focal_rd = rd[ki, np.arange(len(ki))]
    focal_rt = rt[ki, np.arange(len(ki))]
    # region-specific ref: evaluate per selected region
    band = np.array(["theta"] * len(calls), dtype=object)
    for r in LOBES:
        m = fr == r
        if m.any():
            band[m] = alt_for(r, focal_rd[m], focal_rt[m], age[m])
    calls["focal_band_alt"] = band
    calls.loc[calls["age"].isna(), ["gen_band_alt", "focal_band_alt"]] = np.nan
    return calls


# ============================== 3. expert per-event band matrices ==================================
def load_cat(cat: str) -> pd.DataFrame:
    """Pool a slowing category over rounds, BDSP-only, indexed by event; columns = rater usernames."""
    frames = []
    for r in ROUNDS:
        g = glob.glob(f"{SC}/{r}_csv_labels_20241028/moe_*{cat}.csv")
        if not g:
            continue
        d = pd.read_csv(g[0])
        d = d[d.event.astype(str).str.match(r"^\d{9}_\d{14}$")]         # BDSP events only
        d = d.drop(columns=[c for c in ["eeg"] if c in d]).set_index("event")
        frames.append(d)
    return pd.concat(frames) if frames else None


def aligned_DT(kind, anon, events):
    """Return delta/theta 0/1/NaN matrices (events x anonymized raters) aligned to `events`."""
    D = load_cat(f"{kind}-delta").rename(columns=anon)
    T = load_cat(f"{kind}-theta").rename(columns=anon)
    raters = sorted(set(D.columns) & set(T.columns))
    D = D.reindex(index=events, columns=raters)
    T = T.reindex(index=events, columns=raters)
    return D.values.astype(float), T.values.astype(float), raters


# ============================== 4. agreement statistics ===========================================
def _kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if len(a) < 2 or len(set(a)) < 2 or len(set(b)) < 2:
        return np.nan
    return cohen_kappa_score(a, b)


def compute_kind(kind, our_band, D, T, raters, boot=True):
    """our_band: array (nE,) of 'delta'/'theta' aligned to the D/T rows.
    Returns a dict of point estimates + bootstrap CI on the algorithm-minus-ceiling contrast.
    STAT B (categorical, single-band events): expert band is 'delta' or 'theta' only where the expert
    marked EXACTLY one of the two; algorithm is always one of the two; match + Cohen kappa.
    STAT A (delta-vs-theta vote vector): among events the expert called slowing (delta or theta marked),
    fraction where the full (delta,theta) vote pair matches; mirrors the human-ceiling script's number."""
    ours_delta = (our_band == "delta")
    nE, nR = D.shape
    single_delta = (D == 1) & (T == 0)
    single_theta = (D == 0) & (T == 1)
    single = single_delta | single_theta                  # unambiguous categorical band exists
    exp_delta = single_delta                              # among single, True=delta
    called = ((D == 1) | (T == 1)) & np.isfinite(D) & np.isfinite(T)   # STAT A: any delta/theta slowing

    # ---- STAT B: algorithm vs each expert (categorical) ----
    ae_match, ae_kappa, ae_n = [], [], []
    for r in range(nR):
        m = single[:, r]
        if m.sum() < MIN_EVENTS:
            continue
        ed = exp_delta[m, r]
        od = ours_delta[m]
        ae_match.append(float((ed == od).mean()))
        ae_kappa.append(_kappa(np.where(ed, "delta", "theta"), np.where(od, "delta", "theta")))
        ae_n.append(int(m.sum()))
    # ---- STAT B: expert vs expert (ceiling), same categorical statistic ----
    ee_match, ee_kappa, ee_n = [], [], []
    for i in range(nR):
        for j in range(i + 1, nR):
            m = single[:, i] & single[:, j]
            if m.sum() < MIN_EVENTS:
                continue
            di, dj = exp_delta[m, i], exp_delta[m, j]
            ee_match.append(float((di == dj).mean()))
            ee_kappa.append(_kappa(np.where(di, "delta", "theta"), np.where(dj, "delta", "theta")))
            ee_n.append(int(m.sum()))

    # ---- STAT A: vote-vector match (conditional on expert calling slowing) ----
    aeA, eeA = [], []
    for r in range(nR):
        m = called[:, r]
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
        kind=kind, n_experts=len([1 for r in range(nR) if single[:, r].sum() >= MIN_EVENTS]),
        ae_match_med=np.median(ae_match), ae_match_iqr=(np.percentile(ae_match, 25), np.percentile(ae_match, 75)),
        ee_match_med=np.median(ee_match), ee_match_iqr=(np.percentile(ee_match, 25), np.percentile(ee_match, 75)),
        ae_kappa_med=np.nanmedian(ae_kappa), ee_kappa_med=np.nanmedian(ee_kappa),
        aeA_med=np.median(aeA), eeA_med=np.median(eeA),
        ae_n_med=int(np.median(ae_n)), ee_n_med=int(np.median(ee_n)),
        n_pairs=len(ee_match), sqrt_kappa_ee=float(np.sqrt(max(np.nanmedian(ee_kappa), 0.0))),
    )

    # ---- bootstrap the contrast (resample events) ----
    if boot:
        d_match, d_kappa = [], []
        idx_all = np.arange(nE)
        for _ in range(NBOOT):
            bi = rng.integers(0, nE, nE)
            sD, sT = single_delta[bi], single_theta[bi]
            sS = sD | sT
            sEd = sD
            od = ours_delta[bi]
            am, ak = [], []
            for r in range(nR):
                m = sS[:, r]
                if m.sum() < MIN_EVENTS:
                    continue
                am.append(float((sEd[m, r] == od[m]).mean()))
                ak.append(_kappa(np.where(sEd[m, r], "d", "t"), np.where(od[m], "d", "t")))
            em, ek = [], []
            for i in range(nR):
                for j in range(i + 1, nR):
                    m = sS[:, i] & sS[:, j]
                    if m.sum() < MIN_EVENTS:
                        continue
                    em.append(float((sEd[m, i] == sEd[m, j]).mean()))
                    ek.append(_kappa(np.where(sEd[m, i], "d", "t"), np.where(sEd[m, j], "d", "t")))
            if am and em:
                d_match.append(np.median(am) - np.median(em))
                d_kappa.append(np.nanmedian(ak) - np.nanmedian(ek))
        res["contrast_match"] = (float(np.median(d_match)),
                                 float(np.percentile(d_match, 2.5)), float(np.percentile(d_match, 97.5)))
        res["contrast_kappa"] = (float(np.nanmedian(d_kappa)),
                                 float(np.nanpercentile(d_kappa, 2.5)), float(np.nanpercentile(d_kappa, 97.5)))
    return res


# ============================== 5. driver =========================================================
def fmt_ci(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"


def main():
    # --- canonical anonymization across all categories (identical scheme to script 90) ---
    allcols = set()
    for kind in ["focalslowing", "genslowing"]:
        for b in ["delta", "theta"]:
            d = load_cat(f"{kind}-{b}")
            if d is not None:
                allcols |= set(d.columns)
    names = sorted(allcols)
    anon = {n: f"R{i+1:02d}" for i, n in enumerate(names)}
    author_anon = anon.get(AUTHOR)                                     # kept in-memory only

    # --- the pooled BDSP event universe (from focal delta, which covers every event) ---
    events_all = list(load_cat("focalslowing-delta").index)
    feat = build_feature_table(events_all)
    calls = our_band_calls(feat)
    calls = add_age_alt_bands(calls, feat)
    events = list(calls["event"])                                     # featurized events only
    n_feat, n_total = len(events), len(set(events_all))
    n_aged = int(calls["age"].notna().sum())

    print(f"{len(names)} raters -> R01..R{len(names):02d}; "
          f"{n_feat}/{n_total} BDSP events featurized with the project pipeline; "
          f"{n_aged} have a recoverable age.", file=sys.stderr)

    rows = {}
    for kind, band_col in [("focalslowing", "focal_band"), ("genslowing", "gen_band")]:
        D, T, raters = aligned_DT(kind, anon, events)
        rows[kind] = compute_kind(kind, calls[band_col].values, D, T, raters)

    # author-rater-excluded sensitivity (drop that anonymized column; never name it)
    sens = {}
    for kind, band_col in [("focalslowing", "focal_band"), ("genslowing", "gen_band")]:
        D, T, raters = aligned_DT(kind, anon, events)
        if author_anon in raters:
            k = raters.index(author_anon)
            keep = [c for c in range(len(raters)) if c != k]
            sens[kind] = compute_kind(kind, calls[band_col].values, D[:, keep], T[:, keep],
                                      [raters[c] for c in keep], boot=False)

    # age-matched ALT rule, on the aged subset only
    aged_mask = calls["age"].notna().values
    ev_aged = list(np.array(events)[aged_mask])
    alt = {}
    for kind, band_col in [("focalslowing", "focal_band_alt"), ("genslowing", "gen_band_alt")]:
        D, T, raters = aligned_DT(kind, anon, ev_aged)
        alt[kind] = compute_kind(kind, calls.loc[aged_mask, band_col].values, D, T, raters, boot=False)

    # --- distribution of our own band calls (sanity: are we degenerate?) ---
    gen_mix = calls["gen_band"].value_counts(normalize=True).to_dict()
    foc_mix = calls["focal_band"].value_counts(normalize=True).to_dict()

    # ============================== write report ==============================
    L = []
    L.append("# MoE — our band determination vs the expert panel (no report text)\n")
    L.append(f"Featurized **{n_feat}/{n_total}** pooled BDSP MoE events with the project's own pipeline "
             f"(`features.extract` -> `features.recording`); each event is one 15-s, 3000-sample, 200 Hz "
             f"referential segment. `icare_*` cardiac-arrest events excluded. {len(names)} raters, "
             f"anonymized R01..R{len(names):02d} (one is an author of this paper).\n")
    L.append("**A-priori band rules.** Generalized: `delta` if whole-head rel_delta > rel_theta else `theta`. "
             "Focal: the same rule at the most-slowed lobe (max rel_delta+rel_theta over "
             "L/R temporal, L/R parasagittal). No report text and no text extractor enter this pipeline.\n")
    L.append(f"Our own band-call mix — generalized: {gen_mix}; focal: {foc_mix}.\n")

    L.append("## Primary: categorical delta-vs-theta band, on single-band slowing events\n")
    L.append("For each expert, restrict to events that expert scored as slowing in **exactly one** of "
             "delta/theta (band unambiguous); compare to our band call. The **ceiling** is the identical "
             "statistic between experts on the identical event universe. Distribution is over "
             f"experts (algorithm) / expert pairs (ceiling); experts/pairs need ≥{MIN_EVENTS} such events.\n")
    L.append("| kind | our vs expert: match median [IQR] | expert vs expert (ceiling): match median [IQR] | "
             "contrast (algo−ceiling), boot 95% CI | our κ (med) | expert κ (med) | √κ_ee benchmark |")
    L.append("|---|---|---|---|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        r = rows[kind]
        L.append(f"| {kind} | **{r['ae_match_med']:.3f}** [{r['ae_match_iqr'][0]:.3f}, {r['ae_match_iqr'][1]:.3f}] "
                 f"| {r['ee_match_med']:.3f} [{r['ee_match_iqr'][0]:.3f}, {r['ee_match_iqr'][1]:.3f}] "
                 f"| {fmt_ci(r['contrast_match'])} | {r['ae_kappa_med']:.3f} | {r['ee_kappa_med']:.3f} "
                 f"| {r['sqrt_kappa_ee']:.3f} |")
    L.append("")
    for kind in ["focalslowing", "genslowing"]:
        r = rows[kind]
        L.append(f"- **{kind}**: {r['n_experts']} experts, {r['n_pairs']} expert pairs; "
                 f"median single-band events per expert = {r['ae_n_med']}, per pair = {r['ee_n_med']}. "
                 f"Cohen-κ contrast (algo−ceiling): {fmt_ci(r['contrast_kappa'])}.")
    L.append("")

    L.append("## Secondary: delta-vs-theta vote-vector match (analogue of the human-ceiling script)\n")
    L.append("Among events the expert called slowing (delta or theta marked), fraction where the full "
             "(delta,theta) vote pair matches. The expert-vs-expert column reproduces the 90-script "
             "ceiling (0.576 focal / 0.434 generalized) on this featurized subset.\n")
    L.append("| kind | our vs expert (median) | expert vs expert / ceiling (median) |")
    L.append("|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        r = rows[kind]
        L.append(f"| {kind} | {r['aeA_med']:.3f} | {r['eeA_med']:.3f} |")
    L.append("")

    L.append("## Sensitivity: author-rater excluded\n")
    L.append("Recomputed dropping the one rater who is an author (index withheld). Primary categorical match:\n")
    L.append("| kind | our vs expert (match med) | ceiling (match med) |")
    L.append("|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        if kind in sens:
            s = sens[kind]
            L.append(f"| {kind} | {s['ae_match_med']:.3f} | {s['ee_match_med']:.3f} |")
    L.append("")

    L.append(f"## Age-matched ALT rule (aged subset, n={n_aged} events with a recoverable age)\n")
    L.append("Band = whichever of rel_delta/rel_theta is more elevated above its age-matched normal median "
             "(growth-curve p50, sex pooled; elevation scaled by p90−p50). Same categorical match statistic.\n")
    L.append("| kind | ALT our vs expert (match med) | ceiling on aged subset (match med) |")
    L.append("|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        a = alt[kind]
        L.append(f"| {kind} | {a['ae_match_med']:.3f} | {a['ee_match_med']:.3f} |")
    L.append("")

    L.append("## Interpretation\n")
    for kind in ["focalslowing", "genslowing"]:
        r = rows[kind]
        c = r["contrast_match"]
        verdict = ("EXCEEDS" if c[1] > 0 else "FALLS BELOW" if c[2] < 0 else "MATCHES")
        L.append(f"- **{kind}**: our band call {verdict} the expert-expert ceiling on band determination "
                 f"(match {r['ae_match_med']:.3f} vs ceiling {r['ee_match_med']:.3f}; "
                 f"contrast {fmt_ci(c)}). The attenuation benchmark √κ_ee = {r['sqrt_kappa_ee']:.3f} is the "
                 f"score an algorithm sitting at the latent truth would reach against noisy experts "
                 f"(conservative, since expert errors are correlated).")
    L.append("")
    L.append("**On the old 0.74.** That number was band agreement of our regex extractor against **report "
             "text**, one report per recording — it measures text parsing, not perception of the signal, and "
             "shares no event, rater, or estimand with the numbers above. It is not comparable to them and "
             "should not be reported as if it were the same quantity. The numbers here are the honest "
             "signal-level band agreement, benchmarked against the expert-expert ceiling on the same events.")

    txt = "\n".join(L) + "\n"
    Path("results/moe_band_vs_ours.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
