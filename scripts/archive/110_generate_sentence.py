"""Generate the clinical description sentence from the gate + the deviation-field descriptors, STRICTLY
against docs/claims_table.md. Every clause is tagged with its claims-table row and status; FORBIDDEN clauses
(severity adjective, frequency word, band-if-not-earned, peak-SD) are never emitted.

Flow (docs/description_architecture.md §1a): Morgoth gates -> branch -> describe.
  gate fires generalized -> AP gradient (diffuse default), band (low-confidence), amount (SD + centile),
                            prevalence (%), persistence, stage-accentuation
  gate fires focal       -> side, max-deviation lobe (provisional), band (low-conf), amount, prevalence,
                            persistence, stage-accentuation ; ABSTAIN if no lobar excess
  neither                -> "No pathological slowing."

ALLOWED (assert): presence + focal/generalized (gate); amount in SD + centile; paucity of faster activity
  (alpha attenuation, wake only); side; prevalence %; stage-accentuation / sleep-only; the abstain path.
PROVISIONAL (hedge): lobe ("maximal in ..."), AP predominance (only if AP clears the normal centile),
  band (low-confidence delta/theta/mixed), persistence.
FORBIDDEN (never): focal-vs-gen from our features; ACNS frequency words; mild/moderate/marked; peak SD.

Run: PYTHONPATH=src python scripts/110_generate_sentence.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm

TAU_GEN, TAU_FOC = 0.40, 0.50          # gate operating points (scripts/112)
ALERT = ["W", "N1"]


def centile(sd):
    return f"{norm.cdf(sd) * 100:.0f}th centile"


def band_word(band_index):
    # PROVISIONAL, low-confidence (rel-power difference ~0.64 vs report word). band_index > 0 -> theta.
    if not np.isfinite(band_index) or abs(band_index) < 0.05:
        return "mixed theta/delta"
    return "theta-predominant" if band_index > 0 else "delta-predominant"


def persistence(rec):
    if rec.longest_run_min < 0.3:
        return None
    return f"longest run {rec.longest_run_min:.1f} min over {int(rec.n_episodes)} episode(s)"


def describe(bid, gate, D, ap, age, e_thr):
    d = D[D.bdsp_id == bid]
    if len(d) == 0:
        return None
    alert = d[d.stage.isin(ALERT)]
    if len(alert) == 0:
        alert = d
    # describe the alert stage where slowing actually MANIFESTS (highest prevalence), tie-break by amount
    top = alert.sort_values(["prevalence", "amount_median"], ascending=False).iloc[0]
    pg, pf = gate.p_generalized, gate.p_focal
    clauses = []

    if pf < TAU_FOC and pg < TAU_GEN:
        return ("No pathological slowing.", [("(gate below threshold)", "1", "ALLOWED")])

    if pf >= TAU_FOC:                                        # ---- FOCAL branch
        E = d.focal_excess.max()
        side = d.loc[d.focal_excess.idxmax()].focal_side if np.isfinite(E) else None
        region = d.loc[d.focal_excess.idxmax()].focal_region if np.isfinite(E) else None
        if not np.isfinite(E) or E < e_thr:                 # ABSTAIN (claims row 11): E below normal 97th centile
            return (f"Focal slowing by pattern; no lateralizing spectral excess above the normal range.",
                    [("focal (gate)", "2", "ALLOWED"), (f"abstain: E<{e_thr:.2f} SD (normal 97th centile)", "11", "ALLOWED")])
        loc = f"{side}-sided slowing" if side else "focal slowing"
        clauses.append((loc, "4", "ALLOWED (side)"))
        if region:
            clauses.append((f"maximal in the {region.replace('_', ' ')} region", "4b", "PROVISIONAL"))
        head = loc + (f", maximal in the {region.replace('_',' ')} region" if region else "")
    else:                                                    # ---- GENERALIZED branch
        apc = ap.get(bid, "diffuse")
        pred = "" if apc == "diffuse" else f", {apc}ly predominant"
        clauses.append(("generalized slowing", "2", "ALLOWED"))
        if apc != "diffuse":
            clauses.append((f"{apc}ly predominant", "4d", "PROVISIONAL (low-confidence)"))
        head = "Generalized slowing" + pred

    # amount (ALLOWED) — SD + centile, on the max-alert stage
    sd = top.amount_median
    clauses.append((f"{sd:.1f} SD above age- and stage-matched normal ({centile(sd)})", "3", "ALLOWED"))
    amt = f"{sd:.1f} SD above age- and stage-matched normal ({centile(sd)})"
    # paucity of faster activity (ALLOWED, wake only)
    paucity = ""
    if top.stage == "W" and top.alpha_attenuation > 0.5:
        paucity = ", with paucity of faster activity"
        clauses.append(("with paucity of faster activity", "3b", "ALLOWED (wake)"))
    # band (PROVISIONAL, low-confidence)
    bw = band_word(top.band_index)
    clauses.append((bw + " (low-confidence)", "5", "PROVISIONAL"))
    # prevalence (ALLOWED, %) -- only assert presence if above the normal rate; else diffuse elevation
    if top.prevalence > 0.05:
        prev = f"present in {top.prevalence*100:.0f}% of {top.stage} segments"
        clauses.append((prev, "6", "ALLOWED"))
    else:
        prev = f"diffusely, without discrete abnormal segments in {top.stage}"
        clauses.append((prev, "6", "ALLOWED (sub-threshold)"))
    # persistence (PROVISIONAL)
    per = persistence(top)
    if per: clauses.append((per, "7", "PROVISIONAL"))
    # stage-accentuation / sleep-only (ALLOWED)
    acc = ""
    if bool(d.sleep_only.any()):
        acc = "; present only during sleep"
        clauses.append(("present only during sleep", "8", "ALLOWED"))
    elif top.stage != d.accentuated_stage.iloc[0]:
        acc = f"; accentuated in {d.accentuated_stage.iloc[0]}"
        clauses.append((f"accentuated in {d.accentuated_stage.iloc[0]}", "8", "ALLOWED"))

    sentence = f"{head}, {bw}; {amt}{paucity}; {prev}" + (f"; {per}" if per else "") + acc + "."
    sentence = sentence[0].upper() + sentence[1:]
    return sentence, clauses


def main():
    g = pd.read_parquet("data/derived/gate_probs.parquet").set_index("bdsp_id")
    D = pd.read_parquet("data/derived/description_descriptors.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id").set_index("bdsp_id")
    try:
        apdf = pd.read_parquet("data/derived/gen_ap_gradient.parquet").set_index("bdsp_id")
        ap = apdf.ap_call.to_dict()
    except Exception:
        ap = {}
    # abstain threshold = 97th centile of focal_excess in clean-normals (claims row 11)
    ne = D[D.stage.isin(ALERT)].groupby("bdsp_id").focal_excess.max()
    ncn = ne[ne.index.isin(lu[lu.clean_normal == True].index)]
    e_thr = float(np.nanpercentile(ncn, 97))
    print(f"focal abstain threshold (normal 97th centile of E) = {e_thr:.2f} SD\n")

    # pick illustrative recordings: a focal, a generalized, a normal, an abstain, a sleep-only
    ids = {}
    ids["generalized"] = g[(g.p_generalized >= 0.6) & (g.lab_gen == 1)].index[:2]
    ids["focal"] = g[(g.p_focal >= 0.6) & (g.lab_focal == 1)].index[:1]
    # a focal case with a REAL lateralizing excess (clears abstain), to show the non-abstain sentence
    _foc_E = D[D.stage.isin(ALERT)].groupby("bdsp_id").focal_excess.max()
    _foc_ok = _foc_E[(_foc_E > np.nanpercentile(_foc_E.reindex(g[g.lab_clean_normal==1].index).dropna(),97))]
    ids["focal (with excess)"] = [i for i in _foc_ok.index if i in g.index
                                  and g.loc[i].p_focal >= 0.5 and g.loc[i].lab_focal == 1][:2]
    ids["normal"] = g[(g.p_slowing < 0.2) & (g.lab_clean_normal == 1)].index[:1]

    out = ["# Generated description sentences — every clause gated by docs/claims_table.md\n",
           "No severity adjective (row 9, forbidden). No frequency word (6b). No peak SD (10). Band is "
           "emitted only as a low-confidence call (5). The abstain path (11) fires when the gate says focal "
           "but no lateralizing spectral excess exists.\n"]
    for kind, sample in ids.items():
        for bid in sample:
            if bid not in g.index: continue
            res = describe(bid, g.loc[bid], D, ap, lu.age.get(bid, np.nan), e_thr)
            if res is None: continue
            sent, clauses = res
            age = lu.age.get(bid, np.nan)
            out.append(f"\n**[{kind}, age {age:.0f}, p_gen={g.loc[bid].p_generalized:.2f}, "
                       f"p_foc={g.loc[bid].p_focal:.2f}]**\n")
            out.append(f"> {sent}\n")
            out.append("| clause | claims row | status |")
            out.append("|---|---|---|")
            for c, row, st in clauses:
                out.append(f"| {c} | {row} | {st} |")

    out.append("\n## What is structurally impossible to emit\n")
    out.append("- a severity adjective (mild/moderate/marked) — not computed\n"
               "- a frequency word (rare/frequent/continuous) — not computed\n"
               "- a peak-SD statistic — the code reports the median, never the max\n"
               "- focal-vs-generalized from our features — that decision is the gate's alone")
    Path("results/generated_sentences.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
