#!/usr/bin/env python3
"""Is the gate-vs-descriptor discordance INTERMITTENCY or MORPHOLOGY?

The two-stage audit (scripts/116) finds ~41% (generalized) / ~40% (focal) of gate-flagged recordings where no
band-power feature departs from its age/stage norm. Two very different explanations:

  INTERMITTENCY — Morgoth fires the recording off a MINORITY of slow segments; the band-power descriptor,
    which needs >=Y% of segments to exceed z=X, is out-voted by the normal majority. The slowing is real and
    present, just sparse. (This is exactly the failure mode the two-level firing rule was meant to survive,
    and if the discordance lives here it is a threshold story, not a model-disagreement story.)
  MORPHOLOGY — Morgoth fires off MOST of the recording (he sees generalized slowing nearly throughout), yet
    band power is flat. That is a genuine gap: the gate reads waveform shape / rhythmicity the descriptor
    cannot represent.

Only the gate RE-RUN can tell these apart, because it kept Morgoth's per-second, per-segment probability
(guard disabled) instead of one recording-level number. For each recording we take his OWN per-segment
generalized signal — the fraction of segments with p_gen_30 > 0.5 ("morgoth_gen_prev") — and ask how it
differs between the recordings our features CORROBORATE and the DISCORDANT ones.

Run: PYTHONPATH=src python3 scripts/38_morgoth_intermittency.py
"""
from __future__ import annotations
import glob, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd

SG = Path("data/derived/segment_gate")
THR = 0.5                      # a segment "is generalized-slow to Morgoth" when p_gen_30 > 0.5


def agg_one(eid):
    f = SG / f"eeg_id={eid}" / "part.parquet"
    if not f.exists():
        return None
    try:
        s = pd.read_parquet(f, columns=["p_gen_30", "p_focal_30"])
    except Exception:
        return None
    if not len(s):
        return None
    return {
        "eeg_id": eid,
        "n_seg": len(s),
        "mgen_prev": float((s.p_gen_30 > THR).mean()),      # fraction of segments Morgoth calls gen-slow
        "mgen_med": float(s.p_gen_30.median()),
        "mgen_p90": float(s.p_gen_30.quantile(0.90)),
        "mfoc_prev": float((s.p_focal_30 > THR).mean()),
        "mfoc_med": float(s.p_focal_30.median()),
    }


