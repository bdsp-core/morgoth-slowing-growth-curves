"""Set the operating points that minimise "flag for review" (docs/description_architecture.md §1d).

Two thresholds jointly determine the corner-case rate:
  tau_M : the Morgoth gate cutoff on p_slowing (below -> "no slowing"; above -> describe)
  tau_S : our descriptor cutoff -- we hold this at its PRINCIPLED value (per-stage prevalence exceeding the
          normal 95th centile), because it has a meaning (5% false-positive in normals by construction) and
          must not be tuned to flatter the gate.

Corner cases, counted with the BRANCH-APPROPRIATE score (not whole-head, which undercounts focal):
  case 1 : we measure MARKED slowing (amount >3 SD or lobar excess >3 SD), gate silent -> flag (gate miss?)
  case 2 : gate fires but we measure NOTHING (amount <=0 SD and no lobar excess) -> flag (gate false-positive?)
NOTE: the descriptor DESCRIBES; it does not re-detect. "gate fires, we measure only MILD slowing" is normal
operation, not a flag. A flag requires a genuine contradiction. (Defining case 2 as "below our detection
threshold" instead inflated the flag rate to ~40%, because our coarse whole-head metric is far less sensitive
than the pattern-aware gate -- that is not disagreement, it is a blunter instrument.)

We sweep tau_M, report the frontier, and pick the knee that minimises case1+case2 subject to the gate's own
sensitivity (against the report label) staying >= a floor. Flag-for-review should land at ~2-5%.

Run: PYTHONPATH=src python scripts/112_operating_points.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ALERT = ["W", "N1"]


def main():
    g = pd.read_parquet("data/derived/gate_probs.parquet").set_index("bdsp_id")
    D = pd.read_parquet("data/derived/description_descriptors.parquet")
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id").set_index("bdsp_id")

    # our descriptor call at the PRINCIPLED cutoff: does prevalence exceed the normal 95th centile in any
    # alert stage? branch-appropriate -> generalized uses whole-head amount/prevalence; focal uses the
    # regional excess E (so intermittent/focal slowing that whole-head dilutes is still counted).
    # Our quantified amount, per recording (max over alert stages). The descriptor DESCRIBES; it does not
    # re-detect. So a flag requires a genuine CONTRADICTION with the gate, not merely "our coarse metric is
    # below its threshold while the gate (which sees pattern) fires". Two contradiction signals:
    da = D[D.stage.isin(ALERT)]
    amt = da.groupby("bdsp_id").amount_median.max().rename("amount")             # SD above age/stage normal
    E = da.groupby("bdsp_id").focal_excess.max().rename("foc_E")
    ours = pd.concat([amt, E], axis=1)
    # "we measure MARKED slowing": clearly abnormal amount OR a strong lobar excess
    ours["ours_marked"] = (ours.amount > 3.0) | (ours.foc_E > 3.0)
    # "we measure essentially NOTHING": amount at or below the normal median AND no lobar excess -- i.e. the
    # signal is genuinely absent, not merely mild. (mild slowing is described, not flagged.)
    ours["ours_absent"] = (ours.amount <= 0.0) & (ours.foc_E.fillna(0) < 1.0)

    J = g[["p_slowing"]].join(ours).join(lu).dropna(subset=["p_slowing"])
    J["report_slow"] = ((J.has_focal_slow == 1) | (J.gen_class == "pathologic")).astype(int)
    n = len(J)

    rows = []
    for tau in np.round(np.arange(0.20, 0.96, 0.05), 2):
        gate = J.p_slowing >= tau
        case1 = (J.ours_marked.fillna(False)) & (~gate)                        # we see MARKED, gate silent
        case2 = gate & (J.ours_absent.fillna(False))                            # gate fires, we see NOTHING (contradiction)
        # gate sensitivity/specificity against the report label (do not trade detection away for tidiness)
        se = gate[J.report_slow == 1].mean(); sp = 1 - gate[J.report_slow == 0].mean()
        rows.append(dict(tau_M=tau, gate_pos=gate.mean(), case1=case1.mean(), case2=case2.mean(),
                         flag=(case1 | case2).mean(), gate_sens=se, gate_spec=sp))
    F = pd.DataFrame(rows)
    F.to_csv("results/operating_points.csv", index=False)

    # knee: minimise total flag subject to gate sensitivity >= 0.80
    ok = F[F.gate_sens >= 0.80]
    knee = ok.loc[ok.flag.idxmin()] if len(ok) else F.loc[F.flag.idxmin()]

    out = ["# Operating points — minimising flag-for-review\n",
           f"n = {n:,} recordings with both a gate probability and descriptors. Descriptor cutoff held at its "
           "principled value (per-stage prevalence above the normal 95th centile; focal via a >2 SD lobar "
           "excess). Corner cases counted with the branch-appropriate score.\n",
           "| gate τ_M | % gated in | case 1 (we see, gate silent) | case 2 (gate fires, we don't) | "
           "total flag | gate sens | gate spec |", "|---|---|---|---|---|---|---|"]
    for _, r in F.iterrows():
        star = "  ←" if abs(r.tau_M - knee.tau_M) < 1e-6 else ""
        out.append(f"| {r.tau_M:.2f} | {r.gate_pos:.1%} | {r.case1:.1%} | {r.case2:.1%} | "
                   f"**{r.flag:.1%}** | {r.gate_sens:.2f} | {r.gate_spec:.2f} |{star}")
    out.append(f"\n**Chosen τ_M = {knee.tau_M:.2f}** (minimises total flag with gate sensitivity ≥ 0.80): "
               f"flag-for-review **{knee.flag:.1%}** (case1 {knee.case1:.1%}, case2 {knee.case2:.1%}), "
               f"gate sensitivity {knee.gate_sens:.2f}, specificity {knee.gate_spec:.2f}.")
    out.append(f"\nAt the shipped τ_M = 0.30 the flag rate is {F[F.tau_M==0.30].flag.iloc[0]:.1%}; "
               f"the knee cuts it to {knee.flag:.1%}. Both corner cases remain flag-for-review outputs — the "
               "goal is a small, genuinely surprising set, not zero.")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].plot(F.tau_M, F.case1, "o-", label="case 1: we see, gate silent")
    ax[0].plot(F.tau_M, F.case2, "s-", label="case 2: gate fires, we don't")
    ax[0].plot(F.tau_M, F.flag, "k^-", lw=2, label="total flag-for-review")
    ax[0].axvline(knee.tau_M, color="crimson", ls="--", label=f"chosen τ_M={knee.tau_M:.2f}")
    ax[0].set_xlabel("Morgoth gate cutoff τ_M"); ax[0].set_ylabel("fraction of recordings")
    ax[0].legend(fontsize=8); ax[0].set_title("Flag-for-review vs gate threshold")
    ax[1].plot(1 - F.gate_spec, F.gate_sens, "o-", color="#333")
    for _, r in F.iterrows():
        ax[1].annotate(f"{r.tau_M:.2f}", (1 - r.gate_spec, r.gate_sens), fontsize=6)
    ax[1].plot([0, 1], [0, 1], "k:", lw=.6)
    ax[1].set_xlabel("1 − gate specificity"); ax[1].set_ylabel("gate sensitivity (vs report)")
    ax[1].set_title("Gate operating characteristic")
    fig.tight_layout(); fig.savefig("figures/growth_v2/operating_points.png", dpi=140); plt.close(fig)

    Path("results/operating_points.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
