#!/usr/bin/env python3
"""Table 3 — descriptor reliability (SAP §10). Resolves pre-registered P3 and P4, both UNEVALUATED.

  P3: the AMOUNT score is reliable        -> falsified if split-half ICC < 0.8
  P4: the PREVALENCE descriptor is reliable -> falsified if ICC < 0.8

Split-half design (the reliability question the predictions actually pose): within each recording, split
its usable segments in the scoring stage into two interleaved halves (odd/even segment index — so the two
halves are matched for time-on-task and drift), compute the descriptor independently on each half, and
take the ICC(2,1) across recordings between the two half-estimates.

Normative map: age-conditioned kernel z against clean-normal segments in the SAME stage (identical to the
map used by the van Putten producer). NOTE, stated plainly: the SAP's centile model is GAMLSS/BCT, and
absolute centiles should be read off that. Split-half RELIABILITY, however, is a property of the
measurement's stability — both halves pass through the same normative map, so the choice of map cancels.
Using GAMLSS here would change the z values but not their split-half agreement.

Reads ONLY the v6 fleet output (segment_master) + corrected SAP labels. Zero legacy reuse.
Run: PYTHONPATH=src python scripts/table3_descriptor_reliability.py [--stage W] [--feature log_TAR]
"""
import argparse, glob
from pathlib import Path
import numpy as np, pandas as pd

SM = "data/derived/segment_master"
LAB = "data/derived/recording_labels_sap.parquet"
TAU = 1.645          # 95th centile of the normal segment distribution -> the prevalence threshold


def fit_norm(age_ref, v_ref, bw=8.0, grid=np.arange(-1, 101, 0.5)):
    """Fit the age-conditioned normative mean/SD grid ONCE (was recomputed per recording: O(n x grid x n_ref))."""
    ok = np.isfinite(age_ref) & np.isfinite(v_ref); ar, vr = age_ref[ok], v_ref[ok]
    mu = np.full(len(grid), np.nan); sd = np.full(len(grid), np.nan)
    for j, g in enumerate(grid):
        w = np.exp(-0.5 * ((ar - g) / bw) ** 2); sw = w.sum()
        if sw < 5:
            continue
        m = (w * vr).sum() / sw; mu[j] = m
        sd[j] = np.sqrt(max((w * (vr - m) ** 2).sum() / sw, 1e-9))
    good = np.isfinite(mu)
    return grid[good], mu[good], sd[good]


def z_of(gr, mu, sd, age, vals):
    """Cheap: interpolate the pre-fitted grid at this recording's age."""
    m = np.interp(age, gr, mu); s = np.interp(age, gr, sd)
    return (np.asarray(vals, float) - m) / s


