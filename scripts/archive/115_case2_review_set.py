"""Assemble the GENERALIZED CASE-2 review set for MBW's by-eye adjudication
(docs/description_architecture.md §1b/§1d; results/operating_points.md).

Generalized case-2 = the rare, irreducible corner case where
  (i)   Morgoth's gate fires generalized slowing:      p_generalized >= 0.50
  (ii)  the recording HAS sleep coverage:              any of {N1,N2,N3,REM} staged
  (iii) our band-power deviation measures NOTHING:     max amount_median <= 0
                                                       AND max prevalence < 0.05
This set floors at ~2.5-3.4% of recordings and cannot be pushed < 1% at any gate
threshold (§1d). We restrict to cleanly-paired recordings that the REPORT also calls
generalized-slow (gen_class == 'pathologic'), i.e. the report agrees there IS slowing --
those are the interesting contradictions. Two hypotheses to adjudicate by eye:
  H1  rhythmic morphology (GRDA / FIRDA): intermittent rhythmic delta that experts and
      Morgoth recognise but that does not elevate MEAN band power -> we register nothing.
  H2  age-norm over-correction in the elderly: the age-norm already bakes in slowing, so
      pathological slowing does not clear the (already-elevated) 95th centile.

Output (PHI-free, safe to commit):
  data/derived/case2_review_set.jsonl   opaque case_id + numeric descriptor fields only
  results/case2_review_set.md           what MBW should score for each case + age-skew

Private (scratchpad only, NEVER committed):
  <scratchpad>/case2_crosswalk.jsonl    case_id -> bdsp_id

The EEG clips are exported through the SAME viewer used for V3: point the crosswalk's
bdsp_ids at scripts/98_build_review_set.py (--fetch), which writes PHI-free int16 npz
clips to viewer/data/signals/<case_id>.npz. This script does NOT rebuild that machinery.

Run: KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python3 scripts/115_case2_review_set.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

DER = Path("data/derived")
RESULTS = Path("results")
SCRATCH = Path(
    "/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
    "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
CROSSWALK = SCRATCH / "case2_crosswalk.jsonl"

SEED = 115
N_TARGET = 40
BANDS = ["delta", "theta", "mixed"]      # report gen_band strata (§3 band)
SLEEP = {"N1", "N2", "N3", "REM"}
AGE_CAP = 90                              # HIPAA safe-harbor: ages >= 90 -> "90+"


def age_band(a: float) -> str:
    if pd.isna(a):
        return "unk"
    if a < 50:
        return "young(<50)"
    if a < 70:
        return "mid(50-69)"
    return "old(70+)"


def load() -> pd.DataFrame:
    """One row per recording with gate prob, recording-level descriptor maxes, report label."""
    g = pd.read_parquet(DER / "gate_probs.parquet").set_index("bdsp_id")
    D = pd.read_parquet(DER / "description_descriptors.parquet")
    lu = (pd.read_parquet(DER / "labels_unified.parquet")
          .drop_duplicates("bdsp_id").set_index("bdsp_id"))
    pair = (pd.read_parquet(DER / "report_pairing.parquet")
            .drop_duplicates("bdsp_id").set_index("bdsp_id"))

    # recording-level descriptor summary (max over the recording's staged epochs)
    cov = D.groupby("bdsp_id").agg(
        amount_median=("amount_median", "max"),
        amount_p90=("amount_p90", "max"),
        prevalence=("prevalence", "max"),
        has_sleep=("stage", lambda s: bool(set(s) & SLEEP)))
    cov["has_sleep"] = cov["has_sleep"].fillna(False).astype(bool)

    J = (g[["p_generalized", "p_focal"]]
         .join(cov)
         .join(lu[["age", "gen_class", "gen_band"]])
         .join(pair[["clean_pair"]]))
    return J


def eligible(J: pd.DataFrame) -> pd.DataFrame:
    excl = set(pd.read_parquet(DER / "excluded_bdsp_ids.parquet").bdsp_id)
    gate = J.p_generalized >= 0.50
    absent = (J.amount_median <= 0) & (J.prevalence < 0.05)
    case2 = gate & absent & J.has_sleep.fillna(False)
    J = J.assign(gate=gate, absent=absent, case2=case2)
    J = J[~J.index.isin(excl)]
    return J


def round_robin(pool: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Stratified sample across (age_band x gen_band) cells, spread as evenly as the cell
    counts allow (equalises age-band AND band coverage -- the point is to test H2 across
    the age range and to span bands, NOT to reproduce the pool's proportions)."""
    cells = {k: sub for k, sub in pool.groupby(["age_band", "gen_band"])}
    quota = {k: 0 for k in cells}
    avail = {k: len(sub) for k, sub in cells.items()}
    while sum(quota.values()) < n and any(quota[k] < avail[k] for k in cells):
        for k in sorted(cells):                       # deterministic order
            if sum(quota.values()) >= n:
                break
            if quota[k] < avail[k]:
                quota[k] += 1
    picks = [cells[k].sample(quota[k], random_state=int(rng.integers(1 << 30)))
             for k in cells if quota[k] > 0]
    return pd.concat(picks)


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    J = eligible(load())

    # --- populations for the age-skew comparison ------------------------------------
    report_path = J.gen_class == "pathologic"
    case2_all = J[J.case2 & (J.clean_pair == True) & report_path]          # noqa: E712
    captured = J[J.gate & ~J.absent & J.has_sleep.fillna(False) &
                 (J.clean_pair == True) & report_path]                     # noqa: E712

    # --- eligible sampling frame: case-2 + report band in {delta,theta,mixed} + known age
    pool = case2_all[case2_all.gen_band.isin(BANDS) & case2_all.age.notna()].copy()
    pool["age_band"] = pool.age.map(age_band)

    rng = np.random.default_rng(SEED)
    sel = round_robin(pool, N_TARGET, rng)
    sel = sel.sample(frac=1.0, random_state=SEED).reset_index()            # shuffle, expose bdsp_id
    sel["case_id"] = [f"case_g2_{i:03d}" for i in range(1, len(sel) + 1)]

    # --- write PHI-free review set --------------------------------------------------
    def emit_age(a):
        return AGE_CAP if a >= AGE_CAP else int(round(a))                  # cap ages >= 90

    with open(DER / "case2_review_set.jsonl", "w") as fh:
        for _, r in sel.iterrows():
            fh.write(json.dumps({
                "case_id": r.case_id,
                "age": emit_age(r.age),
                "age_band": r.age_band,
                "amount_median": round(float(r.amount_median), 3),   # max over staged epochs
                "amount_p90": round(float(r.amount_p90), 3),
                "prevalence": round(float(r.prevalence), 3),
                "p_generalized": round(float(r.p_generalized), 3),
                "report_gen_band": r.gen_band,
            }) + "\n")

    # --- private crosswalk (scratchpad only) ----------------------------------------
    with open(CROSSWALK, "w") as fh:
        for _, r in sel.iterrows():
            fh.write(json.dumps({"case_id": r.case_id, "bdsp_id": r.bdsp_id}) + "\n")

    # --- PHI guard on the committed jsonl -------------------------------------------
    import re
    txt = (DER / "case2_review_set.jsonl").read_text()
    for bid in sel.bdsp_id:
        assert bid not in txt, f"LEAK: bdsp_id {bid} in committed jsonl"
    assert "bdsp_id" not in txt, "field 'bdsp_id' leaked into committed jsonl"
    assert not re.search(r"S\d{6,}", txt), "bdsp-style id leaked into committed jsonl"
    assert not re.search(r"\d{5,}", txt), "long digit run (date/id) leaked into committed jsonl"

    write_report(sel, pool, case2_all, captured, J)

    # --- console report -------------------------------------------------------------
    print(f"[case2] eligible case-2 pool (sleep, clean_pair, report-path, band-known): {len(pool)}")
    print(f"[case2] sampled {len(sel)} -> {DER/'case2_review_set.jsonl'} (PHI-free)")
    print(f"[case2] crosswalk -> {CROSSWALK} (PRIVATE)")
    print(f"[case2] age  case-2 pool  median={pool.age.median():.0f}  "
          f"mean={pool.age.mean():.1f}  %>=70={ (pool.age>=70).mean():.0%}")
    print(f"[case2] age  captured     median={captured.age.median():.0f}  "
          f"mean={captured.age.mean():.1f}  %>=70={ (captured.age>=70).mean():.0%}")
    print("[case2] sample age_band x report_gen_band:")
    print(pd.crosstab(sel.age_band, sel.gen_band).to_string())


