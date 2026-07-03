"""Phase v2: stage-aware descriptive scoring -> prevalence, persistence, stage-accentuation.

Each 15-s segment's delta is scored against the NORMAL curve *for its own sleep stage* (so normal
deep-sleep delta is not flagged). Then per recording we summarize the descriptors a report needs:
  - prevalence / intermittency (overall + per stage)  - burden  - persistence (longest run, episodes)
  - stage-accentuation (stage with max burden)         - "only in sleep?" (wake vs sleep prevalence)
Outputs: data/derived/scores_v2.parquet, results/example_reports_v2.md
Run: after scripts/10_stage_curves.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from morgoth_slowing.scoring import burden as burden_mod
from morgoth_slowing.report import phrase as ph

OUT = Path("data/derived"); RES = Path("results"); RES.mkdir(exist_ok=True)
FEAT = "log_delta"; TAU = 2.0
SLEEP = ["N1", "N2", "N3", "REM"]


def stage_ref(curves, sex, stage):
    c = curves[(curves.feature == FEAT) & (curves.region == "whole_head") &
               (curves.sex == sex) & (curves.stage == stage)].dropna(subset=["p50"]).sort_values("age")
    return c


def main():
    seg = pd.read_parquet(OUT / "segment_features.parquet", columns=["bdsp_id", "region", "segment", FEAT])
    seg = seg[seg.region == "whole_head"]
    st = pd.read_parquet(OUT / "segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    seg = seg.merge(st, on=["bdsp_id", "segment"], how="inner")
    meta = pd.read_csv("metadata/cohort_metadata.csv")[["bdsp_id", "age", "sex", "label"]].drop_duplicates("bdsp_id")
    seg = seg.merge(meta, on="bdsp_id", how="left")
    seg = seg[seg.age.between(0, 120) & seg.sex.isin(["M", "F"])]
    curves = pd.read_parquet(OUT / "stage_curves.parquet")

    # stage-appropriate z for every segment
    seg["z"] = np.nan
    for (sex, stage), g in seg.groupby(["sex", "stage"]):
        c = stage_ref(curves, sex, stage)
        if len(c) < 2:
            continue
        p50 = np.interp(g.age, c.age, c.p50)
        sd = np.interp(g.age, c.age, (c.p90 - c.p10) / 2.5631)
        seg.loc[g.index, "z"] = (g[FEAT].values - p50) / np.where(sd > 1e-6, sd, np.nan)
    seg = seg.dropna(subset=["z"])
    seg["abn"] = seg.z > TAU

    rows = []
    for bid, g in seg.groupby("bdsp_id"):
        g = g.sort_values("segment")
        prev = float(g.abn.mean()); bur = float(np.maximum(g.z - TAU, 0).mean())
        pers = burden_mod.persistence(g.abn.values)
        wake = g[g.stage == "W"]; sleep = g[g.stage.isin(SLEEP)]
        wake_prev = float(wake.abn.mean()) if len(wake) else np.nan
        sleep_prev = float(sleep.abn.mean()) if len(sleep) else np.nan
        # stage-accentuation: stage with max burden (>=3 segments)
        sb = g.groupby("stage").apply(lambda x: np.maximum(x.z - TAU, 0).mean() if len(x) >= 3 else np.nan)
        acc = sb.idxmax() if sb.notna().any() and sb.max() > 0 else None
        only_sleep = (np.isfinite(wake_prev) and wake_prev < 0.05 and
                      np.isfinite(sleep_prev) and sleep_prev > 0.15)
        rows.append({"bdsp_id": bid, "label": g.label.iloc[0], "age": g.age.iloc[0], "sex": g.sex.iloc[0],
                     "prevalence": prev, "burden": bur, "peak_z": float(g.z.max()),
                     "longest_run_min": pers["longest_run_min"], "n_episodes": pers["n_episodes"],
                     "wake_prev": wake_prev, "sleep_prev": sleep_prev,
                     "accentuated_stage": acc, "only_in_sleep": bool(only_sleep)})
    sc = pd.DataFrame(rows)
    sc.to_parquet(OUT / "scores_v2.parquet")

    print("recordings scored:", len(sc))
    print("prevalence (median) by label:\n", sc.groupby("label").prevalence.median().round(3).to_string())
    print("only_in_sleep rate by label:\n", sc.groupby("label").only_in_sleep.mean().round(3).to_string())

    # verbal examples with stage-dependence
    def sentence(r):
        sev = ph.severity_word(r.peak_z if np.isfinite(r.peak_z) else 0)
        prevw = ph.prevalence_word(r.prevalence)
        s = f"{prevw.capitalize()} {sev} generalized delta slowing, present in {r.prevalence*100:.0f}% of segments"
        if r.only_in_sleep:
            s += ", present only during sleep"
        if r.accentuated_stage and r.accentuated_stage != 'W':
            s += f", accentuated in {r.accentuated_stage}"
        s += (f"; peak {r.peak_z:.1f} SD above stage-matched norms; longest run "
              f"{r.longest_run_min:.1f} min over {int(r.n_episodes)} episodes.")
        return s
    with open(RES / "example_reports_v2.md", "w") as fh:
        fh.write("# Stage-aware descriptive examples (v2)\n\nEach segment scored vs its own sleep "
                 "stage's normal curve; description adds prevalence, persistence, and stage-accentuation.\n\n")
        for lab in ["focal_slow", "general_slow", "normal"]:
            ex = sc[(sc.label == lab)].sort_values("burden", ascending=False).head(5)
            if not len(ex): continue
            fh.write(f"## {lab}\n\n")
            for _, r in ex.iterrows():
                fh.write(f"- (age {r.age:.0f} {r.sex}) {sentence(r)}\n")
            fh.write("\n")
    print("wrote results/example_reports_v2.md")


if __name__ == "__main__":
    main()
