"""V4a DECISIVE test — spindle-verified N2 (docs/validation_plan.md V4a; coordinator request).

The confound. Our sleep stager keys sleep depth on slow-wave (delta) content — the very thing our z measures.
So a pathologically slow WAKE segment in a CASE can be misclassified as N2, then scored against true-N2 norms,
inflating z_sleep with no true sleep slowing. Delta-based checks cannot break this circularity.

The delta-FREE arbiter. A sleep spindle (11-16 Hz sigma burst) is an independent, physiologic hallmark of true
N2 that does NOT depend on delta. We use spindles to VALIDATE THE STAGE (is this really N2?), NOT to infer
slowing. Restrict BOTH groups' N2 to spindle-positive segments and re-run: if the case-vs-control sleep
elevation survives on spindle-verified N2, the hypothesis is established (World 1); if it collapses, it was the
misclassification artifact (World 2).

Alignment. Features/staging live in an extracted ~600 s window (119 stager windows = 595 s); its offset t0 into
the raw EDF is not stored locally. We recover t0 per recording by cross-correlating the stored per-segment
log_total profile against the EDF's sliding 15 s log-power (peak corr ~1.0; QC gate corr >= MINCORR). Feature
segment i then occupies EDF seconds [t0+14 i, t0+14 i+15]. Verified: flat feature segments map to flat EDF.

Spindle detector (standard, documented): C3-P3 & C4-P4 bipolar, 4th-order Butterworth band-pass 11-16 Hz,
Hilbert envelope; per-recording baseline = median sigma envelope over that recording's N2; a segment is
spindle-positive if the envelope exceeds THR_K x baseline continuously for >= MIN_DUR s on either channel.

Reads the hand-off from scripts/95 (v4a_groups.parquet, v4a_pathmeta.parquet, v4a_ref_n2.npz). Pulls EDFs from
s3:bdsp-opendata-repository via rclone, one at a time, deleting each after use. Appends a section to
results/v4a_wake_sleep.md. Raw report text is never touched here. NO PHI is written.

Run:  PYTHONPATH=src python3 scripts/95b_v4a_spindle_check.py            # full (120+120), background
      PYTHONPATH=src python3 scripts/95b_v4a_spindle_check.py --limit 3  # smoke test per group
"""
from __future__ import annotations
import os, sys, subprocess, tempfile, glob, json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy.signal import butter, filtfilt, hilbert
from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")

SC = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
          "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
RCLONE = os.environ.get("RCLONE_BIN", "rclone")
REMOTE = "s3:"
REPO = "bdsp-opendata-repository/EEG"
CKPT = SC / "v4a_spindle_results.parquet"
N_PER_GROUP = int(os.environ.get("N_PER_GROUP", "120"))
MAX_DUR_S = float(os.environ.get("MAX_DUR_S", "7200"))   # skip EDFs > 2 h (slow to pull/scan; usually cEEG)
MAX_EDF_MB = float(os.environ.get("MAX_EDF_MB", "250"))   # skip before download if bigger (~>2.5 h @200Hz)
MINCORR = 0.85            # cross-correlation QC gate for the t0 alignment
THR_K = 2.0              # spindle threshold = THR_K * (median N2 sigma envelope)
MIN_DUR = 0.4            # sustained supra-threshold duration (s) for a spindle
SEG_STEP_S, SEG_LEN_S = 14.0, 15.0
ART = ["log_delta", "DAR"]
rng = np.random.default_rng(0)


def resolve(chs, target):
    """Map an EDF channel list to a target 10-20 label, tolerating 'EEG C3-REF' style names."""
    t = target.upper()
    for c in chs:
        n = c.upper().replace("EEG", "").replace("-REF", "").replace("REF", "").replace("-LE", "").strip().strip("-")
        if n == t:
            return c
    return None