def write_report(sel, pool, case2_all, captured, J):
    def dist(s):
        q = s.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
        return (f"n={len(s)}, median={s.median():.0f}, mean={s.mean():.1f}, "
                f"IQR {q[0.25]:.0f}-{q[0.75]:.0f}, p10-p90 {q[0.1]:.0f}-{q[0.9]:.0f}, "
                f">=70y {(s>=70).mean():.0%}, <50y {(s<50).mean():.0%}")

    ct = pd.crosstab(sel.age_band, sel.gen_band)
    ct_lines = ["| age_band \\ report_gen_band | " + " | ".join(ct.columns) + " | total |",
                "|---|" + "---|" * (len(ct.columns) + 1)]
    for ab in ct.index:
        ct_lines.append(f"| {ab} | " + " | ".join(str(int(x)) for x in ct.loc[ab]) +
                        f" | {int(ct.loc[ab].sum())} |")
    ct_lines.append("| **total** | " + " | ".join(str(int(x)) for x in ct.sum()) +
                    f" | **{int(ct.values.sum())}** |")

    md = f"""# Generalized case-2 review set -- by-eye adjudication (MBW)

Generated by `scripts/115_case2_review_set.py` (seed {SEED}). PHI-free.

## What this set is

The **generalized case-2** corner case (`docs/description_architecture.md` §1b/§1d,
`results/operating_points.md`): Morgoth's gate fires generalized slowing
(`p_generalized >= 0.50`), the recording **has sleep coverage**, yet our band-power
deviation field measures **nothing** (recording-max `amount_median <= 0` **and**
recording-max `prevalence < 0.05`). This floors at ~2.5-3.4% of recordings and cannot be
pushed below 1% at any gate threshold. Here we keep only cleanly-paired recordings whose
**report also calls generalized slowing** (`gen_class == 'pathologic'`) -- Morgoth AND the
clinician see slowing our measurement does not register. Two hypotheses:

- **H1 -- rhythmic morphology (GRDA / FIRDA):** generalized / frontal intermittent rhythmic
  delta. A morphology experts and Morgoth recognise, but it is *intermittent* and may not
  raise *mean* band power, so our amount/prevalence stay flat.
- **H2 -- norm over-correction in the elderly:** the age-norm already bakes in substantial
  slowing, so pathological slowing does not clear the (already-elevated) 95th centile.

## How to review each case

Score every `case_id` with ONE primary label from this dropdown:

| label | meaning |
|---|---|
| **rhythmic-morphology (GRDA/FIRDA)** | intermittent rhythmic delta / frontal IRDA; explains H1 -- fix is a rhythmicity feature |
| **norm-over-correction-elderly** | continuous slowing is visibly present but plausibly within an elderly age-norm; explains H2 -- fix is an elderly-norm correction |
| **genuine-model-miss** | clear continuous slowing our field should have caught; a real measurement failure |
| **gate-false-positive** | no convincing generalized slowing on the raw EEG; the gate (and report) over-called |

Optional free-text note per case (band seen, state, artifact, sedation, etc.).

The tally of these four across the sample decides the fix: a rhythmicity feature (H1),
an elderly-norm correction (H2), an accepted limitation (genuine-miss / FP mix), or some
combination. The **age skew below is the first quantitative hint**: if H2 were the driver
the case-2 set would skew OLDER than the captured generalized recordings -- it does not.

## Exporting the EEG clips (reuse the V3 viewer -- do NOT rebuild)

The clips go through the **same viewer as V3**. `scripts/98_build_review_set.py` already
exports PHI-free int16 `.npz` clips (18-ch double-banana, ~4 min centred on the most
delta-heavy window, 200 Hz, no EDF header, no dates) to `viewer/data/signals/<case_id>.npz`
and reads its `case_id -> bdsp_id` map from a scratchpad crosswalk. To export these cases,
point that fetch path at the case-2 crosswalk written by this script
(`<scratchpad>/case2_crosswalk.jsonl`, PRIVATE) and run its `--fetch` stage; then open
`viewer/app.py`. Do not duplicate the extraction machinery.

## Fields in `data/derived/case2_review_set.jsonl` (PHI-free)

`case_id`, `age` (integer; ages >= {AGE_CAP} shown as {AGE_CAP} per HIPAA safe-harbor),
`age_band`, `amount_median` / `amount_p90` / `prevalence` (our descriptor, **max over the
recording's staged epochs** -- these are the values that made it a case-2), `p_generalized`
(Morgoth), `report_gen_band` (delta / theta / mixed, from the report). **No `bdsp_id`, no
dates, no raw text.** The `case_id -> bdsp_id` crosswalk lives only in the scratchpad.

## Age distribution -- case-2 vs captured generalized (the H2 pre-test)

Both populations are gate-fired generalized, sleep-covered, report-pathologic, cleanly
paired. The ONLY difference: "captured" is where our field DOES measure slowing; "case-2"
is where it measures nothing.

- **captured generalized (measured):** {dist(captured.age)}
- **case-2 (measured nothing):**       {dist(case2_all.age)}
- **sampled case-2 (n={len(sel)}):**   {dist(sel.age)}

**Reading:** the case-2 set is if anything **younger**, not older, than the captured set
(median {case2_all.age.median():.0f} vs {captured.age.median():.0f}). A strong elderly skew
would have supported H2 up front; its absence points the weight of the explanation toward
**H1 (rhythmic morphology)** and away from a pure elderly-norm artifact. The by-eye scores
are the arbiter.

## Sampled composition (stratified by age band x report band)

{chr(10).join(ct_lines)}

Sample drawn to span the age range (H2) and the report bands; theta is scarce in this pool
({int((pool.gen_band=='theta').sum())} eligible) so it is capped by availability, not design.
"""
    (RESULTS / "case2_review_set.md").write_text(md)


if __name__ == "__main__":
    main()
