#!/usr/bin/env python3
"""Harmonise the descriptor with Morgoth, then describe — and audit what is left over.

THE FRAME. Morgoth's call is TAKEN AS TRUTH. Our job is not to re-detect; it is to say, faithfully, *in
which way* the EEG is abnormal and *how much*. So the descriptor's own free parameters should be set to
agree with Morgoth as well as they possibly can, and whatever disagreement SURVIVES that is the real,
irreducible thing worth reporting.

THE FIRING RULE is two-level, per feature (MBW):
    a SEGMENT fires for feature f  <=>  its abnormality z exceeds X
    the RECORDING fires for f      <=>  at least Y% of its segments fire
    the RECORDING has EVIDENCE     <=>  ANY feature fires   (features are independent; one may be elevated
                                        while the others are not, and the description says WHICH)
Severity is NOT part of the rule. It is the CONDITIONAL severity — the median z among the FIRING segments —
and it is a descriptor. So is persistence (longest run, episodes). Intermittent slowing is something to
DESCRIBE, never a reason to say nothing is there.

CHOOSING (X, Y). Both are free. They are chosen by GRID SEARCH to maximise Cohen's kappa against Morgoth's
gate call, FIT on a patient-split TRAIN half and REPORTED on a held-out TEST half, so two free parameters
cannot buy a flattering number. The discordance we then report is the BEST ACHIEVABLE — not an artefact of
someone's favourite percentile.

Run: PYTHONPATH=src MPLBACKEND=Agg python scripts/116_harmonize_and_describe.py
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import cohen_kappa_score, balanced_accuracy_score, roc_curve

UP = ["log_delta", "log_theta", "rel_delta", "log_DAR", "log_TAR"]
DOWN = ["rel_alpha"]
FEATS = UP + DOWN
LABEL = {"log_delta": "delta excess", "log_theta": "theta excess", "rel_delta": "relative delta excess",
         "log_DAR": "delta/alpha ratio", "log_TAR": "theta/alpha ratio", "rel_alpha": "paucity of alpha"}
PAIRS = ["L_temporal|R_temporal", "L_parasagittal|R_parasagittal"]
XG = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
YG = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
ACNS = [(0.00, "none/rare (<1%)"), (0.01, "occasional (1-10%)"), (0.10, "frequent (10-50%)"),
        (0.50, "abundant (50-90%)"), (0.90, "continuous (>90%)")]


def acns(p):
    w = ACNS[0][1]
    for t, n in ACNS:
        if p >= t:
            w = n
    return w


def youden(y, s):
    f, t, th = roc_curve(y, s)
    return float(th[int(np.argmax(t - f))])


def fires(D, kind, region_or_pair, X, Y):
    """boolean: does ANY feature fire at (X, Y)?  plus the per-feature matrix."""
    cols = {f: f"{kind}|{f}|{region_or_pair}|{X}" for f in FEATS}
    M = pd.DataFrame({f: (D[c] >= Y) if c in D.columns else False for f, c in cols.items()},
                     index=D.index)
    return M.any(axis=1), M


def grid_search(D, target, kind, keys, tr):
    """pick (X, Y) maximising Cohen kappa vs Morgoth on the TRAIN half."""
    best = (-1, None, None)
    rows = []
    for X in XG:
        for Y in YG:
            any_fire = None
            for k in keys:
                f, _ = fires(D, kind, k, X, Y)
                any_fire = f if any_fire is None else (any_fire | f)
            kp = cohen_kappa_score(target[tr], any_fire[tr])
            ba = balanced_accuracy_score(target[tr], any_fire[tr])
            rows.append({"X": X, "Y": Y, "kappa": kp, "bal_acc": ba,
                         "fire_rate": float(any_fire[tr].mean())})
            if kp > best[0]:
                best = (kp, X, Y)
    return best[1], best[2], pd.DataFrame(rows)


def main():
    D = pd.read_parquet("data/derived/descriptor_grid.parquet")
    G = pd.read_parquet("data/derived/gate_eeg_level.parquet").drop_duplicates("eeg_id")
    L = pd.read_parquet("data/derived/recording_labels_sap.parquet").drop_duplicates("eeg_id")
    d = D.merge(G[["eeg_id", "p_focal", "p_generalized"]], on="eeg_id") \
         .merge(L[["eeg_id", "patient_id", "clean_pair", "clean_normal",
                   "slowing_focal", "slowing_gen_pathologic"]], on="eeg_id", how="left")
    d = d[~d.eeg_id.astype(str).str.startswith("ON_")].reset_index(drop=True)

    cp = d[d.clean_pair == True]                                          # noqa: E712
    tf = youden(cp.slowing_focal.fillna(False).astype(int), cp.p_focal)
    tg = youden(cp.slowing_gen_pathologic.fillna(False).astype(int), cp.p_generalized)
    d["gate_gen"] = d.p_generalized >= tg
    d["gate_foc"] = d.p_focal >= tf
    print(f"{len(d):,} recordings | Morgoth: generalized {d.gate_gen.mean()*100:.1f}%, "
          f"focal {d.gate_foc.mean()*100:.1f}%")

    # patient-split train/test so two free parameters cannot overfit
    pats = d.patient_id.dropna().unique()
    rng = np.random.default_rng(0)
    tr_p = set(rng.choice(pats, int(.5 * len(pats)), replace=False))
    tr = d.patient_id.isin(tr_p).values
    te = ~tr
    print(f"train {tr.sum():,} / test {te.sum():,} recordings, split by PATIENT\n")

    out = {}
    for axis, target, kind, keys in [
            ("generalized", d.gate_gen.values, "prev", ["whole_head"]),
            ("focal", d.gate_foc.values, "aprev", PAIRS)]:
        X, Y, tab = grid_search(d, target, kind, keys, tr)
        any_fire, _ = None, None
        for k in keys:
            f, _ = fires(d, kind, k, X, Y)
            any_fire = f if any_fire is None else (any_fire | f)
        kp_te = cohen_kappa_score(target[te], any_fire[te])
        ba_te = balanced_accuracy_score(target[te], any_fire[te])
        gated = target & te
        disc = float((~any_fire[gated]).mean())
        conv = float(any_fire[(~target) & te].mean())
        out[axis] = {"X": X, "Y": Y, "kappa_test": round(kp_te, 3), "bal_acc_test": round(ba_te, 3),
                     "n_gated_test": int(gated.sum()),
                     "discordance": round(disc, 4), "converse": round(conv, 4)}
        d[f"fire_{axis}"] = any_fire
        print(f"=== {axis.upper()} ===")
        print(f"  harmonised operating point: segment z > {X}, in >= {Y*100:.0f}% of segments")
        print(f"  (chosen on TRAIN by Cohen kappa; TEST kappa {kp_te:.3f}, balanced acc {ba_te:.3f})")
        print(f"  DISCORDANCE (gate fires, no feature fires): {100*disc:.1f}%  "
              f"of {int(gated.sum()):,} gated test recordings")
        print(f"  converse   (gate silent, a feature fires): {100*conv:.1f}%\n")
        tab.to_csv(f"results/harmonization_grid_{axis}.csv", index=False)

    # ---------------------------------------------------------------- DESCRIBE (on the harmonised point)
    Xg, Yg = out["generalized"]["X"], out["generalized"]["Y"]
    Xf, Yf = out["focal"]["X"], out["focal"]["Y"]
    gen = d[d.gate_gen]
    foc = d[d.gate_foc]

    _, Mg = fires(d, "prev", "whole_head", Xg, Yg)
    per_feat = {LABEL[f]: float(Mg.loc[d.gate_gen, f].mean()) for f in FEATS}
    print("WHICH FEATURE fires, among the recordings Morgoth calls generalized "
          f"(z > {Xg} in >= {Yg*100:.0f}% of segments):")
    for k, v in sorted(per_feat.items(), key=lambda x: -x[1]):
        print(f"    {k:24s} {100*v:5.1f}%")

    # how many features fire at once (are they redundant, or independent statements?)
    nfire = Mg.loc[d.gate_gen].sum(axis=1)
    print("\nhow many of the 6 features fire together:")
    for k, v in nfire.value_counts().sort_index().items():
        print(f"    {int(k)} feature(s): {v:>6,}  ({100*v/len(nfire):5.1f}%)")

    # severity / persistence / ACNS at the harmonised point, for the recordings that DO fire
    sev_c = f"sev|log_delta|whole_head|{Xg}"
    prev_c = f"prev|log_delta|whole_head|{Xg}"
    run_c = f"run|log_delta|whole_head|{Xg}"
    eps_c = f"eps|log_delta|whole_head|{Xg}"
    fg = gen[gen.fire_generalized]
    print(f"\nDESCRIPTION of the {len(fg):,} gated-generalized recordings that our features corroborate:")
    print(f"    prevalence (delta)      median {fg[prev_c].median():.2f}  -> "
          f"'{acns(float(fg[prev_c].median()))}'")
    print(f"    conditional severity    median z {fg[sev_c].median():+.2f}  (among FIRING segments only)")
    print(f"    longest continuous run  median {fg[run_c].median():.1f} min")
    print(f"    episodes                median {fg[eps_c].median():.0f}")

    _, Mf = fires(d, "aprev", PAIRS[0], Xf, Yf)
    side_c = f"aside|log_delta|{PAIRS[0]}|{Xf}"
    ff = foc[foc.fire_focal]
    side = np.where(ff[side_c] > 0.2, "left", np.where(ff[side_c] < -0.2, "right", "no clear side"))
    print(f"\nDESCRIPTION of the {len(ff):,} gated-focal recordings that our features corroborate:")
    for k, v in pd.Series(side).value_counts().items():
        print(f"    side {k:16s} {v:>6,}  ({100*v/len(ff):5.1f}%)")

    d.to_parquet("data/derived/harmonized_calls.parquet", index=False)
    json.dump(out, open("results/harmonization.json", "w"), indent=2)

    # ---------------------------------------------------------------- figure
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    g = pd.read_csv("results/harmonization_grid_generalized.csv")
    piv = g.pivot(index="Y", columns="X", values="kappa")
    im = axes[0].imshow(piv.values, aspect="auto", cmap="viridis", origin="lower")
    axes[0].set_xticks(range(len(piv.columns))); axes[0].set_xticklabels(piv.columns, fontsize=7)
    axes[0].set_yticks(range(len(piv.index)))
    axes[0].set_yticklabels([f"{v*100:.0f}%" for v in piv.index], fontsize=7)
    axes[0].set_xlabel("X — segment z threshold"); axes[0].set_ylabel("Y — % of segments that must fire")
    bi = np.unravel_index(np.nanargmax(piv.values), piv.shape)
    axes[0].plot(bi[1], bi[0], "r*", ms=16)
    axes[0].set_title(f"Harmonising with Morgoth (generalized)\nbest kappa {piv.values.max():.3f} "
                      f"at z>{Xg}, >={Yg*100:.0f}% of segments", fontsize=10)
    plt.colorbar(im, ax=axes[0], label="Cohen kappa vs Morgoth")

    a = axes[1]
    k = list(per_feat.keys()); v = [100 * per_feat[x] for x in k]
    o = np.argsort(v)
    a.barh(range(len(k)), [v[i] for i in o], color="#c8443c", alpha=.85)
    a.set_yticks(range(len(k))); a.set_yticklabels([k[i] for i in o], fontsize=8)
    a.set_xlabel("% of gated-generalized recordings in which it fires")
    a.set_title("WHICH WAY is it abnormal?\n(features evaluated independently)", fontsize=10)
    a.grid(alpha=.2, axis="x")

    a = axes[2]
    bars = [100 * out["generalized"]["discordance"], 100 * out["focal"]["discordance"],
            100 * out["generalized"]["converse"]]
    a.bar(range(3), bars, color=["#c8443c", "#f0a259", "#666"], alpha=.9)
    for i, vv in enumerate(bars):
        a.text(i, vv + .8, f"{vv:.1f}%", ha="center", fontsize=9, weight="bold")
    a.set_xticks(range(3))
    a.set_xticklabels(["gated GEN,\nno feature fires", "gated FOC,\nno feature fires",
                       "gate silent,\nfeature fires"], fontsize=7.5)
    a.set_ylabel("% (held-out patients)")
    a.set_title("Discordance AT THE BEST\nACHIEVABLE operating point", fontsize=10)
    a.set_ylim(0, max(bars) * 1.35); a.grid(alpha=.2, axis="y")

    fig.suptitle("Morgoth is truth; our features describe. The firing rule is harmonised to him, "
                 "then the residual disagreement is reported.", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig("figures/growth_v2/harmonized_two_stage.png", dpi=150)
    plt.close(fig)
    print("\nwrote figures/growth_v2/harmonized_two_stage.png + results/harmonization.json")


if __name__ == "__main__":
    main()
