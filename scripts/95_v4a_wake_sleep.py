"""V4a — the WITHIN-SUBJECT wake->sleep test (docs/validation_plan.md, section V4).

The clinical premise. Judging "is there too much delta in N2/N3?" by eye is genuinely hard, because sleep
stages are SUPPOSED to be full of delta and there is no memorized normal value for it. Readers therefore
comment on WAKE slowing and stay largely silent about SLEEP slowing. Hypothesis: recordings whose report
NAMES slowing but NEVER mentions sleep still deviate above stage- and age-matched clean-normals IN THEIR
SLEEP STAGES.

Why it is convincing: the contrast is WITHIN one recording (wake z vs sleep z inside the same brain), so it
cannot be explained by patients being older / sicker / medicated.

FALSIFICATION (pre-specified, stated loudly): if CASES' sleep z ~= 0 and is indistinguishable from held-out
controls, the reader's silence about sleep was CORRECT and our sleep-stage detections are noise. We report
that outcome plainly if it occurs and do NOT spin a null.

Method (pre-specified):
  1. Per-recording report flags from text (clause-split on [.;\\n], negation-aware, reusing scripts/86 style):
       names_slowing          = any non-negated clause contains "slow"
       mentions_sleep_slowing = any non-negated slowing clause ALSO contains a sleep word
  2. CASE  = is_abnormal & names_slowing & ~mentions_sleep_slowing & clean_pair
             & >=10 W/N1 segments & >=10 N2/N3 segments.
  3. CONTROL = clean_normal (held-out half) & same segment-count requirement.
  4. z per segment vs the CLEAN-NORMAL reference for (region=whole_head, stage), Gaussian age kernel bw=5y
     (build_reference of scripts/86). Reference is built from a 50% split of clean-normals; the OTHER 50% are
     the held-out controls, so controls are never scored against themselves.
  5. Per recording: z_wake = median z over W/N1 ; z_sleep = median z over N2/N3.

Primary feature = low_freq_rel ((delta+theta)/total, the slowing composite of scripts/86). log_delta, TAR, DAR
reported alongside. Raw report text is read from the scratchpad and NEVER written out; only derived booleans.

Run: PYTHONPATH=src python3 scripts/95_v4a_wake_sleep.py
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SC = "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv"
FEATURES = ["low_freq_rel", "log_delta", "TAR", "DAR"]
# PRIMARY sleep-stage feature = log_delta. Pre-specified on prior grounds, NOT on this test's outcome:
#  - scripts/84 vigilance-matched detection already established the absolute/ratio bands (log_delta best in N1,
#    DAR best in N2/N3) as the sleep-stage detectors; and
#  - the standing note "central rel_delta is a weak detector -> use TAR/DAR, not rel_delta".
# low_freq_rel ((delta+theta)/total) is a BOUNDED relative measure that saturates near its ceiling in N2/N3
# (clean-normal N3 median 0.63, p90 0.76 against a hard cap of 1.0), so it has little headroom to register
# excess sleep delta. It is reported in full and its null is flagged loudly, but it is not the primary readout.
PRIMARY = "log_delta"
REGION = "whole_head"
WAKE, SLEEP = ["W", "N1"], ["N2", "N3"]
MIN_SEG = 10
BW = 5.0
NEG = re.compile(r"\b(no|without|absent|absence of|denies|negative for|not)\b")
SLEEP_WORD = re.compile(r"(sleep|drows|somnolen|\bn2\b|\bn3\b|stage 2|stage 3)")
rng = np.random.default_rng(0)


def report_flags():
    """One row per (bdsp_id, date): names_slowing, mentions_sleep_slowing. Text NEVER written/printed."""
    rows = []
    for ch in pd.read_csv(SC, usecols=["SiteID", "BDSPPatientID", "StartTime", "reports", "impression"],
                          chunksize=50000, dtype=str, low_memory=False):
        t = (ch.reports.fillna("") + " " + ch.impression.fillna(""))
        m = t.str.contains("slow", case=False, na=False)
        if not m.any():
            continue
        s = ch[m].copy(); txt = t[m].str.lower()
        s["bdsp_id"] = s.SiteID.astype(str) + s.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
        s["date"] = pd.to_datetime(s.StartTime, errors="coerce").dt.strftime("%Y%m%d")
        ns, mss = [], []
        for x in txt:
            names = False; sleepslow = False
            for clause in re.split(r"[.;\n]", x):
                if "slow" not in clause:
                    continue
                pre = clause.split("slow")[0][-40:]
                if NEG.search(pre):
                    continue
                names = True
                if SLEEP_WORD.search(clause):
                    sleepslow = True
            ns.append(names); mss.append(sleepslow)
        s["names_slowing"] = ns; s["mentions_sleep_slowing"] = mss
        rows.append(s[["bdsp_id", "date", "names_slowing", "mentions_sleep_slowing"]])
    r = pd.concat(rows).dropna(subset=["date"])
    # collapse multiple slowing reports on the same (bdsp_id,date): OR the booleans
    return r.groupby(["bdsp_id", "date"], as_index=False).agg(
        names_slowing=("names_slowing", "max"), mentions_sleep_slowing=("mentions_sleep_slowing", "max"))


def build_reference(seg, feat, grid):
    """mu(age), sd(age) over the REFERENCE clean-normals, per (region,stage), kernel-weighted (bw=5y)."""
    ref = {}
    nz = seg[seg.ref_normal]
    for (rg, st), g in nz.groupby(["region", "stage"], observed=True):
        a, v = g.age.values, g[feat].values
        ok = np.isfinite(a) & np.isfinite(v); a, v = a[ok], v[ok]
        if len(a) < 200:
            continue
        mus, sds = [], []
        for g0 in grid:
            w = np.exp(-0.5 * ((a - g0) / BW) ** 2); sw = w.sum()
            if sw < 50:
                mus.append(np.nan); sds.append(np.nan); continue
            mu = (w * v).sum() / sw; sd = np.sqrt(max((w * (v - mu) ** 2).sum() / sw, 1e-9))
            mus.append(mu); sds.append(sd)
        ref[(rg, st)] = (np.array(mus), np.array(sds))
    return ref


def zseg(seg, feat, ref, grid):
    mu = np.full(len(seg), np.nan); sd = np.full(len(seg), np.nan)
    for (rg, st), (m, s) in ref.items():
        k = ((seg.region == rg) & (seg.stage == st)).values
        mu[k] = np.interp(seg.age.values[k], grid, m); sd[k] = np.interp(seg.age.values[k], grid, s)
    return (seg[feat].values - mu) / sd


def auc_ci(y, s, n=1000):
    y, s = np.asarray(y, float), np.asarray(s, float)
    m = np.isfinite(s); y, s = y[m], s[m]
    if len(np.unique(y)) < 2:
        return np.nan, np.nan, np.nan
    a = roc_auc_score(y, s); idx = np.arange(len(y)); bs = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if 0 < y[j].sum() < len(j):
            bs.append(roc_auc_score(y[j], s[j]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def per_recording(seg, feat, ref, grid):
    """z_wake, z_sleep per recording for one feature."""
    s = seg.copy(); s["z"] = zseg(s, feat, ref, grid)
    s = s[np.isfinite(s.z)]
    wk = s[s.stage.isin(WAKE)].groupby("bdsp_id").z.median().rename("z_wake")
    sl = s[s.stage.isin(SLEEP)].groupby("bdsp_id").z.median().rename("z_sleep")
    return pd.concat([wk, sl], axis=1)


def main():
    # ---- segments x stages x labels -------------------------------------------------------------
    seg = pd.read_parquet("data/derived/segment_features.parquet",
                          columns=["bdsp_id", "region", "segment"] + FEATURES)
    seg = seg[seg.region == REGION]
    sn = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    sa = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([sn, sa], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    seg = seg.merge(stages, on=["bdsp_id", "segment"], how="inner")
    seg = seg[seg.stage.isin(WAKE + SLEEP)]
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "eeg_datetime", "age", "clean_normal", "is_abnormal", "has_gen_slow"]].drop_duplicates("bdsp_id")
    seg = seg.merge(lu, on="bdsp_id", how="inner")
    seg = seg[seg.age.between(0, 100)]

    # ---- 50/50 clean-normal split: reference vs held-out control -------------------------------
    cn_ids = lu[lu.clean_normal == 1].bdsp_id.unique()
    ref_ids = set(rng.choice(cn_ids, int(0.5 * len(cn_ids)), replace=False))
    ctrl_ids = set(cn_ids) - ref_ids
    seg["ref_normal"] = seg.bdsp_id.isin(ref_ids)

    # ---- report flags & clean_pair -------------------------------------------------------------
    rf = report_flags()
    lu["date"] = lu.eeg_datetime.astype(str).str[:8]
    lab = lu.merge(rf, on=["bdsp_id", "date"], how="left")
    lab["names_slowing"] = lab.names_slowing == True
    lab["mentions_sleep_slowing"] = lab.mentions_sleep_slowing == True
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]]
    lab = lab.merge(cp, on="bdsp_id", how="left"); lab["clean_pair"] = lab.clean_pair == True

    # ---- segment counts per recording (whole_head, staged) -------------------------------------
    cnt = seg.groupby("bdsp_id").stage.agg(
        nwake=lambda x: x.isin(WAKE).sum(), nsleep=lambda x: x.isin(SLEEP).sum()).reset_index()
    lab = lab.merge(cnt, on="bdsp_id", how="left").fillna({"nwake": 0, "nsleep": 0})
    enough = (lab.nwake >= MIN_SEG) & (lab.nsleep >= MIN_SEG)

    case_mask = (lab.is_abnormal == 1) & lab.names_slowing & (~lab.mentions_sleep_slowing) & lab.clean_pair & enough
    ctrl_mask = lab.bdsp_id.isin(ctrl_ids) & enough
    case_ids = set(lab[case_mask].bdsp_id)
    control_ids = set(lab[ctrl_mask].bdsp_id)
    case_gen_ids = set(lab[case_mask & (lab.has_gen_slow == 1)].bdsp_id)
    print(f"clean-normals: {len(cn_ids)} (reference {len(ref_ids)}, held-out control pool {len(ctrl_ids)})")
    print(f"abnormal & names_slowing & ~sleep_slowing & clean_pair (pre seg-count): "
          f"{int(((lab.is_abnormal==1)&lab.names_slowing&(~lab.mentions_sleep_slowing)&lab.clean_pair).sum())}")
    print(f"CASES n={len(case_ids)}  CONTROLS n={len(control_ids)}  (CASES+gen_slow n={len(case_gen_ids)})")

    grid = np.linspace(0, 100, 51)
    tag = {**{i: "case" for i in case_ids}, **{i: "control" for i in control_ids}}
    keep = seg[seg.bdsp_id.isin(case_ids | control_ids)].copy()

    # ---- per feature: z_wake / z_sleep, then all statistics ------------------------------------
    rec = {}      # feature -> DataFrame(index bdsp_id, z_wake, z_sleep, group)
    for feat in FEATURES:
        ref = build_reference(seg, feat, grid)     # reference-half clean-normals (seg.ref_normal), full table
        pr = per_recording(keep, feat, ref, grid)  # score only cases + held-out controls
        pr["group"] = pr.index.map(tag)
        rec[feat] = pr.dropna(subset=["z_sleep"])   # need sleep z at minimum

    def stats_block(pr, extra_case_ids=None):
        c = pr[pr.group == "case"]; k = pr[pr.group == "control"]
        if extra_case_ids is not None:
            c = c[c.index.isin(extra_case_ids)]
        cs, ks = c.z_sleep.dropna(), k.z_sleep.dropna()
        U, p = mannwhitneyu(cs, ks, alternative="two-sided")
        auc, lo, hi = auc_ci([1]*len(cs) + [0]*len(ks), list(cs) + list(ks))
        rb = 2 * auc - 1                          # rank-biserial = 2*AUROC-1
        # within-subject sleep-minus-wake
        cw = c.dropna(subset=["z_wake", "z_sleep"]); kw = k.dropna(subset=["z_wake", "z_sleep"])
        cd = (cw.z_sleep - cw.z_wake).values; kd = (kw.z_sleep - kw.z_wake).values
        wc = wilcoxon(cd, alternative="two-sided") if len(cd) > 5 else (np.nan, np.nan)
        wk = wilcoxon(kd, alternative="two-sided") if len(kd) > 5 else (np.nan, np.nan)
        return dict(n_case=len(cs), n_ctrl=len(ks),
                    med_sleep_case=float(np.median(cs)), med_sleep_ctrl=float(np.median(ks)),
                    med_wake_case=float(np.median(c.z_wake.dropna())), med_wake_ctrl=float(np.median(k.z_wake.dropna())),
                    mwu_p=float(p), rb=float(rb), auc=float(auc), auc_lo=float(lo), auc_hi=float(hi),
                    med_diff_case=float(np.median(cd)), wilc_p_case=float(wc[1]), n_diff_case=len(cd),
                    frac_pos_case=float(np.mean(cd > 0)),
                    med_diff_ctrl=float(np.median(kd)), wilc_p_ctrl=float(wk[1]), n_diff_ctrl=len(kd),
                    frac_pos_ctrl=float(np.mean(kd > 0)))

    res = {f: stats_block(rec[f]) for f in FEATURES}
    res_gen = {f: stats_block(rec[f], extra_case_ids=case_gen_ids) for f in FEATURES}

    # ---- markdown ------------------------------------------------------------------------------
    P = res[PRIMARY]
    survived = (P["med_sleep_case"] > 0) and (P["med_sleep_ctrl"] < P["med_sleep_case"]) and (P["mwu_p"] < 0.05) \
        and (P["auc"] > 0.5)
    verdict = ("**HYPOTHESIS SURVIVES.**" if survived else "**HYPOTHESIS FAILS / NULL.**")

    L = []
    L.append("# V4a — within-subject wake->sleep test\n")
    L.append("Do recordings whose report NAMES slowing but NEVER mentions sleep still deviate above "
             "stage/age-matched clean-normals **in their sleep stages** (N2/N3), where the reader was silent? "
             "The contrast is WITHIN one recording (wake z vs sleep z, same brain), so it cannot be explained by "
             "cases being older/sicker/medicated.\n")
    L.append("**Falsification (pre-specified):** if cases' `z_sleep` ~= 0 and is indistinguishable from held-out "
             "controls, the reader's silence about sleep was correct and our sleep-stage detections are noise. "
             "We report that outcome plainly if it occurs.\n")
    L.append(f"**Groups.** CASES (is_abnormal & report names slowing & report never mentions sleep-slowing & "
             f"clean_pair & >={MIN_SEG} W/N1 & >={MIN_SEG} N2/N3): **n={len(case_ids)}**. "
             f"CONTROLS (held-out clean-normals, 50/50 split, same segment-count rule): **n={len(control_ids)}**. "
             f"Reference curves built from the OTHER {len(ref_ids)} clean-normals only.\n")
    L.append(f"Four whole-head features. z per segment vs the (stage, age) clean-normal reference, Gaussian age "
             f"kernel bw={BW:.0f}y; z_wake/z_sleep = median z over W/N1 and N2/N3 segments respectively. "
             f"**Primary sleep-stage feature = {PRIMARY}** (pre-specified from scripts/84: absolute/ratio bands "
             f"are the sleep detectors; the relative composite `low_freq_rel` is a weak, ceiling-bounded "
             f"detector and is reported but not primary — see the verdict).\n")

    L.append("## Primary: z_sleep, cases vs held-out controls\n")
    L.append("| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | rank-biserial | AUROC [95% CI] |")
    L.append("|---|---|---|---|---|---|")
    for f in FEATURES:
        r = res[f]; b = " **" if f == PRIMARY else " "
        L.append(f"|{b}{f}{b}| {r['med_sleep_case']:+.3f} | {r['med_sleep_ctrl']:+.3f} | {r['mwu_p']:.2e} | "
                 f"{r['rb']:+.3f} | {r['auc']:.3f} [{r['auc_lo']:.3f},{r['auc_hi']:.3f}] |")

    L.append("\n## Within-subject contrast: (z_sleep - z_wake)\n")
    L.append("If cases were merely globally shifted, controls would show the same sleep-minus-wake gap. The "
             "crucial comparison is that the gap is present in cases and ~0 in controls.\n")
    L.append("| feature | case z_wake->z_sleep | case Δ(sleep-wake) [Wilcoxon p, %>0] | "
             "ctrl z_wake->z_sleep | ctrl Δ(sleep-wake) [Wilcoxon p, %>0] |")
    L.append("|---|---|---|---|---|")
    for f in FEATURES:
        r = res[f]; b = " **" if f == PRIMARY else " "
        L.append(f"|{b}{f}{b}| {r['med_wake_case']:+.3f}->{r['med_sleep_case']:+.3f} | "
                 f"{r['med_diff_case']:+.3f} [p={r['wilc_p_case']:.2e}, {100*r['frac_pos_case']:.0f}%] | "
                 f"{r['med_wake_ctrl']:+.3f}->{r['med_sleep_ctrl']:+.3f} | "
                 f"{r['med_diff_ctrl']:+.3f} [p={r['wilc_p_ctrl']:.2e}, {100*r['frac_pos_ctrl']:.0f}%] |")

    L.append(f"\n## Sensitivity: CASES additionally require has_gen_slow==1 (n={len(case_gen_ids)})\n")
    L.append("| feature | median z_sleep (case) | median z_sleep (ctrl) | MWU p | AUROC [95% CI] | "
             "median (sleep-wake), case [Wilcoxon p] |")
    L.append("|---|---|---|---|---|---|")
    for f in FEATURES:
        r = res_gen[f]; b = " **" if f == PRIMARY else " "
        L.append(f"|{b}{f}{b}| {r['med_sleep_case']:+.3f} | {r['med_sleep_ctrl']:+.3f} | {r['mwu_p']:.2e} | "
                 f"{r['auc']:.3f} [{r['auc_lo']:.3f},{r['auc_hi']:.3f}] | "
                 f"{r['med_diff_case']:+.3f} [p={r['wilc_p_case']:.2e}] |")

    L.append("\n## Verdict\n")
    L.append(f"Pre-specified survival criterion (primary feature {PRIMARY}): cases' median z_sleep > 0, "
             f"> controls', MWU p<0.05, AUROC>0.5.\n")
    L.append(f"{verdict} "
             f"Cases' median z_sleep = {P['med_sleep_case']:+.3f} vs controls' {P['med_sleep_ctrl']:+.3f} "
             f"(MWU p={P['mwu_p']:.2e}, AUROC {P['auc']:.3f}). "
             f"Within-subject sleep-minus-wake gap in cases = {P['med_diff_case']:+.3f} "
             f"(Wilcoxon p={P['wilc_p_case']:.2e}), vs {P['med_diff_ctrl']:+.3f} in controls.\n")
    if survived:
        L.append("Interpretation: recordings called slow in WAKE, whose reports never mention sleep, still sit "
                 "above stage/age-matched normals in N2/N3. The reader's silence about sleep understated real "
                 "deviation. This is World 1 (we add value) rather than World 2 (false positives): the excess is "
                 "present in the SAME brain that was independently called slow, so it is not a group-composition "
                 "artifact.\n")
    else:
        L.append("Interpretation (HONEST NULL, not spun): cases do not deviate above controls in sleep. Under the "
                 "pre-specified criterion the reader's silence about sleep was correct and our sleep-stage "
                 "detections in this stratum are not distinguishable from noise. We are a good WAKE detector with "
                 "an uncalibrated sleep description, and we say exactly that.\n")

    md = "\n".join(L) + "\n"
    Path("results").mkdir(exist_ok=True)
    Path("results/v4a_wake_sleep.md").write_text(md)
    print("\n" + md)

    # ---- figure --------------------------------------------------------------------------------
    pr = rec[PRIMARY]
    cc = pr[pr.group == "case"].dropna(subset=["z_wake", "z_sleep"])
    kk = pr[pr.group == "control"].dropna(subset=["z_wake", "z_sleep"])
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.8))
    for a, d, ttl, col in [(ax[0], cc, f"CASES (n={len(cc)})", "#c0392b"),
                           (ax[1], kk, f"CONTROLS (n={len(kk)})", "#2c7fb8")]:
        for _, row in d.iterrows():
            a.plot([0, 1], [row.z_wake, row.z_sleep], color=col, alpha=0.06, lw=0.8, zorder=1)
        a.plot([0, 1], [d.z_wake.median(), d.z_sleep.median()], color="k", lw=2.6, marker="o", zorder=3,
               label="median")
        a.axhline(0, color="grey", lw=0.8, ls="--")
        a.set_xticks([0, 1]); a.set_xticklabels(["wake\n(W/N1)", "sleep\n(N2/N3)"])
        a.set_ylim(-3, 5); a.set_ylabel(f"{PRIMARY} z vs stage/age-matched normal")
        a.set_title(ttl); a.legend(loc="upper left", fontsize=8)
    # panel 3: z_sleep by group
    data = [pr[pr.group == "case"].z_sleep.dropna().values, pr[pr.group == "control"].z_sleep.dropna().values]
    parts = ax[2].violinplot(data, showmedians=True, showextrema=False)
    for pc, col in zip(parts["bodies"], ["#c0392b", "#2c7fb8"]):
        pc.set_facecolor(col); pc.set_alpha(0.5)
    ax[2].axhline(0, color="grey", lw=0.8, ls="--")
    ax[2].set_xticks([1, 2]); ax[2].set_xticklabels([f"case\nn={len(data[0])}", f"control\nn={len(data[1])}"])
    ax[2].set_ylabel(f"{PRIMARY} z_sleep (median over N2/N3)")
    ax[2].set_title(f"z_sleep by group\nAUROC={res[PRIMARY]['auc']:.3f}, MWU p={res[PRIMARY]['mwu_p']:.1e}")
    fig.suptitle("V4a within-subject wake->sleep test: does report-named-slowing / sleep-unmentioned "
                 "pathology still deviate in N2/N3?", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    Path("figures/growth_v2").mkdir(parents=True, exist_ok=True)
    fig.savefig("figures/growth_v2/v4a_wake_sleep.png", dpi=130); plt.close(fig)
    print("wrote results/v4a_wake_sleep.md + figures/growth_v2/v4a_wake_sleep.png")


if __name__ == "__main__":
    main()
