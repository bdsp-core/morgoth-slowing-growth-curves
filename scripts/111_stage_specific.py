"""111 — per-stage present/absent slowing call, and its report-state validation (docs/description_architecture.md §1c).

Morgoth gates at the recording level and is not stage-specific; the deviation field IS. `S` is normed per stage
(scripts/107), so we can emit, for each recording and each stage, a present/absent slowing call:

    slowing present in stage X  <=>  prevalence_X > 0.10       (double the 5% normal rate; the field's
                                                                prevalence is the fraction of that stage's
                                                                segments above the normal 95th centile)

The committed plan (§1c) is to VALIDATE that per-stage call against the state a report localises slowing to.
Readers comment on WAKE slowing and stay largely silent about SLEEP slowing, so the report-text scan is the
denominator that decides how strong a state-specific test is even possible.

PART A  per-stage present rate by group (clean_normal / focal / generalized), from the descriptor table.
PART B  report-text state scan (THE VALIDATION DENOMINATOR): clause-scoped, negation-aware, reusing scripts/95
        machinery. For each report: wake_slow (a non-negated slowing clause naming a WAKE word) and sleep_slow
        (a non-negated slowing clause naming a SLEEP word). Raw text is read from the scratchpad in chunks and
        NEVER written or printed; only the two derived booleans reach disk.
PART C  directional validation: among recordings whose report localises slowing to WAKE, is our W-stage
        prevalence elevated vs recordings without? Among those localising to SLEEP, is our N2/N3 prevalence
        elevated? AUROC each. The spindle-verified V4a anchor (wake-reported slowing -> genuine N2 excess,
        AUROC 0.85; results/v4a_wake_sleep.md) is CITED, not recomputed.

Writes data/derived/report_state_labels.parquet (bdsp_id, date, wake_slow, sleep_slow — booleans only) and
results/stage_specific.md. Prints the markdown to stdout.

Run: KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python3 scripts/111_stage_specific.py
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_auc_score

SC = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
      "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/reports/EEGs_And_Reports.csv")
STATE_LABELS = Path("data/derived/report_state_labels.parquet")
PREV_CALL = 0.10                         # "slowing present in stage X" iff prevalence_X > 0.10 (2x the 5% norm)
STAGES = ["W", "N1", "N2", "N3", "REM"]
GROUPS = ["clean-normal", "focal", "generalized"]

# --- clause scan machinery, reused verbatim from scripts/95 ------------------------------------------
NEG = re.compile(r"\b(no|without|absent|absence of|denies|negative for|not)\b")
WAKE_WORD = re.compile(r"(awake|wakefulness|alert)")
SLEEP_WORD = re.compile(r"(sleep|drows|somnolen|\bn2\b|\bn3\b|stage 2|stage 3)")
rng = np.random.default_rng(0)


# ====================================================================================================
# PART B — report-text state scan (booleans only ever written / printed)
# ====================================================================================================
def scan_report_states():
    """One row per (bdsp_id, date): wake_slow, sleep_slow. Raw text NEVER written or printed.

    Cached to data/derived/report_state_labels.parquet so reruns skip the 1.1 GB scan."""
    if STATE_LABELS.exists():
        print(f"[PART B] loading cached {STATE_LABELS}", flush=True)
        return pd.read_parquet(STATE_LABELS)
    print(f"[PART B] scanning report text in chunks (booleans only leave the loop) ...", flush=True)
    rows = []
    n_chunks = 0
    for ch in pd.read_csv(SC, usecols=["SiteID", "BDSPPatientID", "StartTime", "reports", "impression"],
                          chunksize=50000, dtype=str, low_memory=False):
        n_chunks += 1
        t = ch.reports.fillna("") + " " + ch.impression.fillna("")
        m = t.str.contains("slow", case=False, na=False)
        if not m.any():
            continue
        s = ch[m].copy(); txt = t[m].str.lower()
        s["bdsp_id"] = s.SiteID.astype(str) + s.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
        s["date"] = pd.to_datetime(s.StartTime, errors="coerce").dt.strftime("%Y%m%d")
        wk, sl = [], []
        for x in txt:
            w = False; z = False
            for clause in re.split(r"[.;\n]", x):
                if "slow" not in clause:
                    continue
                pre = clause.split("slow")[0][-40:]      # 40-char window before "slow", as in scripts/95
                if NEG.search(pre):
                    continue                              # negated slowing clause -> ignore
                if WAKE_WORD.search(clause):
                    w = True
                if SLEEP_WORD.search(clause):
                    z = True
            wk.append(w); sl.append(z)
        s["wake_slow"] = wk; s["sleep_slow"] = sl
        rows.append(s[["bdsp_id", "date", "wake_slow", "sleep_slow"]])
    print(f"[PART B] processed {n_chunks} chunks", flush=True)
    r = pd.concat(rows).dropna(subset=["date"])
    # collapse multiple slowing reports sharing one (bdsp_id, date): OR the booleans
    out = r.groupby(["bdsp_id", "date"], as_index=False).agg(
        wake_slow=("wake_slow", "max"), sleep_slow=("sleep_slow", "max"))
    out["wake_slow"] = out.wake_slow.astype(bool); out["sleep_slow"] = out.sleep_slow.astype(bool)
    STATE_LABELS.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(STATE_LABELS)                          # bdsp_id, date, wake_slow, sleep_slow ONLY
    print(f"[PART B] wrote {STATE_LABELS} ({len(out):,} slowing reports, booleans only)", flush=True)
    return out


# --- stats helper -----------------------------------------------------------------------------------
def auc_ci(y, s, n=2000):
    y = np.asarray(y, float); s = np.asarray(s, float)
    m = np.isfinite(s) & np.isfinite(y); y, s = y[m], s[m]
    if len(np.unique(y)) < 2:
        return np.nan, np.nan, np.nan, len(y)
    a = roc_auc_score(y, s); idx = np.arange(len(y)); bs = []
    for _ in range(n):
        j = rng.choice(idx, len(idx), replace=True)
        if 0 < y[j].sum() < len(j):
            bs.append(roc_auc_score(y[j], s[j]))
    return a, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(len(y))


def directional(score, label):
    """AUROC + effect of `score` discriminating boolean `label`; medians and MWU p."""
    d = pd.DataFrame({"score": score, "label": label.astype(bool)}).dropna(subset=["score"])
    pos = d[d.label].score; neg = d[~d.label].score
    if len(pos) < 5 or len(neg) < 5:
        return dict(auc=np.nan, lo=np.nan, hi=np.nan, n_pos=len(pos), n_neg=len(neg),
                    med_pos=float(pos.median()) if len(pos) else np.nan,
                    med_neg=float(neg.median()) if len(neg) else np.nan, p=np.nan)
    a, lo, hi, _ = auc_ci(d.label.values, d.score.values)
    _, p = mannwhitneyu(pos, neg, alternative="two-sided")
    return dict(auc=a, lo=lo, hi=hi, n_pos=int(len(pos)), n_neg=int(len(neg)),
                med_pos=float(pos.median()), med_neg=float(neg.median()), p=float(p))


def main():
    # ---- descriptor table: per-(recording, stage) prevalence -----------------------------------
    D = pd.read_parquet("data/derived/description_descriptors.parquet")[["bdsp_id", "stage", "prevalence", "n_seg"]]
    D["present"] = D.prevalence > PREV_CALL

    # ---- labels & groups (same convention as scripts/107) --------------------------------------
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "eeg_datetime", "clean_normal", "is_abnormal", "has_report",
         "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    lu["group"] = np.where(lu.clean_normal == True, "clean-normal",
                    np.where(lu.has_focal_slow == 1, "focal",
                      np.where(lu.gen_class == "pathologic", "generalized", "other")))

    # ================================================================================================
    # PART A — per-stage present rate, by group
    # ================================================================================================
    da = D.merge(lu[["bdsp_id", "group"]], on="bdsp_id", how="inner")
    A = {}
    for st in STAGES:
        g = da[da.stage == st]
        A[st] = {grp: dict(n=int((g.group == grp).sum()),
                           present=float(g.loc[g.group == grp, "present"].mean()) if (g.group == grp).any() else np.nan)
                 for grp in GROUPS}

    # ================================================================================================
    # PART B — report state labels
    # ================================================================================================
    rs = scan_report_states()
    n_slow_reports = len(rs)
    wake_only = int((rs.wake_slow & ~rs.sleep_slow).sum())
    sleep_only = int((~rs.wake_slow & rs.sleep_slow).sum())
    both = int((rs.wake_slow & rs.sleep_slow).sum())
    unspec = int((~rs.wake_slow & ~rs.sleep_slow).sum())
    n_any_wake = int(rs.wake_slow.sum())
    n_any_sleep = int(rs.sleep_slow.sum())

    # ================================================================================================
    # PART C — directional validation (clean_pair only; date from cohort_metadata)
    # ================================================================================================
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"bdsp_id": str, "eeg_datetime": str})
    meta["date"] = meta.eeg_datetime.str[:8]
    meta = meta[["bdsp_id", "date"]].drop_duplicates("bdsp_id")
    cp = pd.read_parquet("data/derived/report_pairing.parquet")[["bdsp_id", "clean_pair"]].drop_duplicates("bdsp_id")

    # per-recording stage prevalences (wide)
    piv = D.pivot_table(index="bdsp_id", columns="stage", values="prevalence")
    piv = piv.rename(columns={s: f"prev_{s}" for s in piv.columns})
    piv["prev_sleep"] = piv[["prev_N2", "prev_N3"]].max(axis=1)     # N2/N3 sleep-slowing score
    piv["prev_any"] = piv[[f"prev_{s}" for s in STAGES]].max(axis=1)  # best stage (field detects slowing at all)

    rec = lu[["bdsp_id", "group", "clean_normal", "is_abnormal", "has_report"]].copy()
    rec = rec.merge(meta, on="bdsp_id", how="left")                 # date from cohort_metadata
    rec = rec.merge(cp, on="bdsp_id", how="left")
    rec["clean_pair"] = rec.clean_pair == True
    rec = rec.merge(piv.reset_index(), on="bdsp_id", how="left")
    # attach report state labels on bdsp_id + date; recordings with no slowing report -> False/False
    rec = rec.merge(rs, on=["bdsp_id", "date"], how="left")
    rec["wake_slow"] = rec.wake_slow == True
    rec["sleep_slow"] = rec.sleep_slow == True

    # analysis population: clean_pair recordings that carry a report (so "without" is well defined)
    pop = rec[rec.clean_pair & (rec.has_report == 1)].copy()
    n_pop = len(pop)
    n_pop_wake = int(pop.wake_slow.sum()); n_pop_sleep = int(pop.sleep_slow.sum())

    # LABEL QUALITY: is each report-state label a pathology marker at all? (abnormal enrichment)
    abn_rate_wake_T = float(pop.loc[pop.wake_slow, "is_abnormal"].mean())
    abn_rate_wake_F = float(pop.loc[~pop.wake_slow, "is_abnormal"].mean())
    abn_rate_sleep_T = float(pop.loc[pop.sleep_slow, "is_abnormal"].mean())
    abn_rate_sleep_F = float(pop.loc[~pop.sleep_slow, "is_abnormal"].mean())
    n_cn_sleep = int(((pop.group == "clean-normal") & pop.sleep_slow).sum())
    n_cn_nosleep = int(((pop.group == "clean-normal") & ~pop.sleep_slow).sum())
    n_cn_wake = int(((pop.group == "clean-normal") & pop.wake_slow).sum())

    # directional tests, FULL population (report state vs field per-stage prevalence)
    wake_on_W = directional(pop.prev_W, pop.wake_slow)
    wake_on_N1 = directional(pop.prev_N1, pop.wake_slow)
    wake_on_any = directional(pop.prev_any, pop.wake_slow)
    sleep_on_sleep = directional(pop.prev_sleep, pop.sleep_slow)
    sleep_on_N2 = directional(pop.prev_N2, pop.sleep_slow)
    sleep_on_any = directional(pop.prev_any, pop.sleep_slow)
    # cross terms for the 2x2 specificity table
    wake_on_sleep = directional(pop.prev_sleep, pop.wake_slow)
    sleep_on_W = directional(pop.prev_W, pop.sleep_slow)

    # CONFOUND-FREE concordance: within ABNORMAL recordings only, does report state-localization match the
    # field's per-stage localization? (removes the abnormal-vs-normal leakage that inflates the full-pop numbers)
    abn = pop[pop.is_abnormal == 1]
    wake_on_W_abn = directional(abn.prev_W, abn.wake_slow)
    wake_on_N1_abn = directional(abn.prev_N1, abn.wake_slow)
    sleep_on_sleep_abn = directional(abn.prev_sleep, abn.sleep_slow)
    sleep_on_N2_abn = directional(abn.prev_N2, abn.sleep_slow)
    n_abn = len(abn)

    # ================================================================================================
    # markdown
    # ================================================================================================
    L = []
    L.append("# Stage-specific slowing: per-stage present/absent call and its report-state validation\n")
    L.append("The deviation field norms `S` per stage (scripts/107), so we can emit a per-stage present/absent "
             f"slowing call: **slowing present in stage X iff prevalence_X > {PREV_CALL:.2f}** (double the 5% "
             "false-positive rate baked into the normal 95th-centile threshold). Morgoth gates the recording; "
             "this is the piece Morgoth cannot do (docs/description_architecture.md §1c).\n")

    L.append("## Part A — per-stage present rate, by group\n")
    L.append("Fraction of recordings called slowing-present in each stage (denominator = recordings staged in "
             "that stage). Groups per scripts/107 (`clean_normal` / `has_focal_slow` / `gen_class==pathologic`).\n")
    L.append("| stage | clean-normal | focal | generalized |")
    L.append("|---|---|---|---|")
    for st in STAGES:
        cells = []
        for grp in GROUPS:
            a = A[st][grp]
            cells.append(f"{a['present']:.3f} (n={a['n']})" if np.isfinite(a["present"]) else "— (n=0)")
        L.append(f"| {st} | " + " | ".join(cells) + " |")
    cn_w = A["W"]["clean-normal"]
    L.append(f"\n**Calibration.** With the threshold at the normal 95th centile, a clean-normal recording is "
             f"called present iff >10% of its segments in that stage exceed it — well above the 5% expected by "
             f"chance — so clean-normals sit low by construction (W present rate {cn_w['present']:.3f}). Focal and "
             f"generalized rise above them in every stage, and the call fires in **sleep as well as wake** — the "
             f"stage-specific capability the architecture asked for.\n")

    L.append("## Part B — report-state scan: the validation denominator\n")
    L.append("Clause-scoped, negation-aware scan of the raw report text (reusing scripts/95: split on `[.;\\n]`, "
             "40-char pre-`slow` negation window). `wake_slow` = a non-negated slowing clause names a wake word "
             "(awake/wakefulness/alert); `sleep_slow` = names a sleep word (sleep/drows*/somnolen*/N2/N3/stage 2/"
             "stage 3). Only the two booleans are written (`data/derived/report_state_labels.parquet`); raw text "
             "never leaves the scan.\n")
    L.append(f"**{n_slow_reports:,} reports** contain a non-negated slowing clause. Of those, the state the "
             "report localises slowing to:\n")
    L.append("| localization | reports | share of slowing reports |")
    L.append("|---|---|---|")
    L.append(f"| wake only | {wake_only:,} | {wake_only/n_slow_reports:.1%} |")
    L.append(f"| sleep only | {sleep_only:,} | {sleep_only/n_slow_reports:.1%} |")
    L.append(f"| both wake and sleep | {both:,} | {both/n_slow_reports:.1%} |")
    L.append(f"| unspecified (slowing named, no state word) | {unspec:,} | {unspec/n_slow_reports:.1%} |")
    L.append(f"\nAny wake mention: **{n_any_wake:,}**; any sleep mention: **{n_any_sleep:,}**. "
             f"A sleep word co-occurs with slowing in **{n_any_sleep/n_slow_reports:.0%}** of slowing reports — so "
             f"'sleep-localized slowing' looks *common*, not rare. **That count is misleading, and Part C shows "
             f"why:** physiological drowsiness and sleep ARE slow, and reports routinely say so ('slowing with "
             f"drowsiness/sleep' is a normal finding). The raw sleep-word co-occurrence therefore does NOT isolate "
             f"pathological sleep slowing. The wake mention is the rarer but cleaner signal.\n")

    L.append("## Part C — directional validation (clean_pair, reports only)\n")
    L.append(f"Join per-stage calls to report-state labels on `bdsp_id`+`date` (date = cohort_metadata "
             f"`eeg_datetime[:8]`), restrict to `clean_pair` recordings carrying a report: **n={n_pop:,}** "
             f"(report localises wake slowing: {n_pop_wake:,}; sleep slowing: {n_pop_sleep:,}).\n")

    L.append("### C0 — first, is each report-state label a pathology marker at all?\n")
    L.append("Abnormal rate (`is_abnormal`) among recordings the report does / doesn't localize slowing to a "
             "state — a prerequisite for using the label as ground truth:\n")
    L.append("| report label | abnormal rate if TRUE | abnormal rate if FALSE | clean-normals flagged |")
    L.append("|---|---|---|---|")
    L.append(f"| wake_slow | **{abn_rate_wake_T:.2f}** | {abn_rate_wake_F:.2f} | {n_cn_wake:,} |")
    L.append(f"| sleep_slow | {abn_rate_sleep_T:.2f} | {abn_rate_sleep_F:.2f} | {n_cn_sleep:,} of "
             f"{n_cn_sleep+n_cn_nosleep:,} clean-normals |")
    L.append(f"\n**`wake_slow` is a clean pathology marker** ({abn_rate_wake_T:.0%} abnormal vs "
             f"{abn_rate_wake_F:.0%}; only {n_cn_wake} clean-normals flagged). **`sleep_slow` is not** — its "
             f"abnormal rate ({abn_rate_sleep_T:.2f}) is no higher than its complement ({abn_rate_sleep_F:.2f}), "
             f"and it flags MORE clean-normals ({n_cn_sleep:,}) than it leaves unflagged ({n_cn_nosleep:,}). "
             f"Report 'sleep slowing' is dominated by *normal physiological* sleep slowing, so it cannot serve as "
             f"a pathological-sleep-slowing denominator.\n")

    L.append("### C1 — directional tests (full population)\n")
    L.append("Score = the field's stage prevalence; label = the report's state localization. 'Without' = every "
             "other reported clean_pair recording (includes normals), so a positive AUROC here blends "
             "state-concordance with generic abnormal-vs-normal separation.\n")
    L.append("| report localizes | field score | AUROC [95% CI] | median present vs absent | MWU p | n pos/neg |")
    L.append("|---|---|---|---|---|---|")
    for name, r, sc in [("WAKE slowing", wake_on_W, "W prevalence (the plan's test)"),
                        ("WAKE slowing", wake_on_N1, "N1 prevalence"),
                        ("WAKE slowing", wake_on_any, "best-stage prevalence"),
                        ("SLEEP slowing", sleep_on_sleep, "N2/N3 prevalence (the plan's test)"),
                        ("SLEEP slowing", sleep_on_N2, "N2 prevalence"),
                        ("SLEEP slowing", sleep_on_any, "best-stage prevalence")]:
        L.append(f"| {name} | {sc} | {r['auc']:.3f} [{r['lo']:.3f},{r['hi']:.3f}] | "
                 f"{r['med_pos']:.3f} vs {r['med_neg']:.3f} | {r['p']:.2e} | {r['n_pos']}/{r['n_neg']} |")
    L.append("\nThe field's per-stage prevalence is heavily zero-inflated (median 0 in every stage), so read the "
             "AUROCs, not the medians. **The plan's wake->W test is at chance** "
             f"(AUROC {wake_on_W['auc']:.3f}): report wake-slowing does not track the field's *W-specific* call, "
             f"because the field puts most detected slowing in N1/N2 (Part A: focal N1 present rate "
             f"{A['N1']['focal']['present']:.2f} vs W {A['W']['focal']['present']:.2f}). It shows a modest signal "
             f"against N1 / best-stage ({wake_on_N1['auc']:.3f} / {wake_on_any['auc']:.3f}) — but that is mostly "
             f"the abnormal-vs-normal leakage (wake_slow is {abn_rate_wake_T:.0%} abnormal). **The plan's "
             f"sleep->N2/N3 test runs BELOW chance** ({sleep_on_sleep['auc']:.3f}) — the direct consequence of C0: "
             f"reports that name sleep slowing are enriched for *normals*, which have low pathological N2/N3 "
             f"prevalence.\n")

    L.append("### C2 — confound-free concordance (within abnormal recordings only)\n")
    L.append(f"Restricting to abnormal recordings (**n={n_abn:,}**) removes the abnormal-vs-normal leakage and "
             "asks the pure question: *given the recording is abnormal, does the report's state localization "
             "agree with the field's per-stage localization?*\n")
    L.append("| report localizes | field score | AUROC [95% CI] | n pos/neg |")
    L.append("|---|---|---|---|")
    for name, r, sc in [("WAKE slowing", wake_on_W_abn, "W prevalence"),
                        ("WAKE slowing", wake_on_N1_abn, "N1 prevalence"),
                        ("SLEEP slowing", sleep_on_sleep_abn, "N2/N3 prevalence"),
                        ("SLEEP slowing", sleep_on_N2_abn, "N2 prevalence")]:
        L.append(f"| {name} | {sc} | {r['auc']:.3f} [{r['lo']:.3f},{r['hi']:.3f}] | {r['n_pos']}/{r['n_neg']} |")
    L.append("\n**Every within-abnormal concordance sits at or below 0.5.** The report's state-localization and "
             "the field's per-stage prevalence do not agree at the recording level once abnormal-vs-normal is "
             "removed. This is the reader-reliability limit V4a is built around: readers localize slowing to a "
             "*state* coarsely and inconsistently (sleep especially), so report text is not a usable criterion "
             "for a *stage-specific* call.\n")

    L.append("## What is and isn't possible\n")
    L.append(f"- **The per-stage present/absent call itself (Part A) is sound** — calibrated to the normal 95th "
             f"centile and dose-responsive across groups in every stage, including sleep (focal/gen N2 present "
             f"rate {A['N2']['focal']['present']:.2f}/{A['N2']['generalized']['present']:.2f} vs clean-normal "
             f"{A['N2']['clean-normal']['present']:.2f}). Its validity rests on construct validity, not on report "
             f"text.\n")
    L.append(f"- **Report WAKE-slowing validates abnormal-vs-normal, not stage.** `wake_slow` is a clean "
             f"pathology flag ({abn_rate_wake_T:.0%} abnormal) but at chance against the field's W-specific call "
             f"(AUROC {wake_on_W['auc']:.3f}; {wake_on_W_abn['auc']:.3f} within abnormals) — it says the recording "
             f"is slow, not that the slowing lives in wake.\n")
    L.append(f"- **A report-text SLEEP-specific test is not achievable, and not merely underpowered.** "
             f"{n_pop_sleep:,} reports localize slowing to sleep (a large denominator), but the label is "
             f"*contaminated*: normal physiological sleep is slow and reports say so, so `sleep_slow` flags "
             f"normals as much as abnormals and runs below chance against pathological N2/N3 prevalence "
             f"({sleep_on_sleep['auc']:.3f}). No clause-scoping fixes this — the words for physiological and "
             f"pathological sleep slowing are the same.\n")
    L.append("- **The decisive sleep anchor is therefore not report text but the spindle-verified V4a result** "
             "(results/v4a_wake_sleep.md), cited not recomputed: recordings whose report names slowing in WAKE "
             "and never mentions sleep still carry genuine N2 excess on spindle-verified true-N2 segments "
             "(**AUROC 0.85**, an independent delta-free marker that the stage is truly N2). That within-subject, "
             "spindle-gated design — precisely because it does NOT rely on the reader localizing sleep slowing — "
             "is what establishes that stage-specific sleep slowing is real where the reader was silent.\n")

    md = "\n".join(L) + "\n"
    Path("results").mkdir(exist_ok=True)
    Path("results/stage_specific.md").write_text(md)
    print("\n" + md)


if __name__ == "__main__":
    main()