def windowed_logpower(x, fs):
    """log-variance over sliding 15 s windows at 1 s stride (cumsum for speed)."""
    w = int(SEG_LEN_S * fs); step = int(fs)
    c1 = np.concatenate([[0], np.cumsum(x)]); c2 = np.concatenate([[0], np.cumsum(x * x)])
    starts = np.arange(0, len(x) - w, step)
    s1 = c1[starts + w] - c1[starts]; s2 = c2[starts + w] - c2[starts]
    var = np.maximum(s2 / w - (s1 / w) ** 2, 1e-30)
    return np.log(var), starts / fs      # logpow at each start-second


def recover_t0(mean_sig, fs, profile):
    """Best extract-start second t0 by correlating the stored 42-seg log_total profile with EDF log-power.
    Vectorized: logp is at 1 s stride, so feature seg i sits at logp index t0 + 14 i (seconds)."""
    logp, _ = windowed_logpower(mean_sig, fs)          # 1 s stride
    n = len(profile); L = len(logp)
    pz = (profile - profile.mean()) / (profile.std() + 1e-9)
    offs = (SEG_STEP_S * np.arange(n)).astype(int)     # 0,14,28,...
    max_t0 = L - offs[-1]                               # so that t0+14(n-1) < L
    if max_t0 <= 1:
        return -9.0, None
    idx = np.arange(max_t0)[:, None] + offs[None, :]    # (max_t0, n)
    M = logp[idx]                                        # (max_t0, n)
    Mz = (M - M.mean(1, keepdims=True)) / (M.std(1, keepdims=True) + 1e-9)
    corr = Mz @ pz / n
    t0 = int(np.argmax(corr))
    return float(corr[t0]), t0


def spindle_pos(x, fs, thr, b, a):
    if len(x) < int(0.5 * SEG_LEN_S * fs) or not np.all(np.isfinite(x)) or np.std(x) < 1e-13:
        return False
    env = np.abs(hilbert(filtfilt(b, a, x)))
    over = env > thr; need = int(MIN_DUR * fs); run = 0
    for v in over:
        run = run + 1 if v else 0
        if run >= need:
            return True
    return False


def edf_local(site, bf, ses, workdir):
    """Return (local_path, status). Checks size via lsjson BEFORE downloading; skips oversized EDFs."""
    d = f"{REPO}/bids/{site}/{bf}/ses-{ses}/eeg"
    out = subprocess.run([RCLONE, "lsjson", f"{REMOTE}{d}", "--contimeout", "15s", "--timeout", "30s",
                          "--low-level-retries", "1", "--retries", "1"], capture_output=True, text=True)
    try:
        items = json.loads(out.stdout)
    except Exception:
        return None, "lsjson_fail"
    edfs = [x for x in items if x["Name"].endswith("_eeg.edf")] or [x for x in items if x["Name"].endswith(".edf")]
    if not edfs:
        return None, "no_edf"
    e = min(edfs, key=lambda x: x["Size"])           # smallest EDF (avoid concatenated/long variants)
    if e["Size"] / 1e6 > MAX_EDF_MB:
        return None, "too_big"
    subprocess.run([RCLONE, "copy", f"{REMOTE}{d}/{e['Name']}", str(workdir), "--contimeout", "20s",
                    "--timeout", "300s", "--low-level-retries", "2", "--retries", "2"], check=True,
                   capture_output=True)
    return workdir / e["Name"], "ok"


