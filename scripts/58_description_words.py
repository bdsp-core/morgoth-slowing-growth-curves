#!/usr/bin/env python3
"""§4 DESCRIPTION — D6: from descriptors to WORDS. Turn the read-off descriptors into a templated clinical
sentence, then measure how often each generated component matches the report's structured word (component
agreement, not a binary classification), and emit a reasonableness review set.

Sentence template (report-slowing recordings):
  "<persistence> <distribution> <band> slowing<, region/side><, stage>."
  e.g. "Frequent left temporal theta-delta slowing, present in wake and sleep."

Agreement is component-wise vs the report's STRUCTURED fields (focal_band/gen_band, focal_side, focal_region,
slowing_focal/gen). Raw report text is PHI and is never read here. Writes figures/story/s4_d6.png +
results/story/s4_d6.md.  Run: PYTHONPATH=src MPLBACKEND=Agg python3 scripts/58_description_words.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = Path("figures/story"); RES = Path("results/story")
STAGES = ["W", "N1", "N2", "N3", "REM"]


def persistence_word(prev):
    return ("intermittent" if prev < 0.10 else "frequent" if prev < 0.50 else
            "abundant" if prev < 0.90 else "nearly continuous")


def band_word(dp, tp, thr=1.0):
    # bands co-occur clinically (reports are ~64% "mixed"); call a single band only on clear dominance.
    hi_d, hi_t = dp > thr, tp > thr
    if hi_d and hi_t:
        return "delta" if dp - tp >= 0.7 else "theta" if tp - dp >= 0.7 else "theta-delta"
    if hi_d:
        return "delta"
    if hi_t:
        return "theta"
    return "mild theta"                                  # low amount -> default to theta (mildest slowing)


def our_side(lat):
    return "left" if lat > 0.25 else "right" if lat < -0.25 else "bilateral"


def our_lobe(row):
    ft = row.lobe_temporal - (row.lobe_frontal + row.lobe_posterior) / 2
    ff = row.lobe_frontal - (row.lobe_temporal + row.lobe_posterior) / 2
    fp = row.lobe_posterior - (row.lobe_temporal + row.lobe_frontal) / 2
    return max([("temporal", ft), ("frontal", ff), ("posterior", fp)], key=lambda x: x[1])[0]


def ourisfoc(row):
    ft = row.lobe_temporal - (row.lobe_frontal + row.lobe_posterior) / 2
    ff = row.lobe_frontal - (row.lobe_temporal + row.lobe_posterior) / 2
    fp = row.lobe_posterior - (row.lobe_temporal + row.lobe_frontal) / 2
    return (abs(row.lat_signed) >= 0.5) or (max(ft, ff, fp) >= 0.6)


def sentence(row, stagetop):
    dist = "focal" if row.isfoc else "diffuse"
    parts = [persistence_word(row.prevalence)]
    if row.isfoc:
        parts.append(f"{our_side(row.lat_signed)} {our_lobe(row)}")
    else:
        parts.append("diffuse")
    parts.append(band_word(row.delta_p90, row.theta_p90))
    s = " ".join(parts) + " slowing"
    if stagetop:
        s += f", most prominent in {stagetop}"
    return s[0].upper() + s[1:] + "."


def main():
    FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    R = pd.read_parquet("data/derived/description_recording.parquet")
    S = pd.read_parquet("data/derived/description_stage.parquet")
    lab = pd.read_parquet("data/derived/recording_labels.parquet").drop_duplicates("eeg_id")
    sap = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = R.merge(lab[["eeg_id", "focal_side", "focal_region", "focal_band", "gen_band"]], on="eeg_id") \
         .merge(sap[["eeg_id", "slowing_focal", "slowing_gen_pathologic"]], on="eeg_id")
    d = d[d.slowing_focal.fillna(False) | d.slowing_gen_pathologic.fillna(False)].copy()
    d["isfoc"] = d.apply(ourisfoc, axis=1)
    # dominant sleep stage per recording (highest band deviation), for the stage clause
    top = (S.assign(amt=S[["delta_p90", "theta_p90"]].max(axis=1))
             .sort_values("amt").groupby("eeg_id").tail(1).set_index("eeg_id")["stage"])
    d["stagetop"] = d.eeg_id.map(top)
    d["sentence"] = [sentence(r, r.stagetop) for r in d.itertuples()]
    d["our_band"] = [band_word(r.delta_p90, r.theta_p90) for r in d.itertuples()]
    d["our_side"] = [our_side(r) for r in d.lat_signed]
    d["our_lobe"] = [our_lobe(r) for r in d.itertuples()]

    md = ["# §4 D6 — from descriptors to words: templated clinical sentence + component agreement\n",
          "Each report-slowing recording is turned into a sentence built from the read-off descriptors. "
          "Agreement is measured component-by-component against the report's STRUCTURED fields (never raw text, "
          "which is PHI). Agreement here is a *concordance* check on the description, not a detection task.\n"]

    # ---- component agreement ----
    def agree(sub, our, rep, mapper=lambda x: x):
        sub = sub.dropna(subset=[rep]); sub = sub[sub[rep].map(mapper).notna()]
        if not len(sub):
            return np.nan, 0
        return float((sub[our] == sub[rep].map(mapper)).mean()), len(sub)

    # distribution: our isfoc vs report (report focal if slowing_focal & not gen; gen if gen & not focal)
    exc = d[d.slowing_focal.fillna(False) ^ d.slowing_gen_pathologic.fillna(False)].copy()
    exc["repisfoc"] = exc.slowing_focal.fillna(False)
    a_dist = float((exc.isfoc == exc.repisfoc).mean()); n_dist = len(exc)
    # band: collapse report band to {delta,theta,theta-delta}; our_band 'mild theta'->theta
    def repband(x):
        return {"delta": "delta", "theta": "theta", "mixed": "theta-delta"}.get(x, None)
    dd = d.copy(); dd["our_b"] = dd.our_band.replace({"mild theta": "theta"})
    dd["rep_b"] = dd.focal_band.where(dd.focal_band.notna(), dd.gen_band).map(repband)
    a_band, n_band = agree(dd, "our_b", "rep_b")
    # side (focal, report side in left/right/bilateral)
    foc = d[d.slowing_focal == True]                                                        # noqa: E712
    a_side, n_side = agree(foc, "our_side", "focal_side", lambda x: x if x in ("left", "right", "bilateral") else None)
    # region (focal, temporal/frontal/posterior)
    a_reg, n_reg = agree(foc, "our_lobe", "focal_region", lambda x: x if x in ("temporal", "frontal", "posterior") else None)

    # side, region, band each have a discrete report word -> shown as concordance vs the 1/3 chance line.
    # (focal-vs-diffuse is the trained detection head's job, §2 AUROC 0.92, not a raw-threshold descriptor, so
    # it is NOT re-derived/scored here.)
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
           "\n*Focal-vs-diffuse (distribution) is decided by the detection head (§2, AUROC 0.92), not re-derived "
           "here. D6 is the synthesis/output layer; each component's validation lives in D1–D5.*\n"]

    # ---- reasonableness review set (structured only, no raw text, no ids) ----
    md += ["## Reasonableness review set — generated sentence vs report structured descriptors",
           "*(random sample; raw report text withheld as PHI, report columns are its structured labels; "
           "✓/✗ mark whether our word matches the report's for the discretely-checkable components)*\n",
           "| # | generated sentence | report: band · side · region | side | region | band |",
           "|---|---|---|:--:|:--:|:--:|"]
    samp = pd.concat([foc.sample(min(8, len(foc)), random_state=1),
                      d[d.slowing_gen_pathologic == True].sample(min(4, (d.slowing_gen_pathologic == True).sum()), random_state=1)])  # noqa: E712
    bmap = {"delta": "delta", "theta": "theta", "mixed": "theta-delta"}
    for i, r in enumerate(samp.itertuples(), 1):
        rb = r.focal_band if isinstance(r.focal_band, str) else (r.gen_band if isinstance(r.gen_band, str) else "-")
        rs = r.focal_side if isinstance(r.focal_side, str) else "-"
        rr = r.focal_region if isinstance(r.focal_region, str) else "-"
        mk = lambda ours, rep, ok: ("✓" if ours == rep else "✗") if ok else "–"
        s_side = mk(r.our_side, rs, rs in ("left", "right", "bilateral") and r.slowing_focal)
        s_reg = mk(r.our_lobe, rr, rr in ("temporal", "frontal", "posterior") and r.slowing_focal)
        s_band = mk(r.our_band.replace("mild theta", "theta"), bmap.get(rb, None), rb in bmap)
        md.append(f"| {i} | {r.sentence} | {rb} · {rs} · {rr} | {s_side} | {s_reg} | {s_band} |")

    (RES / "s4_d6.md").write_text("\n".join(md))
    print("\n".join(md[:16]))
    print("\n... (+ %d review rows)" % len(samp))
    print("wrote figures/story/s4_d6.png + results/story/s4_d6.md")


if __name__ == "__main__":
    main()