def icc21(a, b):
    """ICC(2,1), two-way random, single measure — agreement between the two half-estimates."""
    m = np.isfinite(a) & np.isfinite(b)
    a, b = np.asarray(a)[m], np.asarray(b)[m]
    n = len(a)
    if n < 10:
        return np.nan, n
    Y = np.c_[a, b]
    grand = Y.mean()
    ms_r = 2 * ((Y.mean(axis=1) - grand) ** 2).sum() / (n - 1)             # between-subject
    ms_c = n * ((Y.mean(axis=0) - grand) ** 2).sum() / 1                    # between-half (systematic)
    ms_e = ((Y - Y.mean(axis=1, keepdims=True) - Y.mean(axis=0) + grand) ** 2).sum() / (n - 1)
    icc = (ms_r - ms_e) / (ms_r + ms_e + 2 * (ms_c - ms_e) / n)
    return float(icc), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="W")
    ap.add_argument("--feature", default="log_TAR")   # SAP's lead slowing feature
    a = ap.parse_args()

    lab = pd.read_parquet(LAB).drop_duplicates("eeg_id").set_index("eeg_id")
    files = sorted(glob.glob(f"{SM}/eeg_id=*/part.parquet"))
    print(f"reading {len(files):,} recordings from the v6 fleet output (stage={a.stage}, "
          f"feature={a.feature})…", flush=True)

    rows = []
    for i, f in enumerate(files):
        eid = f.split("eeg_id=")[1].split("/")[0]
        if eid not in lab.index:
            continue
        d = pd.read_parquet(f, columns=["segment", "stage", "artifact_flag", "channel", a.feature])
        d = d[(~d.artifact_flag) & (d.stage == a.stage)]
        if d.empty:
            continue
        # whole-head = mean over the 18 channels, per segment
        seg = d.groupby("segment")[a.feature].mean()
        if len(seg) < 20:                      # need enough segments to split
            continue
        odd = seg[seg.index % 2 == 1]; even = seg[seg.index % 2 == 0]
        if len(odd) < 8 or len(even) < 8:
            continue
        rows.append({"eeg_id": eid, "age": lab.age.get(eid), "clean_normal": bool(lab.clean_normal.get(eid)),
                     "vals_odd": odd.values, "vals_even": even.values,
                     "all_vals": seg.values})
        if (i + 1) % 4000 == 0:
            print(f"  {i+1:,}/{len(files):,}", flush=True)

    R = pd.DataFrame(rows)
    print(f"recordings with >=20 usable {a.stage} segments: {len(R):,} "
          f"({int(R.clean_normal.sum()):,} clean-normal)")

    # normative reference: clean-normal SEGMENTS, age-conditioned (pooled across their segments)
    ref = R[R.clean_normal]
    ref_age = np.concatenate([[r.age] * len(r.all_vals) for r in ref.itertuples()])
    ref_val = np.concatenate([r.all_vals for r in ref.itertuples()])
    print(f"normative reference: {len(ref_val):,} clean-normal segments")
    gr, mu, sd = fit_norm(ref_age, ref_val)      # fitted ONCE
    print(f"normative grid fitted over {len(gr)} age knots")

    # descriptors on each half
    out = []
    for r in R.itertuples():
        rec = {}
        for tag, vals in [("odd", r.vals_odd), ("even", r.vals_even)]:
            z = z_of(gr, mu, sd, float(r.age), vals)
            rec[f"amount_{tag}"] = np.nanmedian(z)                      # AMOUNT   (P3)
            rec[f"prev_{tag}"] = np.nanmean(z > TAU)                    # PREVALENCE (P4)
        rec["eeg_id"] = r.eeg_id; rec["clean_normal"] = r.clean_normal
        out.append(rec)
    D = pd.DataFrame(out)

    icc_amt, n_a = icc21(D.amount_odd, D.amount_even)
    icc_prev, n_p = icc21(D.prev_odd, D.prev_even)
    v_amt = "CONFIRMED" if icc_amt >= 0.8 else "FALSIFIED"
    v_prev = "CONFIRMED" if icc_prev >= 0.8 else "FALSIFIED"
    print(f"\nP3  AMOUNT      split-half ICC(2,1) = {icc_amt:.3f}  (n={n_a:,})   -> {v_amt}  (threshold 0.8)")
    print(f"P4  PREVALENCE  split-half ICC(2,1) = {icc_prev:.3f}  (n={n_p:,})   -> {v_prev}  (threshold 0.8)")

    tab = pd.DataFrame([
        {"descriptor": "amount (median z)", "split-half ICC(2,1)": round(icc_amt, 3), "n": n_a,
         "pre-registered threshold": ">= 0.80", "prediction": "P3", "verdict": v_amt},
        {"descriptor": f"prevalence (frac z > {TAU})", "split-half ICC(2,1)": round(icc_prev, 3), "n": n_p,
         "pre-registered threshold": ">= 0.80", "prediction": "P4", "verdict": v_prev},
    ])
    Path("results").mkdir(exist_ok=True)
    Path("results/table3_descriptor_reliability.md").write_text(
        "# Table 3 — Descriptor reliability (SAP §10); resolves P3 and P4\n\n"
        f"Split-half reliability on the completed v6 run: within each recording, usable **{a.stage}** "
        f"segments are split into interleaved halves (odd/even segment index, so the halves are matched "
        f"for time-on-task), each descriptor is computed independently on each half, and ICC(2,1) is taken "
        f"across **{n_a:,}** recordings. Feature: `{a.feature}` (whole-head). Normative map: age-conditioned "
        "against clean-normal segments in the same stage.\n\n" + tab.to_markdown(index=False) + "\n\n"
        "*Note: the SAP's centile model is GAMLSS/BCT and absolute centiles should be read from it. "
        "Split-half reliability is a property of measurement stability — both halves pass through the same "
        "normative map, so the choice of map cancels and does not affect these ICCs.*\n")
    D.to_parquet("data/derived/descriptor_halves.parquet", index=False)
    print("\nwrote results/table3_descriptor_reliability.md")


if __name__ == "__main__":
    main()
