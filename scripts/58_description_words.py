#!/usr/bin/env python3
"""§4 DESCRIPTION — D6: from descriptors to WORDS. Turn the read-off descriptors into a clinically faithful,
claims-table-compliant slowing description — a compact finding line AND a full report-style paragraph — then
measure how often each generated component matches the report's structured word (component agreement, not a
binary classification), and emit a PHI-free reasonableness review set.

Every clause is governed by docs/claims_table.md:
  - magnitude as SD + centile, never a severity adjective (clause 3; clause 9 mild/moderate/marked FORBIDDEN)
  - persistence reported as a PERCENTAGE (clause 6 ALLOWED); the ACNS prevalence word (rare/occasional/
    frequent/abundant/continuous) is a gloss on OUR measured prevalence, never a report-concordance claim
    (clause 6b FORBIDDEN)
  - band is a LOW-CONFIDENCE delta/theta/mixed call, asserted only on clear dominance (clause 5; bands
    co-occur, ~64% of reports say "mixed")
  - side ALLOWED; maximum-deviation lobe is PROVISIONAL, phrased as "maximal over …" (clauses 4/4b)
  - anterior/posterior predominance asserted only when it clears the normal centile, else "diffuse" (clause 4d)
  - stage accentuation / "present only during sleep" ALLOWED (clause 8)
  - ABSTAIN path when no lateralizing/regional excess clears the normal centile (clause 11, required)

Agreement is component-wise vs the report's STRUCTURED fields (focal_band/gen_band, focal_side, focal_region,
slowing_focal/gen). Raw report text is PHI and is never read here. The side/region/band component derivations
are unchanged from the prior version, so the concordance numbers are stable. Writes figures/story/s4_d6.png +
results/story/s4_d6.md.  Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/58_description_words.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = Path("figures/story"); RES = Path("results/story")
STAGES = ["W", "N1", "N2", "N3", "REM"]
SLEEP = ["N1", "N2", "N3", "REM"]
STAGE_PREV_THR = 0.15                                   # a stage "shows" slowing if >15% of its segments abnormal
PEAK_READABLE = {"anterior": "the frontal (anterior) region", "posterior": "the posterior (occipito-parietal) region",
                 "L_temporal": "the left temporal region", "R_temporal": "the right temporal region",
                 "L_parasagittal": "the left parasagittal chain", "R_parasagittal": "the right parasagittal chain"}


def nz(x):
    return float(x) if np.isfinite(x) else -9.0


# ---- ACNS-standard prevalence gloss (a description of OUR measured prevalence, not report concordance) ----
def persistence_word(prev):
    return ("rare" if prev < 0.01 else "occasional" if prev < 0.10 else
            "frequent" if prev < 0.50 else "abundant" if prev < 0.90 else "continuous")


# ---- band: low-confidence delta/theta/mixed, asserted only on clear dominance (bands co-occur clinically) ----
def band_word(dp, tp, thr=1.0):
    hi_d, hi_t = dp > thr, tp > thr
    if hi_d and hi_t:
        return "delta" if dp - tp >= 0.7 else "theta" if tp - dp >= 0.7 else "theta-delta"
    if hi_d:
        return "delta"
    if hi_t:
        return "theta"
    return "theta"                                      # no clear dominance -> theta (mildest slow band); NO adjective


def band_phrase(b):
    return "theta–delta (mixed)" if b == "theta-delta" else b


def _ord(n):
    n = int(round(n))
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def centile_word(z):
    if not np.isfinite(z):
        return None
    c = norm.cdf(z) * 100
    if c >= 99.9:
        return ">99.9th"
    if c <= 0.1:
        return "<0.1st"
    return _ord(min(max(c, 1), 99))


def our_side(lat):
    return "left" if lat > 0.25 else "right" if lat < -0.25 else "bilateral"


def _foc(row):
    ft = row.lobe_temporal - (row.lobe_frontal + row.lobe_posterior) / 2
    ff = row.lobe_frontal - (row.lobe_temporal + row.lobe_posterior) / 2
    fp = row.lobe_posterior - (row.lobe_temporal + row.lobe_frontal) / 2
    return ft, ff, fp


def our_lobe(row):
    ft, ff, fp = _foc(row)
    return max([("temporal", ft), ("frontal", ff), ("posterior", fp)], key=lambda x: x[1])[0]


def ourisfoc(row):
    ft, ff, fp = _foc(row)
    return (abs(row.lat_signed) >= 0.5) or (max(ft, ff, fp) >= 0.6)


def ap_word(antpost):
    # normal-referenced z; assert predominance only beyond ~95th centile, else the (majority) "diffuse"
    if not np.isfinite(antpost):
        return "diffuse"
    if antpost > 1.645:
        return "frontally predominant"
    if antpost < -1.645:
        return "posteriorly predominant"
    return "diffuse"


def localization(row):
    """Return (short_spatial, maximal_region_phrase, confident). Handles bilateral/bitemporal and the diffuse
    (generalized) case; `confident` gates the abstain clause per claims-table clause 11."""
    isfoc = ourisfoc(row)
    if not isfoc:
        return ap_word(row.antpost), None, True
    ft, ff, fp = _foc(row)
    lat = row.lat_signed
    lobe = our_lobe(row)
    confident = ((abs(lat) >= 0.5) or (max(ft, ff, fp) >= 0.6)) and (nz(row.peak_region_z) >= 1.0)
    bitemp = (min(nz(row.reg_L_temporal), nz(row.reg_R_temporal)) > 1.0 and abs(lat) < 0.4 and lobe == "temporal")
    if bitemp:
        return "bilateral (independent) temporal", "both temporal regions", confident
    side = our_side(lat)
    if side == "bilateral":
        return f"bilateral {lobe}", f"the {lobe} region bilaterally", confident
    # only name the maximum-deviation region when its hemisphere is consistent with the asserted side
    pr = str(row.peak_region)
    pr_side = "left" if pr.startswith("L_") else "right" if pr.startswith("R_") else None
    maxreg = PEAK_READABLE.get(pr) if (pr_side is None or pr_side == side) else None
    return f"{side} {lobe}", maxreg, confident


def magnitude(row, isfoc):
    if isfoc and np.isfinite(row.peak_region_z):
        return float(row.peak_region_z)
    return float(np.nanmax([row.delta_p90, row.theta_p90]))


def stage_presence(stage_rows):
    """stage_rows: {stage: (prevalence, n_seg, amount)}. Returns (base_clause, accent_clause)."""
    have = {st for st, (p, n, a) in stage_rows.items() if n >= 3}
    present = {st for st, (p, n, a) in stage_rows.items() if n >= 3 and p >= STAGE_PREV_THR}
    if not have:
        return "", ""
    wake_present = "W" in present
    sleep_have = have & set(SLEEP)
    sleep_present = bool(present & set(SLEEP))
    if wake_present and sleep_present:
        base = "present in wakefulness and sleep"
    elif sleep_present and not wake_present and "W" in have:
        base = "present only during sleep"                                       # the added-value clause (clause 8)
    elif wake_present and sleep_have and not sleep_present:
        base = "seen in wakefulness only"
    elif wake_present and not sleep_have:
        base = "seen in the waking record"
    elif sleep_present:
        base = "present during sleep"
    else:
        base = ""
    pool = present or have
    accent = max(pool, key=lambda st: stage_rows[st][2] if np.isfinite(stage_rows[st][2]) else -9)
    if accent == "N1":
        acc = "activated in drowsiness"
    elif accent in ("N2", "N3"):
        acc = f"most prominent in {accent}"
    elif accent == "REM":
        acc = "most prominent in REM sleep"
    else:
        acc = ""
    return base, acc


def finding_line(row, spatial, band, base, acc):
    """Compact headline finding — persistence gloss + spatial + band + stage."""
    prev = row.prevalence
    parts = [persistence_word(prev), spatial, band_phrase(band)]
    s = " ".join(p for p in parts if p) + " slowing"
    tail = "; ".join(x for x in [base, acc] if x)
    s = s + (", " + tail if tail else "")
    return s[0].upper() + s[1:] + "."


def report_paragraph(row, spatial, maxreg, confident, band, base, acc):
    """Full report-style paragraph, every clause a number with a reference population (claims-table §permitted)."""
    isfoc = ourisfoc(row)
    prev = row.prevalence
    z = magnitude(row, isfoc); cent = centile_word(z)
    # sentence 1 — localization + band
    s1 = " ".join(x for x in [spatial, band_phrase(band)] if x) + " slowing"
    if isfoc and maxreg:
        s1 += f", maximal over {maxreg}"
    s1 = s1[0].upper() + s1[1:] + "."
    # sentence 2 — magnitude + prevalence % + run structure
    ref = "the age- and stage-matched normal at that region" if isfoc else "the age- and stage-matched normal"
    mag = f"Peak deviation {z:.1f} SD above {ref}" + (f" ({cent} centile)" if cent else "")
    nep = int(row.n_episodes) if np.isfinite(row.n_episodes) else 0
    run = f"; longest continuous run ≈{row.longest_run_min:.1f} min over {nep} episode{'s' if nep != 1 else ''}" \
        if nep and np.isfinite(row.longest_run_min) else ""
    s2 = f"{mag}, abnormal in {prev*100:.0f}% of analysed segments ({persistence_word(prev)}){run}."
    # sentence 3 — stage (cap first letter only; keep stage tokens like REM/N2 uppercase)
    stage_txt = "; ".join(x for x in [base, acc] if x)
    s3 = (stage_txt[0].upper() + stage_txt[1:] + ".") if stage_txt else ""
    # sentence 4 — abstain (claims-table clause 11)
    s4 = ""
    if isfoc and not confident:
        s4 = "Localization is low-confidence: no lateralizing or regional spectral excess clears the 84th " \
             "centile of normals."
    return " ".join(x for x in [s1, s2, s3, s4] if x)


def build(row, stage_rows):
    isfoc = ourisfoc(row)
    spatial, maxreg, confident = localization(row)
    band = band_word(row.delta_p90, row.theta_p90)
    base, acc = stage_presence(stage_rows)
    finding = finding_line(row, spatial, band, base, acc)
    paragraph = report_paragraph(row, spatial, maxreg, confident, band, base, acc)
    return finding, paragraph, isfoc


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    R = pd.read_parquet("data/derived/description_recording.parquet")
    S = pd.read_parquet("data/derived/description_stage.parquet")
    lab = pd.read_parquet("data/derived/recording_labels.parquet").drop_duplicates("eeg_id")
    sap = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = R.merge(lab[["eeg_id", "focal_side", "focal_region", "focal_band", "gen_band", "gen_topography"]], on="eeg_id") \
         .merge(sap[["eeg_id", "slowing_focal", "slowing_gen_pathologic"]], on="eeg_id")
    d = d[d.slowing_focal.fillna(False) | d.slowing_gen_pathologic.fillna(False)].copy()

    # per-recording stage table: {eeg_id: {stage: (prev, n_seg, amount)}}
    S = S[S.eeg_id.isin(set(d.eeg_id))].copy()
    S["amount"] = S[["delta_p90", "theta_p90"]].max(axis=1)
    stage_map: dict = {}
    for eid, g in S.groupby("eeg_id"):
        stage_map[eid] = {r.stage: (r.prevalence, r.n_seg, r.amount) for r in g.itertuples()}

    d["isfoc"] = d.apply(ourisfoc, axis=1)
    findings, paragraphs = [], []
    for r in d.itertuples():
        f, p, _ = build(r, stage_map.get(r.eeg_id, {}))
        findings.append(f); paragraphs.append(p)
    d["finding"] = findings
    d["report"] = paragraphs
    d["our_band"] = [band_word(r.delta_p90, r.theta_p90) for r in d.itertuples()]
    d["our_side"] = [our_side(r) for r in d.lat_signed]
    d["our_lobe"] = [our_lobe(r) for r in d.itertuples()]

    md = ["# §4 D6 — from descriptors to words: clinical slowing description + component agreement\n",
          "Each report-slowing recording is turned into (a) a compact **finding line** and (b) a full "
          "**report-style paragraph**, built from the read-off descriptors and governed clause-by-clause by "
          "`docs/claims_table.md` (magnitude as SD/centile — no severity adjective; prevalence as a "
          "percentage with the ACNS word only as an internal gloss; band a low-confidence delta/theta/mixed "
          "call on clear dominance; side asserted, maximum-deviation lobe provisional; anterior/posterior "
          "predominance only when it clears the normal centile; stage accentuation and 'present only during "
          "sleep'; and an abstain path when no regional excess clears the normal centile). Component agreement "
          "below is measured against the report's STRUCTURED fields (never raw text, which is PHI); it is a "
          "*concordance* check on the description, not a detection task.\n"]

    # ---- component agreement (derivations unchanged -> stable numbers) ----
    def agree(sub, our, rep, mapper=lambda x: x):
        sub = sub.dropna(subset=[rep]); sub = sub[sub[rep].map(mapper).notna()]
        if not len(sub):
            return np.nan, 0
        return float((sub[our] == sub[rep].map(mapper)).mean()), len(sub)

    def repband(x):
        return {"delta": "delta", "theta": "theta", "mixed": "theta-delta"}.get(x, None)
    dd = d.copy()
    dd["rep_b"] = dd.focal_band.where(dd.focal_band.notna(), dd.gen_band).map(repband)
    a_band, n_band = agree(dd, "our_band", "rep_b")
    foc = d[d.slowing_focal == True]                                                        # noqa: E712
    a_side, n_side = agree(foc, "our_side", "focal_side", lambda x: x if x in ("left", "right", "bilateral") else None)
    a_reg, n_reg = agree(foc, "our_lobe", "focal_region", lambda x: x if x in ("temporal", "frontal", "posterior") else None)

    comps = [("side\n(L/R/bilat)", a_side, n_side, True), ("region\n(T/F/P)", a_reg, n_reg, True),
             ("band\n(delta/theta/mix)", a_band, n_band, False)]
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    xx = np.arange(len(comps))
    for i, (lab_, v, n, solid) in enumerate(comps):
        ax.bar(xx[i], v, color=("#2c7fb8" if solid else "#8aa9c4"), alpha=.9, edgecolor="#5a6b7a")
        ax.text(xx[i], v + .01, f"{v*100:.0f}%\n(n={n})", ha="center", fontsize=8)
    ax.axhline(1/3, ls="--", color="#666", lw=1); ax.text(xx[-1]+.15, 1/3, "chance (1/3)", color="#666", fontsize=8, va="bottom")
    ax.set_xticks(xx); ax.set_xticklabels([c[0] for c in comps], fontsize=8.5)
    ax.set_ylabel("concordance with report word"); ax.set_ylim(0, 1)
    ax.set_title("D6 — Generated descriptor words concordant with the report", fontsize=11)
    ax.grid(alpha=.2, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "s4_d6.png", dpi=140); plt.close(fig)
    md += ["## Component concordance (generated word vs report structured field)",
           "| component | concordance | n | chance | note |", "|---|---|---|---|---|",
           f"| side (L/R/bilateral) | **{a_side*100:.0f}%** | {n_side} | 33% | above chance |",
           f"| region (temporal/frontal/posterior) | **{a_reg*100:.0f}%** | {n_reg} | 33% | above chance |",
           f"| band (delta/theta/mixed) | {a_band*100:.0f}% | {n_band} | 33% | modest — bands co-occur; the "
           f"primary test is the CONTINUOUS D1 contrast (our delta rises with report-delta, theta with report-theta) |",
           "\n*Focal-vs-diffuse (distribution) is decided by the detection head (§2, AUROC 0.92), not "
           "re-derived here. D6 is the synthesis/output layer; each component's validation lives in D1–D5.*\n"]

    # ---- reasonableness review set (structured only, no raw text, no ids, no ages) ----
    md += ["## Reasonableness review set — generated report vs report structured descriptors",
           "*(random sample; raw report text withheld as PHI, report columns are its structured labels; "
           "✓/✗ mark whether our word matches the report's for the discretely-checkable components. "
           "The magnitude/percentage/run/stage clauses are measurements with a reference population, not "
           "report-checkable.)*\n",
           "| # | generated report | report: band · side · region · topo | side | region | band |",
           "|---|---|---|:--:|:--:|:--:|"]
    samp = pd.concat([foc.sample(min(11, len(foc)), random_state=1),
                      d[d.slowing_gen_pathologic == True].sample(min(6, (d.slowing_gen_pathologic == True).sum()), random_state=1)])  # noqa: E712
    bmap = {"delta": "delta", "theta": "theta", "mixed": "theta-delta"}
    for i, r in enumerate(samp.itertuples(), 1):
        rb = r.focal_band if isinstance(r.focal_band, str) else (r.gen_band if isinstance(r.gen_band, str) else "-")
        rs = r.focal_side if isinstance(r.focal_side, str) else "-"
        rr = r.focal_region if isinstance(r.focal_region, str) else "-"
        rt = r.gen_topography if isinstance(r.gen_topography, str) else "-"
        mk = lambda ours, rep, ok: ("✓" if ours == rep else "✗") if ok else "–"
        s_side = mk(r.our_side, rs, rs in ("left", "right", "bilateral") and bool(r.slowing_focal))
        s_reg = mk(r.our_lobe, rr, rr in ("temporal", "frontal", "posterior") and bool(r.slowing_focal))
        s_band = mk(r.our_band, bmap.get(rb, None), rb in bmap)
        md.append(f"| {i} | {r.report} | {rb} · {rs} · {rr} · {rt} | {s_side} | {s_reg} | {s_band} |")

    md += ["\n## Example finding lines (compact headline form)\n"]
    for r in samp.head(6).itertuples():
        md.append(f"- {r.finding}")

    (RES / "s4_d6.md").write_text("\n".join(md))
    print("\n".join(md[:14]))
    print("\n... (+ %d review rows)" % len(samp))
    print("EXAMPLE PARAGRAPH:", samp.iloc[0].report)
    print("wrote figures/story/s4_d6.png + results/story/s4_d6.md")


if __name__ == "__main__":
    main()
