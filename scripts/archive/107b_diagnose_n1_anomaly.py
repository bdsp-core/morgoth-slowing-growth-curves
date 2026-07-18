"""Diagnose the N1 anomaly: alpha attenuation is REVERSED in abnormal N1.

In the deviation field (scripts/107), the alpha-attenuation descriptor (a_atten = -z_log_alpha) is
NEGATIVE in abnormal N1 (focal -0.34, generalized -0.20) but ~0 in normal N1 (+0.04). That means abnormal
recordings have MORE alpha in their N1 segments than normal recordings do in theirs -- backwards for slowing.

Hypotheses, tested here:
  H1  STAGING: the stager calls "N1" on abnormal recordings for segments that are really drowsy WAKE (alpha
      preserved), whereas normal N1 is genuine N1 (alpha attenuated/fragmented). Abnormal "N1" would then
      carry more alpha. Prediction: the reversal concentrates in LOW-confidence N1, and vanishes when
      restricted to high-p(N1) segments; abnormal N1 should also look wake-like on other features.
  H2  REFERENCE: too few normal N1 recordings across age, so the N1 alpha norm is noisy/biased.
  H3  PHYSIOLOGY: real -- e.g. abnormal patients have a slow, persistent alpha that intrudes into drowsiness.

Reads the abnormal-stage probability cache (data/derived/abn_stage_probs.parquet, scripts/100) for the
confidence test. No PHI; derived tables only.

Run: PYTHONPATH=src python scripts/107b_diagnose_n1_anomaly.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta"]
GRID = np.arange(0, 101, 2.0); BW = 5.0


def kstats(a, v):
    W = np.exp(-0.5 * ((GRID[:, None] - a[None, :]) / BW) ** 2); sw = W.sum(1); ok = sw >= 30
    mu = np.full(len(GRID), np.nan); sd = np.full(len(GRID), np.nan)
    mu[ok] = (W[ok] @ v) / sw[ok]
    sd[ok] = np.sqrt(np.clip((W[ok] @ (v ** 2)) / sw[ok] - mu[ok] ** 2, 1e-9, None))
    return mu, sd


def main():
    seg = pd.read_parquet("data/derived/segment_features.parquet")
    stg = pd.read_parquet("data/derived/segment_stages.parquet")[["bdsp_id", "segment", "stage"]]
    abn = pd.read_parquet("data/derived/segment_stages_abnormal.parquet")[["bdsp_id", "segment", "stage"]]
    stages = pd.concat([stg, abn], ignore_index=True).drop_duplicates(["bdsp_id", "segment"])
    lu = pd.read_parquet("data/derived/labels_unified.parquet")[
        ["bdsp_id", "age", "clean_normal", "has_focal_slow", "gen_class"]].drop_duplicates("bdsp_id")
    ex = set(pd.read_parquet("data/derived/excluded_bdsp_ids.parquet").bdsp_id)
    seg = seg[(seg.region == "whole_head") & ~seg.bdsp_id.isin(ex)].merge(stages, on=["bdsp_id", "segment"])
    seg = seg.merge(lu, on="bdsp_id").dropna(subset=["age"])
    seg["grp"] = np.where(seg.clean_normal == True, "normal",
                          np.where(seg.has_focal_slow == 1, "focal",
                                   np.where(seg.gen_class == "pathologic", "generalized", "other")))

    out = ["# N1 anomaly — why is alpha attenuation reversed in abnormal N1?\n"]

    # ---- confirm, on RAW power, per stage x group (no norming) so we see the physical fact
    out.append("## Raw band power by stage and group (mean log-power; higher alpha = more alpha)\n")
    out.append("| stage | group | n_seg | log_alpha | log_delta | log_theta | log_beta |")
    out.append("|---|---|---|---|---|---|---|")
    for st in ["W", "N1", "N2"]:
        for g in ["normal", "focal", "generalized"]:
            s = seg[(seg.stage == st) & (seg.grp == g)]
            if len(s) < 500: continue
            out.append(f"| {st} | {g} | {len(s):,} | {s.log_alpha.mean():+.3f} | {s.log_delta.mean():+.3f} | "
                       f"{s.log_theta.mean():+.3f} | {s.log_beta.mean():+.3f} |")
    out.append("\nRead the N1 alpha column against W: in NORMALS alpha should fall W→N1 (alpha drops out in "
               "true N1). If abnormal N1 alpha does NOT fall, its 'N1' is drowsy wake.\n")
    for g in ["normal", "focal", "generalized"]:
        w = seg[(seg.stage == "W") & (seg.grp == g)].log_alpha.mean()
        n = seg[(seg.stage == "N1") & (seg.grp == g)].log_alpha.mean()
        out.append(f"- {g}: log_alpha W {w:+.3f} → N1 {n:+.3f}  (drop {w - n:+.3f})")

    # ---- H1: does the reversal live in LOW-confidence N1? use the abnormal stage probabilities
    pr = Path("data/derived/abn_stage_probs.parquet")
    if pr.exists():
        P = pd.read_parquet(pr)               # bdsp_id, segment, p_wake, p_sleep, p_assigned, abn_pred
        abn_n1 = seg[(seg.stage == "N1") & (seg.grp != "normal")].merge(
            P[["bdsp_id", "segment", "p_wake", "p_assigned"]], on=["bdsp_id", "segment"], how="inner")
        out.append("\n## H1 — is abnormal 'N1' really drowsy wake? (stager confidence)\n")
        out.append(f"abnormal N1 segments with probabilities: {len(abn_n1):,}")
        out.append(f"- median p(Wake) on these 'N1' segments: **{abn_n1.p_wake.median():.3f}** "
                   f"(if 'N1' were solid, this is low; high = wake bleed-through)")
        # reference N1 alpha norm from normals
        refn = seg[(seg.stage == "N1") & (seg.grp == "normal")]
        mu, sd = kstats(refn.age.values, refn.log_alpha.values)
        za = (abn_n1.log_alpha.values - np.interp(abn_n1.age.values, GRID, mu)) / np.interp(abn_n1.age.values, GRID, sd)
        abn_n1 = abn_n1.assign(z_alpha=za)
        lowconf = abn_n1.p_wake >= 0.30
        out.append(f"- z_alpha vs normal-N1, all abnormal 'N1': **{np.nanmean(za):+.3f}** "
                   f"(positive = MORE alpha than normal N1 — the anomaly)")
        out.append(f"- z_alpha on LOW-confidence 'N1' (p_wake≥0.30, n={int(lowconf.sum())}): "
                   f"**{np.nanmean(za[lowconf.values]):+.3f}**")
        out.append(f"- z_alpha on HIGH-confidence 'N1' (p_wake<0.10, n={int((abn_n1.p_wake<0.10).sum())}): "
                   f"**{np.nanmean(za[(abn_n1.p_wake<0.10).values]):+.3f}**")
        out.append("\nIf the anomaly vanishes on high-confidence N1, it is a STAGING artifact (H1) and the fix "
                   "is a confidence gate on N1 segments. If it persists, H1 is out.")
    else:
        out.append("\n## H1 — SKIPPED: data/derived/abn_stage_probs.parquet missing (run scripts/100).")

    # ---- H2: normal N1 coverage across age
    out.append("\n## H2 — is the normal-N1 reference well powered?\n")
    cov = seg[(seg.stage == "N1") & (seg.grp == "normal")].copy()
    cov["ageband"] = pd.cut(cov.age, [0, 18, 40, 60, 75, 100])
    out.append(f"normal N1 recordings: {cov.bdsp_id.nunique():,}; segments {len(cov):,}")
    out.append("\n" + cov.groupby("ageband", observed=True).bdsp_id.nunique().to_frame("n_recordings").to_markdown())

    txt = "\n".join(out) + "\n"
    Path("results/n1_anomaly_diagnosis.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