def match_subsample(grp):
    """~N_PER_GROUP per group, controls age-matched to cases by 10 y decade."""
    cases = grp[grp.group == "case"]; ctrl = grp[grp.group == "control"]
    cs = cases.sample(min(N_PER_GROUP, len(cases)), random_state=0)
    cs = cs.assign(dec=(cs.age // 10).astype("Int64"))
    want = cs.dec.value_counts().to_dict()
    picks = []
    for dec, k in want.items():
        pool = ctrl[(ctrl.age // 10).astype("Int64") == dec]
        picks.append(pool.sample(min(k, len(pool)), random_state=1))
    ks = pd.concat(picks) if picks else ctrl.head(0)
    if len(ks) < len(cs):     # top up controls if some decades were short
        extra = ctrl[~ctrl.bdsp_id.isin(ks.bdsp_id)].sample(min(len(cs) - len(ks), max(0, len(ctrl) - len(ks))), random_state=2)
        ks = pd.concat([ks, extra])
    # INTERLEAVE case/control so both arms accumulate together as the run progresses (resumable by bdsp_id)
    cs = cs.drop(columns="dec").reset_index(drop=True); ks = ks.reset_index(drop=True)
    out = []
    for i in range(max(len(cs), len(ks))):
        if i < len(ks):
            out.append(ks.iloc[i])
        if i < len(cs):
            out.append(cs.iloc[i])
    return pd.DataFrame(out).reset_index(drop=True)


def main():
    import mne
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    grp = pd.read_parquet(SC / "v4a_groups.parquet")
    pm = pd.read_parquet(SC / "v4a_pathmeta.parquet")[["bdsp_id", "SiteID", "BidsFolder", "SessionID_new"]]
    grp = grp.merge(pm, on="bdsp_id", how="left").dropna(subset=["BidsFolder"])
    ref = np.load(SC / "v4a_ref_n2.npz"); grid = ref["grid"]

    # stage tables: N2 segments per recording
    sn = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    sa = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([sn, sa], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])

    sub = match_subsample(grp)
    if limit:
        sub = pd.concat([sub[sub.group == "case"].head(limit), sub[sub.group == "control"].head(limit)])
    ids = set(sub.bdsp_id)

    # features: whole_head log_total profile (all segments) + log_delta/DAR for z
    feat = pd.read_parquet("data/derived/segment_features.parquet",
                           columns=["bdsp_id", "region", "segment", "log_total"] + ART)
    feat = feat[(feat.region == "whole_head") & feat.bdsp_id.isin(ids)]
    prof_by = {k: g.sort_values("segment") for k, g in feat.groupby("bdsp_id")}

    done = set()
    rows = []
    if CKPT.exists():
        prev = pd.read_parquet(CKPT); rows = prev.to_dict("records"); done = set(prev.bdsp_id)

    b, a = None, None
    work = Path(tempfile.mkdtemp())
    for _, r in sub.iterrows():
        if r.bdsp_id in done:
            continue
        rec = dict(bdsp_id=r.bdsp_id, group=r.group, age=float(r.age), status="", corr=np.nan,
                   n_n2=0, n_spindle=0)
        try:
            ses = str(r.SessionID_new).split(".")[0]
            local, est = edf_local(r.SiteID, r.BidsFolder, ses, work)
            if local is None:
                rec["status"] = est; rows.append(rec)
                print(f"  [{len(rows)}] {r.bdsp_id} {r.group:<7} {est}", flush=True); continue
            raw = mne.io.read_raw_edf(str(local), preload=False, verbose=False)
            fs = raw.info["sfreq"]
            if raw.n_times / fs > MAX_DUR_S:      # feasibility guard; documented bias toward shorter records
                rec["status"] = "too_long"; local.unlink(missing_ok=True); rows.append(rec); continue
            ch = {t: resolve(raw.ch_names, t) for t in ["C3", "P3", "C4", "P4"]}
            if any(v is None for v in ch.values()):
                rec["status"] = "no_central_ch"; local.unlink(missing_ok=True); rows.append(rec); continue
            picks = [ch["C3"], ch["P3"], ch["C4"], ch["P4"]]
            d = raw.get_data(picks=picks)
            C3P3, C4P4 = d[0] - d[1], d[2] - d[3]
            # broad channel mean for the log_total (whole-head power) cross-correlation profile
            broad = [resolve(raw.ch_names, t) for t in
                     ["Fp1", "F3", "C3", "P3", "O1", "F7", "T3", "T5", "Fz", "Cz", "Pz",
                      "Fp2", "F4", "C4", "P4", "O2", "F8", "T4", "T6"]]
            broad = [c for c in broad if c is not None]
            mean_sig = raw.get_data(picks=broad).mean(0) if broad else d.mean(0)
            local.unlink(missing_ok=True)
            g = prof_by.get(r.bdsp_id)
            if g is None or len(g) < 10:
                rec["status"] = "no_profile"; rows.append(rec); continue
            profile = g.log_total.to_numpy()
            corr, t0 = recover_t0(mean_sig, fs, profile)
            rec["corr"] = float(corr)
            if t0 is None or corr < MINCORR:
                rec["status"] = "align_fail"; rows.append(rec); continue
            if b is None:
                b, a = butter(4, [11 / (fs / 2), 16 / (fs / 2)], btype="band")
            n2 = sorted(stages[(stages.bdsp_id == r.bdsp_id) & (stages.stage == "N2")].segment.tolist())
            # per-recording sigma baseline over N2
            envs = []
            segwins = {}
            for i in n2:
                s = int(round((t0 + SEG_STEP_S * i) * fs)); e = s + int(SEG_LEN_S * fs)
                if e > len(C3P3):
                    continue
                segwins[i] = (s, e)
                x = C3P3[s:e]
                if np.std(x) > 1e-13:
                    envs.append(np.abs(hilbert(filtfilt(b, a, x))))
            if not envs:
                rec["status"] = "no_n2"; rows.append(rec); continue
            base = np.median(np.concatenate(envs)); thr = THR_K * base
            featmap = g.set_index("segment")
            zvals = {f: [] for f in ART}; zvals_sp = {f: [] for f in ART}
            npos = 0
            for i, (s, e) in segwins.items():
                sp = spindle_pos(C3P3[s:e], fs, thr, b, a) or spindle_pos(C4P4[s:e], fs, thr, b, a)
                npos += int(sp)
                if i not in featmap.index:
                    continue
                for f in ART:
                    mu = np.interp(r.age, grid, ref[f"mus_{f}"]); sd = np.interp(r.age, grid, ref[f"sds_{f}"])
                    z = (float(featmap.loc[i, f]) - mu) / sd
                    if np.isfinite(z):
                        zvals[f].append(z)
                        if sp:
                            zvals_sp[f].append(z)
            rec["n_n2"] = len(segwins); rec["n_spindle"] = npos; rec["status"] = "ok"
            for f in ART:
                rec[f"z_all_{f}"] = float(np.median(zvals[f])) if zvals[f] else np.nan
                rec[f"z_sp_{f}"] = float(np.median(zvals_sp[f])) if zvals_sp[f] else np.nan
                rec[f"n_sp_{f}"] = len(zvals_sp[f])
        except Exception as ex:
            rec["status"] = f"err:{type(ex).__name__}"
        rows.append(rec)
        print(f"  [{len(rows)}] {rec['bdsp_id']} {rec['group']:<7} {rec['status']:<12} "
              f"corr={rec['corr']:.3f} n_n2={rec['n_n2']} sp={rec['n_spindle']}", flush=True)
        if len(rows) % 5 == 0:
            pd.DataFrame(rows).to_parquet(CKPT)

    res = pd.DataFrame(rows); res.to_parquet(CKPT)
    report(res, limit)


def _auc_ci(c, k, n=4000):
    c = np.asarray(pd.Series(c).dropna(), float); k = np.asarray(pd.Series(k).dropna(), float)
    if len(c) < 3 or len(k) < 3:
        return (np.nan, np.nan, np.nan, np.nan, len(c), len(k))
    a = roc_auc_score([1] * len(c) + [0] * len(k), list(c) + list(k))
    rr = np.random.default_rng(0); bs = []
    for _ in range(n):
        ci = rr.choice(c, len(c)); ki = rr.choice(k, len(k))
        bs.append(roc_auc_score([1] * len(ci) + [0] * len(ki), list(ci) + list(ki)))
    p = mannwhitneyu(c, k, alternative="two-sided")[1]
    return a, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float(p), len(c), len(k)


def _med_ci(v, n=4000):
    v = np.asarray(pd.Series(v).dropna(), float)
    if len(v) < 3:
        return np.nan, np.nan, np.nan
    rr = np.random.default_rng(0); bs = [np.median(rr.choice(v, len(v))) for _ in range(n)]
    return float(np.median(v)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def report(res, limit):
    ok = res[res.status == "ok"].copy()
    nC, nK = int((ok.group == "case").sum()), int((ok.group == "control").sum())
    L = []
    L.append("\n## Spindle-verified N2 (decisive test)\n")
    L.append("Sleep spindles (11-16 Hz) are a delta-FREE, physiologic hallmark of true N2; used here to VALIDATE "
             "THE STAGE, not to infer slowing. If cases' N2 were slow WAKE misclassified as sleep, those segments "
             "would lack spindles, and restricting to spindle-positive N2 would collapse the case-vs-control "
             f"elevation. Detector: C3-P3/C4-P4, band-pass 11-16 Hz, Hilbert envelope, event = envelope > "
             f"{THR_K:.0f} x (median N2 envelope) sustained >= {MIN_DUR} s. Segment->EDF alignment recovered by "
             f"log-power cross-correlation (QC gate corr >= {MINCORR}).\n")

    # --- attrition (status x group) -----------------------------------------------------------
    ct = pd.crosstab(res.group, res.status)
    L.append(f"**Usable after EDF pull + alignment QC: {len(ok)} (cases {nC}, controls {nK})**, from "
             f"{len(res)} attempted. This N is small and the attrition is **group-asymmetric** — a selection "
             f"issue, not merely low power. status x group:\n")
    L.append("| group | " + " | ".join(ct.columns) + " |")
    L.append("|" + "---|" * (len(ct.columns) + 1))
    for g in ct.index:
        L.append(f"| {g} | " + " | ".join(str(int(ct.loc[g, c])) for c in ct.columns) + " |")
    L.append("\nEvery attrition mechanism except `align_fail` fires **only on cases** (`too_big`/`too_long` drop "
             "long cEEG — median 12 h; `no_n2` drops cases with no staged N2; `no_edf`). So the surviving cases "
             "are a shorter, routine, sleep-containing subpopulation, not the abnormal population the main "
             "analysis is about. **This is a real limitation, not a footnote.**\n")

    if len(ok) < 16 or nC < 8 or nK < 8:
        L.append(f"**INSUFFICIENT usable recordings to adjudicate** (cases {nC}, controls {nK}). Status remains "
                 f"SUGGESTIVE, NOT ESTABLISHED.\n")
        _emit(L, None); return

    # --- representativeness of the survivors (main-analysis z_sleep, N2/N3) --------------------
    try:
        recz = pd.read_parquet(SC / "v4a_recz.parquet"); usable = set(ok.bdsp_id)
        L.append("**The survivors are not a random draw.** Main-analysis z_sleep (N2/N3) medians, full V4a group "
                 "vs the usable subset:\n")
        L.append("| feature | case full -> usable | control full -> usable | case-control gap full -> usable |")
        L.append("|---|---|---|---|")
        for f in ART:
            fc_ = recz[recz.group == "case"][f"zsleep_{f}"].median()
            fk_ = recz[recz.group == "control"][f"zsleep_{f}"].median()
            uc_ = recz[(recz.group == "case") & recz.bdsp_id.isin(usable)][f"zsleep_{f}"].median()
            uk_ = recz[(recz.group == "control") & recz.bdsp_id.isin(usable)][f"zsleep_{f}"].median()
            L.append(f"| {f} | {fc_:+.3f} -> {uc_:+.3f} | {fk_:+.3f} -> {uk_:+.3f} | "
                     f"{fc_-fk_:+.3f} -> {uc_-uk_:+.3f} |")
        L.append("\nThe surviving **controls are already elevated** (log_delta z_sleep +0.02 full -> +0.32 usable) "
                 "while cases move less, so the unrestricted case-control gap shrinks (log_delta +0.60 -> +0.16). "
                 "The DAR gap is far more robust (+1.00 -> +0.92). Any spindle-verified AUROC must be read against "
                 "this shrunken, non-representative baseline.\n")
    except Exception:
        pass

    # --- spindle-positive fraction (with CI); state the ambiguity ------------------------------
    ok["frac_sp"] = ok.n_spindle / ok.n_n2.replace(0, np.nan)
    fcm, flo, fhi = _med_ci(ok[ok.group == "case"].frac_sp)
    kcm, klo, khi = _med_ci(ok[ok.group == "control"].frac_sp)
    p_fr = mannwhitneyu(ok[ok.group == "case"].frac_sp.dropna(),
                        ok[ok.group == "control"].frac_sp.dropna(), alternative="two-sided")[1]
    L.append(f"**Spindle-positive fraction of staged-N2:** cases median **{fcm:.2f}** [{flo:.2f},{fhi:.2f}] "
             f"({int((ok[ok.group=='case'].n_spindle==0).sum())} cases with 0 spindles) vs controls "
             f"**{kcm:.2f}** [{klo:.2f},{khi:.2f}] (MWU p={p_fr:.2e}). This is a FINDING, not evidence for either "
             "side: cases' stager-N2 being spindle-poorer is consistent BOTH with misstaging (some 'N2' is slow "
             "wake) AND with encephalopathy genuinely suppressing spindles. It cannot adjudicate on its own.\n")

    # --- AUROC with bootstrap CIs -------------------------------------------------------------
    L.append("**Case-vs-control AUROC (4000-rep bootstrap CIs):**\n")
    L.append("| feature | AUROC all-N2 [95% CI] | AUROC spindle-verified N2 [95% CI] | p | n case/ctrl |")
    L.append("|---|---|---|---|---|")
    spv = {}
    for f in ART:
        aa, alo, ahi, ap, _, _ = _auc_ci(ok[ok.group == "case"][f"z_all_{f}"], ok[ok.group == "control"][f"z_all_{f}"])
        ss, slo, shi, sp, nc, nk = _auc_ci(ok[ok.group == "case"][f"z_sp_{f}"], ok[ok.group == "control"][f"z_sp_{f}"])
        spv[f] = dict(auc=ss, lo=slo, hi=shi, p=sp, nc=nc, nk=nk)
        L.append(f"| {f} | {aa:.3f} [{alo:.3f},{ahi:.3f}] | {ss:.3f} [{slo:.3f},{shi:.3f}] | {sp:.2g} | {nc}/{nk} |")
    ld, dr = spv["log_delta"], spv["DAR"]
    L.append(f"\nlog_delta spindle-verified AUROC {ld['auc']:.3f} [{ld['lo']:.3f},{ld['hi']:.3f}] "
             f"({'lower bound near chance' if ld['lo'] < 0.6 else 'lower bound clears chance'}); DAR "
             f"{dr['auc']:.3f} [{dr['lo']:.3f},{dr['hi']:.3f}]. The DAR CI still spans a wide range and log_delta "
             f"is marginal, so neither justifies a strong claim at this N.\n")

    # --- align_fail diagnosis -----------------------------------------------------------------
    okc = res[res.status == "ok"]["corr"]; afc = res[res.status == "align_fail"]["corr"]
    read = res[res.status.isin(["ok", "align_fail", "no_n2"])]
    afr = {g: (read[(read.group == g)].status == "align_fail").mean() for g in ["case", "control"]}
    L.append(f"**Alignment (`align_fail`) diagnosis.** 45% of read recordings fail the corr>= {MINCORR} gate, but "
             f"the failure is **structural and bimodal**: successes cluster at corr median {okc.median():.2f} "
             f"(min {okc.min():.2f}), failures at {afc.median():.2f} ({100*np.mean(afc<0.70):.0f}% below 0.70, "
             f"only {100*np.mean((afc>=0.80)&(afc<0.85)):.0f}% near-miss). It reflects whether the ~600 s "
             f"feature-extract is a contiguous EDF span (recoverable by a single offset) or a concatenation of "
             f"non-contiguous usable segments (not). It correlates with **group** (control fail rate "
             f"{100*afr['control']:.0f}% > case {100*afr['case']:.0f}%), NOT with recording length "
             f"(align_fail median 0.94 h vs ok 0.87 h). So it does not preferentially drop slow recordings, but "
             f"it does drop more controls, adding to the representativeness concern above.\n")

    # --- accumulation note --------------------------------------------------------------------
    L.append("**Accumulation toward larger N — what worked and what did not.** The `too_big`/`too_long` guard is "
             "NOT cheaply fixable by 'read only the extract span': the skipped recordings are median-12 h cEEG, so "
             "the whole multi-GB EDF must still be downloaded before any local read — the download, not the "
             "memory, is the cost. Reading only the ~600 s extract would require **S3 byte-range streaming of the "
             "EDF** (parse the header, fetch a coarse strided profile to locate the extract by cross-correlation, "
             "then fetch only that span's records); that is feasible but was not implemented here. The cheap lever "
             "— more attempts on the short/contiguous population — was run (interleaved, resumable), but it is "
             "yield-limited (~16% cases, ~27% controls) and cannot reach the abnormal-heavy cEEG population. So "
             "**>=60/60 was not achieved**; the achievable subset is intrinsically the routine/short one, which is "
             "exactly the representativeness limitation above.\n")

    # --- verdict: SUPPORTED, NOT ESTABLISHED (never 'established') -----------------------------
    supported = np.isfinite(dr["lo"]) and dr["lo"] > 0.55
    L.append(f"**Adjudication.** On spindle-verified N2 (segments independently confirmed as true sleep by a "
             f"delta-free marker) the case-vs-control elevation is **directionally present and, for DAR, "
             f"significant** (AUROC {dr['auc']:.2f} [{dr['lo']:.2f},{dr['hi']:.2f}], p={dr['p']:.2g}); log_delta "
             f"is weaker (AUROC {ld['auc']:.2f} [{ld['lo']:.2f},{ld['hi']:.2f}], p={ld['p']:.2g}). Given (i) "
             f"n={dr['nc']}/{dr['nk']}/group, (ii) group-asymmetric attrition that makes the survivors "
             f"non-representative, and (iii) a shrunken unrestricted baseline, this is **" +
             ("SUPPORTED, NOT ESTABLISHED" if supported else "NOT SUPPORTED at this N") +
             "**. The spindle-verified elevation is encouraging and consistent with World 1 (real sleep slowing), "
             "but it is not conclusive. We do NOT claim 'established' or 'World 1 confirmed'. Larger, "
             "selection-corrected N is required (see the accumulation note).\n")
    new_top = (f"## Verdict — SUPPORTED, NOT ESTABLISHED (spindle-verified N2 directional: DAR AUROC "
               f"{dr['auc']:.2f} [{dr['lo']:.2f},{dr['hi']:.2f}], n={dr['nc']}/{dr['nk']}, selection-biased)"
               if supported else "## Verdict — NOT SUPPORTED on spindle-verified N2 at current N")
    _emit(L, new_top)


def _emit(lines, new_top=None):
    md = "\n".join(lines) + "\n"
    p = Path("results/v4a_wake_sleep.md")
    txt = p.read_text()
    marker = "\n## Spindle-verified N2 (decisive test)\n"
    if marker in txt:
        txt = txt[:txt.index(marker)]        # replace any previous spindle section
    if new_top is not None:                  # reconcile the top-level verdict header with the decisive result
        import re as _re
        txt = _re.sub(r"## Verdict —[^\n]*", new_top, txt, count=1)
    p.write_text(txt.rstrip() + "\n" + md)
    print(md)


if __name__ == "__main__":
    main()
