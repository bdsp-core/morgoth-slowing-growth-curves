"""Final report: Morgoth gate decides whether/what; normative features describe (docs/report_architecture).

TIER: gate on Morgoth P(slowing) (gate_probs.parquet). If below threshold -> "no pathological
slowing". Else DESCRIBE using our features:
  - topography/side  : per-region log_delta z (adjusted_z) + temporal asymmetry z -> focal/lateralized/
                        generalized/multifocal + region+side
  - band             : delta vs theta (whole_head z)
  - prevalence/persistence/stage-accentuation/only-in-sleep : scores_v2
Outputs: data/derived/final_report.parquet, results/example_reports_final.md
Run: after scripts/14 (gate_probs) + 06 (adjusted_z) + 11 (scores_v2).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from morgoth_slowing.scoring import topography
from morgoth_slowing.report import phrase as ph

DER = Path("data/derived"); RES = Path("results")
REGION_LABEL = {"L_temporal": "left temporal", "R_temporal": "right temporal",
                "L_parasagittal": "left parasagittal", "R_parasagittal": "right parasagittal"}


def calibrate_threshold(gate):
    """Pick P(slowing) cut maximizing Youden J vs label (normal vs focal/general)."""
    g = gate.dropna(subset=["p_slowing", "label"])
    y = (g.label != "normal").astype(int).values; p = g.p_slowing.values
    best, bt = -1, 0.5
    for t in np.quantile(p, np.linspace(0.05, 0.95, 37)):
        tp = ((p >= t) & (y == 1)).sum(); fn = ((p < t) & (y == 1)).sum()
        tn = ((p < t) & (y == 0)).sum(); fp = ((p >= t) & (y == 0)).sum()
        sens = tp / (tp + fn + 1e-9); spec = tn / (tn + fp + 1e-9)
        if sens + spec - 1 > best:
            best, bt = sens + spec - 1, t
    return float(bt), float(best)


def main():
    gate = pd.read_parquet(DER / "gate_probs.parquet")
    az = pd.read_parquet(DER / "adjusted_z.parquet")
    sc = pd.read_parquet(DER / "scores_v2.parquet")
    asym = pd.read_parquet(DER / "recording_asymmetry.parquet")
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "label", "age", "sex"]].drop_duplicates("bdsp_id")

    thr, J = calibrate_threshold(gate)
    print(f"gate threshold P(slowing) >= {thr:.3f} (Youden J={J:.2f})")

    # per-region log_delta z, and whole_head delta vs theta z
    dz = az[az.feature == "log_delta"].pivot_table(index="bdsp_id", columns="region", values="z")
    tz = az[(az.feature == "log_theta") & (az.region == "whole_head")].groupby("bdsp_id").z.mean()
    # temporal asymmetry z (standardized vs normals)
    a = asym[["bdsp_id", "label", "asym_temporal_delta"]].dropna()
    nm = a[a.label == "normal"].asym_temporal_delta
    a["az"] = (a.asym_temporal_delta - nm.mean()) / (nm.std() + 1e-9)
    asym_z = a.groupby("bdsp_id").az.mean()

    sc = sc.set_index("bdsp_id")
    rows = []
    for _, m in meta.iterrows():
        bid = m.bdsp_id
        p_sl = gate.set_index("bdsp_id").p_slowing.get(bid, np.nan)
        gated_in = np.isfinite(p_sl) and p_sl >= thr
        rec = {"bdsp_id": bid, "label": m.label, "age": m.age, "sex": m.sex,
               "p_slowing": p_sl, "gated_in": bool(gated_in)}
        if not gated_in:
            rec["report"] = "No pathological slowing."
            rows.append(rec); continue
        region_z = {r: dz.loc[bid, r] for r in REGION_LABEL if bid in dz.index and r in dz.columns
                    and np.isfinite(dz.loc[bid, r])}
        az_t = asym_z.get(bid, 0.0)
        # Tier 3: Morgoth heads decide focal vs generalized; our features localize region/side.
        grow = gate.set_index("bdsp_id").loc[bid]
        is_focal = float(grow.get("p_focal", 0)) >= float(grow.get("p_generalized", 0))
        if is_focal and region_z:
            topo = "focal"; loc = REGION_LABEL[max(region_z, key=region_z.get)]
        else:
            topo = "generalized"; loc = "generalized"
        whz = dz.loc[bid, "whole_head"] if bid in dz.index and "whole_head" in dz.columns else np.nan
        thz = tz.get(bid, np.nan)
        srow = sc.loc[bid] if bid in sc.index else None
        prev = float(srow.prevalence) if srow is not None and np.isfinite(srow.prevalence) else 0.0
        run = float(srow.longest_run_min) if srow is not None else float("nan")
        neps = int(srow.n_episodes) if srow is not None and np.isfinite(srow.n_episodes) else 0
        # strongest slowing evidence from our features (regional delta or whole-head theta)
        best_z = max([z for z in region_z.values() if np.isfinite(z)] +
                     [z for z in (whz, thz) if np.isfinite(z)] + [0.0])
        # band: delta / theta / mixed (mixed when both delta and theta are elevated)
        dz_, tz_ = (whz if np.isfinite(whz) else -9), (thz if np.isfinite(thz) else -9)
        if dz_ >= 1.0 and tz_ >= 1.0:
            band = "mixed theta/delta slowing"
        elif tz_ > dz_:
            band = "theta slowing"
        else:
            band = "delta slowing"
        # Morgoth gated it in -> always describe; severity floored to at least "mild"
        sev = ph.severity_word(max(best_z, 2.01))
        prevw = ph.prevalence_word(prev)
        s = f"{prevw.capitalize()} {sev} {loc} {band}"
        parts = []
        if prev > 0:
            parts.append(f"present in {prev*100:.0f}% of segments")
        parts.append(f"peak {best_z:.1f} SD above age/stage-matched norms")
        if np.isfinite(az_t) and abs(az_t) >= 2 and topo == "focal":
            parts.append(f"left–right asymmetry {az_t:.1f} SD")
        if np.isfinite(run) and run > 0:
            parts.append(f"longest run {run:.1f} min over {neps} episodes")
        if srow is not None and getattr(srow, "only_in_sleep", False):
            parts.append("present only during sleep")
        if srow is not None and pd.notna(srow.accentuated_stage) and srow.accentuated_stage != "W":
            parts.append(f"accentuated in {srow.accentuated_stage}")
        s = s + " — " + "; ".join(parts) + "."
        rec["topo_class"] = topo; rec["report"] = s
        rows.append(rec)

    out = pd.DataFrame(rows)
    out.to_parquet(DER / "final_report.parquet")
    print("gated-in rate by label:\n", out.groupby("label").gated_in.mean().round(3).to_string())
    with open(RES / "example_reports_final.md", "w") as fh:
        fh.write("# Final gated reports (Morgoth gate + normative description)\n\n"
                 f"Gate: report slowing only if Morgoth P(slowing) >= {thr:.3f}.\n\n")
        for lab in ["focal_slow", "general_slow", "normal"]:
            ex = out[(out.label == lab) & out.gated_in].head(5)
            fh.write(f"## {lab} (gated-in examples)\n\n")
            for _, r in ex.iterrows():
                fh.write(f"- (age {r.age:.0f} {r.sex}, P_slow={r.p_slowing:.2f}, {r.get('topo_class','')}) {r.report}\n")
            if lab == "normal":
                nn = out[(out.label == "normal") & ~out.gated_in].head(2)
                for _, r in nn.iterrows():
                    fh.write(f"- (age {r.age:.0f} {r.sex}, P_slow={r.p_slowing:.2f}) {r.report}\n")
            fh.write("\n")
    print("wrote results/example_reports_final.md")


if __name__ == "__main__":
    main()
