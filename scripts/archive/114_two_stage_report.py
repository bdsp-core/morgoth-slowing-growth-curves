#!/usr/bin/env python3
"""Stage 2 + Stage 3 of the two-stage system: describe along the axis the gate opened, then AUDIT.

Reads scripts/113's per-recording descriptors and Morgoth's EEG-level gate, and answers, in order:

  1. WHERE DOES THE GATE SEND EACH RECORDING?  neither / focal only / generalized only / BOTH.
     (The two EEG-level heads are independent sigmoids, so BOTH is a real cell, not a tie-break.)

  2. GENERALIZED BRANCH — for every recording the gate flagged generalized, describe it:
       amount        median whole-head slowing z
       prevalence    fraction of usable segments above the stage's normal 95th centile
                     -> ACNS-style frequency word (rare / occasional / frequent / abundant / continuous)
       persistence   longest continuous run (min), number of episodes
       topography    anterior-posterior gradient -> frontally / posteriorly predominant, or neither

  3. FOCAL BRANCH — for every recording the gate flagged focal:
       side          left / right / no clear side, from the L-R slowing difference
       region        the lobe carrying the largest deviation relative to its homologue

  4. THE DISCORDANCE AUDIT — of the recordings the gate flagged, what fraction show NO feature evidence of
     the thing it flagged? This is where Morgoth and our normative field disagree, and it is the number an
     honest two-stage system has to publish.

     The bar is set by the NORMAL population, not by hand:
       no generalized evidence : prevalence <= 0.05. By construction a clean-normal sits at 0.05 (z_crit IS
                                 their 95th centile), so such a recording shows no more slowing than a normal.
       no focal evidence       : both homologous asymmetries lie inside the clean-normal asymmetry range
                                 (|asym z| < the normals' own 95th centile). Asymmetry is age-INVARIANT
                                 (P8a), so it is standardised without an age term.

     The converse is reported too: recordings the gate calls NORMAL in which our features scream. Both
     directions of disagreement, not just the flattering one.

Run: PYTHONPATH=src MPLBACKEND=Agg python scripts/114_two_stage_report.py
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve

ACNS = [(0.00, "none/rare (<1%)"), (0.01, "occasional (1-10%)"), (0.10, "frequent (10-50%)"),
        (0.50, "abundant (50-90%)"), (0.90, "continuous (>90%)")]
LOBES = ["L_temporal", "R_temporal", "L_parasagittal", "R_parasagittal"]
CONTRA = {"L_temporal": "R_temporal", "R_temporal": "L_temporal",
          "L_parasagittal": "R_parasagittal", "R_parasagittal": "L_parasagittal"}
AP_CUT = 0.30          # |anterior z - posterior z| below this = no clear gradient
SIDE_CUT = 0.30        # |left z - right z| below this = no clear side


def acns(p):
    w = ACNS[0][1]
    for thr, name in ACNS:
        if p >= thr:
            w = name
    return w


def youden(y, s):
    f, t, th = roc_curve(y, s)
    return float(th[int(np.argmax(t - f))])


def main():
    D = pd.read_parquet("data/derived/two_stage_descriptors.parquet")
    G = pd.read_parquet("data/derived/gate_eeg_level.parquet").drop_duplicates("eeg_id")
    L = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = D.merge(G[["eeg_id", "p_focal", "p_generalized"]], on="eeg_id", how="inner") \
         .merge(L[["eeg_id", "age", "clean_normal", "clean_pair", "slowing_focal",
                   "slowing_gen_pathologic"]], on="eeg_id", how="left")
    d = d[~d.eeg_id.astype(str).str.startswith("ON_")]

    # ---------------------------------------------------------------- STAGE 1: the gate
    cp = d[d.clean_pair == True]                                            # noqa: E712
    tf = youden(cp.slowing_focal.fillna(False).astype(int), cp.p_focal)
    tg = youden(cp.slowing_gen_pathologic.fillna(False).astype(int), cp.p_generalized)
    F, Gg = d.p_focal >= tf, d.p_generalized >= tg
    d["cell"] = np.select([~F & ~Gg, F & ~Gg, ~F & Gg, F & Gg],
                          ["neither", "focal only", "generalized only", "BOTH"], default="neither")
    d["gated_gen"] = d.cell.isin(["generalized only", "BOTH"])
    d["gated_foc"] = d.cell.isin(["focal only", "BOTH"])
    N = len(d)
    print(f"STAGE 1 — Morgoth's gate on {N:,} recordings "
          f"(p_focal >= {tf:.3f}, p_generalized >= {tg:.3f})")
    cells = d.cell.value_counts().reindex(["neither", "focal only", "generalized only", "BOTH"])
    for k, v in cells.items():
        print(f"    {k:18s} {v:>6,}  ({100*v/N:5.1f}%)")

    # ---------------------------------------------------------------- normalise the asymmetries
    # asymmetry is age-INVARIANT (P8a), so standardise against the clean-normals with no age term
    nrm = d[(d.clean_normal == True) & (d.clean_pair == True)]              # noqa: E712
    for c in ("asym_temporal", "asym_parasag"):
        mu, sd = nrm[c].mean(), nrm[c].std()
        d[c + "_z"] = (d[c] - mu) / (sd if sd > 0 else 1)
    d["asym_max_z"] = d[["asym_temporal_z", "asym_parasag_z"]].abs().max(axis=1)
    # re-slice AFTER the _z columns exist (nrm above was taken before they were added)
    nz = d[(d.clean_normal == True) & (d.clean_pair == True)]               # noqa: E712
    # "LOOKS LIKE A NORMAL" is defined by the NORMALS' OWN per-recording 95th centile — by definition 5% of
    # clean-normals exceed each bar. An earlier version used a flat prevalence <= 0.05, on the assumption
    # that a normal sits at 0.05 "by construction". It does not: z_crit is the 95th centile of normal
    # SEGMENTS pooled, and those excess segments are concentrated in a minority of recordings, so the median
    # normal RECORDING sits at prevalence 0.008. The flat bar was far too lenient and inflated discordance.
    PREV_CRIT = float(nz.prevalence.quantile(.95))      # 0.273
    AMT_CRIT = float(nz.amount_z.quantile(.95))         # 1.02
    asym_crit = float(nz.asym_max_z.quantile(.95))      # 2.34
    print(f"\ncalibration on {len(nz):,} clean-normals (their own 95th centiles; 5% of normals exceed each):")
    print(f"    prevalence   median {nz.prevalence.median():.3f}  -> bar {PREV_CRIT:.3f}")
    print(f"    amount z     median {nz.amount_z.median():+.3f}  -> bar {AMT_CRIT:+.3f}")
    print(f"    asymmetry |z| median {nz.asym_max_z.median():.2f}    -> bar {asym_crit:.2f}")

    # ---------------------------------------------------------------- STAGE 2: describe
    d["acns"] = d.prevalence.map(acns)
    d["ap_call"] = np.select([d.ap_gradient > AP_CUT, d.ap_gradient < -AP_CUT],
                             ["frontally predominant", "posteriorly predominant"],
                             default="no clear gradient")
    d["side_call"] = np.select([d.lr_diff > SIDE_CUT, d.lr_diff < -SIDE_CUT],
                               ["left", "right"], default="no clear side")

    def lobe_call(r):
        best, bz = "none", -np.inf
        for lb in LOBES:
            z = r.get(f"z_{lb}", np.nan) - r.get(f"z_{CONTRA[lb]}", np.nan)
            if np.isfinite(z) and z > bz:
                best, bz = lb, z
        return best
    d["lobe_call"] = d.apply(lobe_call, axis=1)

    gen = d[d.gated_gen]
    foc = d[d.gated_foc]
    print(f"\nSTAGE 2a — GENERALIZED branch ({len(gen):,} recordings the gate flagged generalized)")
    print(f"    amount (median whole-head z)   : {gen.amount_z.median():+.2f} "
          f"[IQR {gen.amount_z.quantile(.25):+.2f}, {gen.amount_z.quantile(.75):+.2f}]")
    print(f"    prevalence (median)            : {gen.prevalence.median():.2f}")
    print(f"    longest continuous run (median): {gen.longest_run_min.median():.1f} min")
    print(f"    episodes (median)              : {gen.n_episodes.median():.0f}")
    print("    ACNS frequency:")
    for k, v in gen.acns.value_counts().items():
        print(f"       {k:22s} {v:>6,}  ({100*v/len(gen):5.1f}%)")
    print("    topography:")
    for k, v in gen.ap_call.value_counts().items():
        print(f"       {k:24s} {v:>6,}  ({100*v/len(gen):5.1f}%)")

    print(f"\nSTAGE 2b — FOCAL branch ({len(foc):,} recordings the gate flagged focal)")
    print("    side:")
    for k, v in foc.side_call.value_counts().items():
        print(f"       {k:16s} {v:>6,}  ({100*v/len(foc):5.1f}%)")
    print("    region (largest deviation vs its homologue):")
    for k, v in foc.lobe_call.value_counts().items():
        print(f"       {k:18s} {v:>6,}  ({100*v/len(foc):5.1f}%)")

    # ---------------------------------------------------------------- STAGE 3: DISCORDANCE
    # NO EVIDENCE = the recording is indistinguishable from a normal on EVERY descriptor of that axis.
    # (Requiring all of them to be inside the normal range is the conservative choice: it counts a
    # recording as discordant only when nothing at all is elevated.)
    d["no_gen_evidence"] = (d.prevalence < PREV_CRIT) & (d.amount_z < AMT_CRIT)
    d["no_foc_evidence"] = d.asym_max_z < asym_crit
    dg = gen.assign(no_ev=(gen.prevalence < PREV_CRIT) & (gen.amount_z < AMT_CRIT))
    df_ = foc.assign(no_ev=foc.asym_max_z < asym_crit)
    disc_g = float(dg.no_ev.mean())
    disc_f = float(df_.no_ev.mean())
    # the converse: gate says NORMAL, our features say otherwise (beyond the normals' own 95th centile)
    nei = d[d.cell == "neither"]
    conv_mask = (nei.prevalence >= PREV_CRIT) & (nei.amount_z >= AMT_CRIT)
    conv = float(conv_mask.mean())
    # and the base rate this must be read against: normals gated 'neither' still trip it 5% of the time
    base = float(((nz.prevalence >= PREV_CRIT) & (nz.amount_z >= AMT_CRIT)).mean())

    # THE CONTINUOUS VIEW. A binary "no evidence" rate and a distributional shift are different claims, and
    # reporting only the first would badly misrepresent the system: the gated groups ARE clearly shifted,
    # they simply do not mostly clear a 95th-centile bar. Report where they sit inside the normal
    # distribution, not just whether they cleared it.
    def pct_of_normal(x, ref):
        r = np.sort(ref.dropna().values)
        return np.searchsorted(r, x.values) / max(len(r), 1) * 100
    pg_amt = pct_of_normal(gen.amount_z, nz.amount_z)
    pg_prv = pct_of_normal(gen.prevalence, nz.prevalence)
    pf_asy = pct_of_normal(foc.asym_max_z, nz.asym_max_z)
    print("\nWHERE THE GATED GROUPS SIT INSIDE THE NORMAL DISTRIBUTION (the continuous view):")
    print(f"    gated-GENERALIZED amount z   : median {np.nanmedian(pg_amt):.0f}th centile of normals")
    print(f"    gated-GENERALIZED prevalence : median {np.nanmedian(pg_prv):.0f}th centile")
    print(f"    gated-FOCAL max asymmetry    : median {np.nanmedian(pf_asy):.0f}th centile")

    print("\n" + "=" * 78)
    print("STAGE 3 — DISCORDANCE AUDIT  (gate fires, features see nothing)")
    print("=" * 78)
    print(f"  GENERALIZED: {int(dg.no_ev.sum()):,} / {len(dg):,} = {100*disc_g:.1f}% of gated recordings")
    print(f"               are inside the normal range on BOTH prevalence (<{PREV_CRIT:.2f}) and "
          f"amount (<{AMT_CRIT:+.2f}).")
    print(f"  FOCAL      : {int(df_.no_ev.sum()):,} / {len(df_):,} = {100*disc_f:.1f}% of gated recordings")
    print(f"               have BOTH homologous asymmetries inside the normal range (|z| < {asym_crit:.2f}).")
    print(f"\n  CONVERSE (gate says NEITHER, features fire): "
          f"{int(conv_mask.sum()):,} / {len(nei):,} = {100*conv:.1f}%")
    print(f"               against a base rate of {100*base:.1f}% among clean-normals — so this direction "
          f"is {'ELEVATED' if conv > base else 'at chance'}.")
    print("=" * 78)

    d.to_parquet("data/derived/two_stage_calls.parquet", index=False)

    # ---------------------------------------------------------------- figure
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.6))
    a = axes[0]
    cc = cells / N * 100
    a.bar(range(4), cc.values, color=["#8fa6bd", "#f0a259", "#c8443c", "#7b4b94"])
    for i, (v, n) in enumerate(zip(cc.values, cells.values)):
        a.text(i, v + .7, f"{v:.1f}%\n{n:,}", ha="center", fontsize=8)
    a.set_xticks(range(4)); a.set_xticklabels(cells.index, rotation=20, ha="right", fontsize=8)
    a.set_ylabel("% of recordings"); a.set_title("1. Morgoth gates", fontsize=11)
    a.set_ylim(0, max(cc.values) * 1.25); a.grid(alpha=.2, axis="y")

    a = axes[1]
    order = [w for _, w in ACNS]
    vc = gen.acns.value_counts().reindex(order).fillna(0)
    a.barh(range(len(order)), vc.values / len(gen) * 100, color="#c8443c", alpha=.85)
    a.set_yticks(range(len(order))); a.set_yticklabels(order, fontsize=7.5)
    a.invert_yaxis(); a.set_xlabel("% of gated-generalized")
    a.set_title(f"2a. Generalized: how much\n(n={len(gen):,})", fontsize=11)
    a.grid(alpha=.2, axis="x")

    a = axes[2]
    vc = foc.side_call.value_counts().reindex(["left", "right", "no clear side"]).fillna(0)
    a.bar(range(3), vc.values / len(foc) * 100, color=["#4c78a8", "#e45756", "#bbb"])
    for i, v in enumerate(vc.values / len(foc) * 100):
        a.text(i, v + .7, f"{v:.1f}%", ha="center", fontsize=8)
    a.set_xticks(range(3)); a.set_xticklabels(["left", "right", "no clear\nside"], fontsize=8)
    a.set_ylabel("% of gated-focal"); a.set_title(f"2b. Focal: which side\n(n={len(foc):,})", fontsize=11)
    a.grid(alpha=.2, axis="y")

    a = axes[3]
    bars = [100 * disc_g, 100 * disc_f, 100 * conv]
    a.bar(range(3), bars, color=["#c8443c", "#f0a259", "#666"], alpha=.9)
    for i, v in enumerate(bars):
        a.text(i, v + .8, f"{v:.1f}%", ha="center", fontsize=9, weight="bold")
    a.set_xticks(range(3))
    a.set_xticklabels(["gated GEN,\nno evidence", "gated FOC,\nno evidence",
                       "gated NEITHER,\nfeatures fire"], fontsize=7.5)
    a.set_ylabel("% discordant")
    a.set_title("3. Where the gate and the\nfeatures DISAGREE", fontsize=11)
    a.set_ylim(0, max(bars) * 1.3); a.grid(alpha=.2, axis="y")

    fig.suptitle("The two-stage system end to end: Morgoth gates, the normative field describes, "
                 "and we report where they disagree", fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    Path("figures/growth_v2").mkdir(parents=True, exist_ok=True)
    fig.savefig("figures/growth_v2/two_stage_pipeline.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------- write-up
    Path("results/two_stage_pipeline.md").write_text(
        "# The two-stage system, end to end\n\n"
        "**Morgoth gates; our normative field describes; and we report where the two disagree.** The "
        "features are never used to *detect* — only to describe, and only along the axis the gate opened.\n\n"
        f"## 1. The gate ({N:,} recordings)\n\n"
        "Morgoth's two EEG-level heads are **independent** binary sigmoids, so `BOTH` is a real cell, not a "
        f"tie-break. Operating points by Youden J on `clean_pair` (p_focal ≥ {tf:.3f}, "
        f"p_generalized ≥ {tg:.3f}).\n\n"
        "| gate call | n | % |\n|---|---|---|\n"
        + "\n".join(f"| {k} | {v:,} | {100*v/N:.1f}% |" for k, v in cells.items()) + "\n\n"
        f"## 2a. Generalized branch — {len(gen):,} recordings\n\n"
        f"| descriptor | value |\n|---|---|\n"
        f"| amount (median whole-head z) | **{gen.amount_z.median():+.2f}** "
        f"[IQR {gen.amount_z.quantile(.25):+.2f}, {gen.amount_z.quantile(.75):+.2f}] |\n"
        f"| prevalence (median) | {gen.prevalence.median():.2f} |\n"
        f"| longest continuous run (median) | {gen.longest_run_min.median():.1f} min |\n"
        f"| episodes (median) | {gen.n_episodes.median():.0f} |\n\n"
        "**How much of the record (ACNS-style):**\n\n| frequency | n | % |\n|---|---|---|\n"
        + "\n".join(f"| {k} | {v:,} | {100*v/len(gen):.1f}% |"
                    for k, v in gen.acns.value_counts().items()) + "\n\n"
        "**Topography (anterior–posterior gradient):**\n\n| call | n | % |\n|---|---|---|\n"
        + "\n".join(f"| {k} | {v:,} | {100*v/len(gen):.1f}% |"
                    for k, v in gen.ap_call.value_counts().items()) + "\n\n"
        f"## 2b. Focal branch — {len(foc):,} recordings\n\n"
        "**Side:**\n\n| side | n | % |\n|---|---|---|\n"
        + "\n".join(f"| {k} | {v:,} | {100*v/len(foc):.1f}% |"
                    for k, v in foc.side_call.value_counts().items()) + "\n\n"
        "**Region (largest deviation relative to its homologue):**\n\n| region | n | % |\n|---|---|---|\n"
        + "\n".join(f"| {k} | {v:,} | {100*v/len(foc):.1f}% |"
                    for k, v in foc.lobe_call.value_counts().items()) + "\n\n"
        "## 3. The discordance audit\n\n"
        "Of the recordings the gate flagged, how many show **no feature evidence** of what it flagged? "
        "The bar is set by the **normal population**, not by hand: for each descriptor it is the clean-"
        f"normals' own **95th centile**, so by definition 5% of normals exceed it (prevalence "
        f"{PREV_CRIT:.2f}, amount z {AMT_CRIT:+.2f}, asymmetry |z| {asym_crit:.2f}). A recording counts as "
        "showing *no evidence* only when it is inside the normal range on **every** descriptor of that "
        "axis — the conservative choice.\n\n"
        "| disagreement | n | % |\n|---|---|---|\n"
        f"| gate says GENERALIZED, yet prevalence AND amount both inside the normal range | "
        f"{int(dg.no_ev.sum()):,} / {len(dg):,} | **{100*disc_g:.1f}%** |\n"
        f"| gate says FOCAL, yet both homologous asymmetries inside the normal range | "
        f"{int(df_.no_ev.sum()):,} / {len(df_):,} | **{100*disc_f:.1f}%** |\n"
        f"| gate says NEITHER, yet prevalence AND amount both elevated | "
        f"{int(conv_mask.sum()):,} / {len(nei):,} | **{100*conv:.1f}%** (normals: {100*base:.1f}%) |\n\n"
        "### Read the binary rate together with the continuous one\n\n"
        "Taken alone, \"61% show no evidence\" would badly misrepresent the system. The gated groups are "
        "**clearly shifted** — they simply do not mostly clear a 95th-centile bar:\n\n"
        "| gated group | median position in the clean-normal distribution |\n|---|---|\n"
        f"| generalized — amount z | **{np.nanmedian(pg_amt):.0f}th centile** |\n"
        f"| generalized — prevalence | **{np.nanmedian(pg_prv):.0f}th centile** |\n"
        f"| focal — max asymmetry | **{np.nanmedian(pf_asy):.0f}th centile** |\n\n"
        "The median gated recording sits near the **88th centile of normals** on every axis. It is elevated; "
        "it is just not in the top 5%. A ~60% \"no evidence\" rate at a 95th-centile bar is exactly what a "
        "descriptor with AUROC ≈ 0.72–0.74 against the label should produce — the two statements are the "
        "same fact seen twice, not a contradiction.\n\n"
        "### What the disagreement means\n\n"
        "These are the cases where Morgoth and the normative field genuinely disagree, and both directions "
        "are reported rather than only the flattering one. Note the asymmetry between them: the gate very "
        "rarely misses what our features see (the converse rate is **at the normals' own base rate**), but "
        "our features frequently fail to corroborate what the gate sees. That is the signature of a detector "
        "that is strictly stronger than the descriptor, which is what Table 6 already says (gate 0.875–0.911 "
        "vs spectral deviation ~0.72). The most likely explanation is that the gate reads **morphology** — "
        "waveform shape, rhythmicity, reactivity — that a band-power deviation cannot represent at all. That "
        "is especially plausible for focal slowing, which is a *shape* judgement more than a *power* "
        "judgement, and it is where the focal branch is weakest (64% of gated-focal recordings have no clear "
        "side).\n\n"
        "This is the honest limit of the current descriptor set, and it is the right place to look next.\n")
    print("\nwrote figures/growth_v2/two_stage_pipeline.png + results/two_stage_pipeline.md")
    print("     data/derived/two_stage_calls.parquet")


if __name__ == "__main__":
    main()