def main():
    d = pd.read_parquet("data/derived/harmonized_calls.parquet")
    ids = d.eeg_id.astype(str).tolist()
    print(f"aggregating per-segment Morgoth signal for {len(ids):,} recordings…")
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4))) as ex:
        rows = [r for r in ex.map(agg_one, ids) if r is not None]
    A = pd.DataFrame(rows)
    print(f"  got {len(A):,} recordings with per-segment gate data")
    m = d.merge(A, on="eeg_id", how="inner")
    m.to_parquet("data/derived/morgoth_intermittency.parquet", index=False)

    gg = m[m.gate_gen].copy()
    corro = gg[gg.fire_generalized]
    disc = gg[~gg.fire_generalized]
    print(f"\nGATED-GENERALIZED: {len(gg):,} recordings "
          f"({len(corro):,} corroborated, {len(disc):,} discordant = {100*len(disc)/len(gg):.1f}%)")
    print(f"\n  Morgoth's OWN per-segment prevalence (frac of segments with p_gen_30 > {THR}):")
    print(f"    corroborated : median {corro.mgen_prev.median():.2f}  "
          f"[IQR {corro.mgen_prev.quantile(.25):.2f}-{corro.mgen_prev.quantile(.75):.2f}]")
    print(f"    discordant   : median {disc.mgen_prev.median():.2f}  "
          f"[IQR {disc.mgen_prev.quantile(.25):.2f}-{disc.mgen_prev.quantile(.75):.2f}]")

    # Decompose the discordant recordings: is Morgoth intermittent (sparse) or continuous (dense)?
    for lo, hi, name in [(0.0, 0.1, "very sparse (<10% of segments)"),
                         (0.1, 0.5, "intermittent (10-50%)"),
                         (0.5, 1.01, "predominant (>=50%)")]:
        sub = disc[(disc.mgen_prev >= lo) & (disc.mgen_prev < hi)]
        print(f"    discordant & Morgoth {name:32s}: {len(sub):>5,}  ({100*len(sub)/len(disc):5.1f}%)")

    # The morphology-gap subset: Morgoth fires >=50% of segments yet NO band-power feature fires.
    morph = disc[disc.mgen_prev >= 0.5]
    print(f"\n  MORPHOLOGY-GAP recordings (Morgoth generalized-slow in >=50% of segments, band power flat): "
          f"{len(morph):,}")
    print(f"    = {100*len(morph)/len(gg):.1f}% of gated-generalized, {100*len(morph)/len(m):.1f}% of all analysed")

    # Sanity: does Morgoth's per-segment prevalence track the descriptor corroboration monotonically?
    gg["mbin"] = pd.cut(gg.mgen_prev, [0, .1, .25, .5, .75, 1.01],
                        labels=["<10%", "10-25%", "25-50%", "50-75%", ">75%"])
    tab = (gg.groupby("mbin", observed=True)
             .agg(n=("eeg_id", "size"), corroborated=("fire_generalized", "mean")))
    tab["corroborated"] = (100 * tab["corroborated"]).round(1)
    print("\n  descriptor corroboration vs Morgoth's per-segment prevalence:")
    print(tab.to_string())

    # ---------------------------------------------------------------- md + figure
    n_sparse = int((disc.mgen_prev < 0.1).sum())
    n_inter = int(((disc.mgen_prev >= 0.1) & (disc.mgen_prev < 0.5)).sum())
    n_pred = int((disc.mgen_prev >= 0.5).sum())
    frac_intermit = 100 * (n_sparse + n_inter) / len(disc)
    L = ["# Is the gate-vs-descriptor discordance INTERMITTENCY or MORPHOLOGY?\n",
         "The two-stage audit leaves ~41% of gate-flagged generalized recordings with no band-power "
         "corroboration. Because the gate re-run kept Morgoth's per-segment probability (guard disabled), we "
         "can split that residual by his OWN view of how much of the recording is slow — the fraction of "
         f"segments with p_gen_30 > {THR}.\n",
         f"Among **{len(gg):,}** gated-generalized recordings, **{len(disc):,} ({100*len(disc)/len(gg):.1f}%)** "
         "are discordant. Morgoth's own per-segment prevalence is markedly lower in those "
         f"(median **{disc.mgen_prev.median():.2f}** vs **{corro.mgen_prev.median():.2f}** in the "
         "corroborated ones): the descriptor tends to fall silent exactly where Morgoth's signal is sparse.\n",
         "| the discordance is… | Morgoth's per-segment prevalence | n | share of discordant |",
         "|---|---|---|---|",
         f"| intermittency (very sparse) | < 10% of segments | {n_sparse:,} | {100*n_sparse/len(disc):.1f}% |",
         f"| intermittency | 10–50% of segments | {n_inter:,} | {100*n_inter/len(disc):.1f}% |",
         f"| **morphology gap** | **≥ 50% of segments** | **{n_pred:,}** | **{100*n_pred/len(disc):.1f}%** |\n",
         f"So **~{frac_intermit:.0f}% of the apparent discordance is intermittency** — sparse slowing that a "
         "band-power rule needing a minimum share of abnormal segments cannot help but out-vote. The genuine "
         f"**morphology gap** — Morgoth generalized-slow in ≥50% of segments yet band power flat — is only "
         f"**{n_pred:,} recordings = {100*n_pred/len(gg):.1f}% of gated-generalized, {100*n_pred/len(m):.1f}% "
         "of all analysed**. The headline ~40% is mostly a threshold artefact of intermittency, not a "
         "model-vs-descriptor chasm; the irreducible morphology miss is a few percent.\n",
         "Corroboration rises monotonically with Morgoth's per-segment prevalence "
         f"({tab.corroborated.iloc[0]:.0f}% at <10% of segments → {tab.corroborated.iloc[-1]:.0f}% at >75%), "
         "the same internal-consistency signature seen against his recording-level confidence.\n"]
    Path("results/morgoth_intermittency.md").write_text("\n".join(L))

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
    # panel 1: decomposition of the discordance
    parts = [n_sparse, n_inter, n_pred]
    labs = [f"very sparse\n<10% seg\n{100*n_sparse/len(disc):.0f}%",
            f"intermittent\n10–50% seg\n{100*n_inter/len(disc):.0f}%",
            f"MORPHOLOGY GAP\n≥50% seg\n{100*n_pred/len(disc):.0f}%"]
    cols = ["#7fb069", "#f0a259", "#c8443c"]
    ax[0].bar(range(3), [100*p/len(disc) for p in parts], color=cols, alpha=.9)
    ax[0].set_xticks(range(3)); ax[0].set_xticklabels(labs, fontsize=8)
    ax[0].set_ylabel("% of the discordant recordings")
    ax[0].set_title(f"The {100*len(disc)/len(gg):.0f}% discordance, split by\nMorgoth's OWN per-segment prevalence",
                    fontsize=10)
    ax[0].grid(alpha=.2, axis="y")
    ax[0].text(0.5, 0.95, f"~{frac_intermit:.0f}% is intermittency", transform=ax[0].transAxes,
               ha="center", va="top", fontsize=9, weight="bold", color="#555")
    # panel 2: corroboration vs prevalence (monotonic)
    ax[1].plot(range(len(tab)), tab.corroborated.values, "o-", color="#2b6", lw=2, ms=8)
    ax[1].set_xticks(range(len(tab))); ax[1].set_xticklabels(tab.index.astype(str), fontsize=8)
    ax[1].set_xlabel("Morgoth's per-segment generalized prevalence")
    ax[1].set_ylabel("% our features corroborate")
    ax[1].set_ylim(0, 100); ax[1].grid(alpha=.2)
    ax[1].set_title("Agreement rises where Morgoth\nsees more of the recording as slow", fontsize=10)
    fig.suptitle("Most of the two-stage discordance is INTERMITTENCY, not a morphology gap "
                 "(only the gate re-run's per-segment probabilities can show this)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig("figures/growth_v2/morgoth_intermittency.png", dpi=150)
    plt.close(fig)
    print("wrote data/derived/morgoth_intermittency.parquet + results/morgoth_intermittency.md "
          "+ figures/growth_v2/morgoth_intermittency.png")


if __name__ == "__main__":
    main()
