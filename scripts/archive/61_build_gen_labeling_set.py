"""Build the generalized-slowing phys/path labeling set for the cohort.

Universe: cohort recordings whose report/findings indicate GENERALIZED slowing
(gen-slowing finding flag set, OR report text mentions generalized/diffuse background slowing).
For each we compute rule-cue features (these double as classifier features later) and take a
stratified ~N sample that over-represents the ambiguous middle so the hand-labels cover the
decision boundary.

Outputs:
  data/derived/gen_labeling_set.parquet   selected cases + impression/report text + cue features
  <scratch>/genlabel/batch_XX.json        input batches for the LLM labelers (text + id only)
  results/gen_labeling_set_summary.md      strata + cue prevalence

Run: python scripts/61_build_gen_labeling_set.py [N]
"""
from __future__ import annotations
import sys, re, json, glob
from pathlib import Path
import numpy as np, pandas as pd

REP = "data/reports_raw/MGB_EEGs_And_Reports.csv"
DER = Path("data/derived"); RES = Path("results")
SCRATCH = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
               "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/genlabel")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
SEED = 20260705

# ---- cue lexicons (shared with the classifier) ----------------------------------------------------
PATH_CUE = re.compile(
    r"excess(?:ive)?\s+(?:\w+\s+){0,3}slow|for age|disorganiz|poor(?:ly)? organiz|"
    r"encephalopath|dysfunction|abnormally slow|slow(?:ing|ed)?\s+(?:of\s+)?the\s+background|"
    r"background\s+(?:is\s+)?(?:\w+\s+){0,2}slow|diffuse(?:ly)?\s+slow|marked|severe|moderate", re.I)
PHYS_CUE = re.compile(
    r"drows|asleep|\bsleep\b|somnolen|hyperventilat|\bhv\b|state[- ]depend|"
    r"during (?:light )?(?:drowsi|sleep)|with drowsi|normal (?:awake|eeg)", re.I)
BG_SCOPED = re.compile(r"slow\w*\s+(?:of\s+)?the\s+background|background\s+(?:\w+\s+){0,3}slow", re.I)
STATE_SCOPED = re.compile(r"(?:drows|sleep|asleep|hyperventilat|hv)\w*[^.;]{0,40}slow|"
                          r"slow\w*[^.;]{0,40}(?:drows|sleep|asleep|hyperventilat|hv)", re.I)
EPILEPTIFORM = re.compile(r"\b(seizure|status|gpd|lpd|lrda|grda|spike|sharp wave|periodic discharge|"
                          r"epileptiform|ictal)\b", re.I)
WAKE = re.compile(r"\b(awake|wakefulness|while awake|during wakefulness)\b", re.I)
GEN_SLOW_TEXT = re.compile(r"(gener\w+|diffuse|bilateral|background)[^.;]{0,40}slow|"
                           r"slow[^.;]{0,40}(gener\w+|diffuse|background)", re.I)


def imp_normal(imp):
    t = (imp or "").lower()
    return bool(re.search(r"\bnormal (eeg|study|awake)|within normal limits|this is a normal\b", t)) \
        and not re.search(r"\babnormal\b", t)


def main():
    # ---- reports (cohort join) ----
    rep = pd.read_csv(REP, usecols=lambda c: c in
                      ["SiteID", "BDSPPatientID", "StartTime", "ReportName", "impression", "reports"],
                      low_memory=False, dtype=str)
    rep["pid"] = rep.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    rep["date"] = pd.to_datetime(rep.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    rep["impression"] = rep.impression.fillna(""); rep["reports"] = rep.reports.fillna("")
    rep = rep.dropna(subset=["date"]).drop_duplicates(["pid", "date"])

    # ---- findings gen flag ----
    fnd = pd.concat([pd.read_csv(f, low_memory=False, dtype=str)
                     for f in glob.glob("data/findings/S000*_EEG__reports_findings.csv")], ignore_index=True)
    fnd["pid"] = fnd.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    fnd["date"] = pd.to_datetime(fnd["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    for out, col in [("gen_flag", "gen slowing"), ("abn_flag", "abnormal"), ("nrm_flag", "normal"),
                     ("foc_flag", "foc slowing")]:
        fnd[out] = (~fnd[col].astype(str).str.lower().isin(["nan", ""])).astype(int)
    fnd = fnd.dropna(subset=["date"]).drop_duplicates(["pid", "date"])

    # ---- cohort ----
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["pid"] = meta.bdsp_id.str.replace(r"^S000\d", "", regex=True)
    meta["date"] = meta.eeg_datetime.str[:8]

    df = (meta.merge(rep, on=["pid", "date"], how="inner")
              .merge(fnd[["pid", "date", "gen_flag", "abn_flag", "nrm_flag", "foc_flag"]],
                     on=["pid", "date"], how="left"))
    for c in ["gen_flag", "abn_flag", "nrm_flag", "foc_flag"]:
        df[c] = df[c].fillna(0).astype(int)
    df["full"] = df.impression + " || " + df.reports

    # ---- universe: generalized slowing present (flag or text) ----
    df["gen_text"] = df.full.str.contains(GEN_SLOW_TEXT).fillna(False)
    uni = df[(df.gen_flag == 1) | df.gen_text].copy()
    print(f"cohort recordings matched to report: {len(df)} | generalized-slowing universe: {len(uni)}")

    # ---- cue features ----
    uni["imp_normal"] = uni.impression.map(imp_normal).astype(int)
    uni["path_cues"] = uni.full.str.count(PATH_CUE)
    uni["phys_cues"] = uni.full.str.count(PHYS_CUE)
    uni["bg_scoped"] = uni.full.str.contains(BG_SCOPED).astype(int)
    uni["state_scoped"] = uni.full.str.contains(STATE_SCOPED).astype(int)
    uni["epileptiform"] = uni.full.str.contains(EPILEPTIFORM).astype(int)
    uni["wake"] = uni.full.str.contains(WAKE).astype(int)

    # ---- stratum for balanced sampling (oversample the ambiguous middle) ----
    def stratum(r):
        if r.imp_normal: return "imp_normal"
        pc, hc = r.path_cues > 0, r.phys_cues > 0
        if pc and not hc: return "clear_path"
        if hc and not pc: return "phys_only"
        if pc and hc: return "ambiguous"
        return "bare"
    uni["stratum"] = uni.apply(stratum, axis=1)
    print("universe strata:", uni.stratum.value_counts().to_dict())

    # target allocation: weight the boundary strata (ambiguous, phys_only, imp_normal) up
    weights = {"ambiguous": 0.35, "clear_path": 0.20, "phys_only": 0.20, "imp_normal": 0.15, "bare": 0.10}
    rng = np.random.default_rng(SEED)
    picks = []
    for s, w in weights.items():
        pool = uni[uni.stratum == s]
        k = min(len(pool), int(round(N * w)))
        if k: picks.append(pool.sample(k, random_state=rng.integers(1 << 30)))
    sel = pd.concat(picks).drop_duplicates("bdsp_id").reset_index(drop=True)
    # top up to N from the remainder if rounding left us short
    if len(sel) < N:
        extra = uni[~uni.bdsp_id.isin(sel.bdsp_id)].sample(min(N - len(sel), len(uni) - len(sel)),
                                                            random_state=SEED)
        sel = pd.concat([sel, extra]).reset_index(drop=True)
    print(f"selected {len(sel)} cases; strata: {sel.stratum.value_counts().to_dict()}")

    cue_cols = ["imp_normal", "path_cues", "phys_cues", "bg_scoped", "state_scoped", "epileptiform",
                "wake", "gen_flag", "abn_flag", "nrm_flag", "foc_flag"]
    keep = ["bdsp_id", "eeg_datetime", "site", "age", "label", "impression", "reports", "stratum", *cue_cols]
    sel = sel[[c for c in keep if c in sel.columns]]
    DER.mkdir(parents=True, exist_ok=True)
    sel.to_parquet(DER / "gen_labeling_set.parquet")
    print("wrote", DER / "gen_labeling_set.parquet", sel.shape)

    # ---- batch files for the LLM labelers (text + id; truncate long free text) ----
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for f in SCRATCH.glob("batch_*.json"): f.unlink()
    BATCH = 50
    sel_sh = sel.sample(frac=1.0, random_state=SEED).reset_index(drop=True)  # shuffle so batches are mixed
    n_batches = int(np.ceil(len(sel_sh) / BATCH))
    for b in range(n_batches):
        chunk = sel_sh.iloc[b * BATCH:(b + 1) * BATCH]
        recs = [{"id": r.bdsp_id,
                 "impression": re.sub(r"\s+", " ", r.impression)[:1500],
                 "report": re.sub(r"\s+", " ", r.reports)[:2500]} for r in chunk.itertuples()]
        (SCRATCH / f"batch_{b:02d}.json").write_text(json.dumps(recs, indent=0))
    print(f"wrote {n_batches} batch files to {SCRATCH}")

    # ---- summary ----
    L = ["# Generalized-slowing labeling set\n\n",
         f"- cohort matched to report: **{len(df)}**\n- generalized-slowing universe: **{len(uni)}**\n",
         f"- selected for labeling: **{len(sel)}** ({n_batches} batches of {BATCH})\n\n## Strata (selected)\n"]
    for s, c in sel.stratum.value_counts().items():
        L.append(f"- {s}: {c}\n")
    L.append("\n## Cue prevalence (universe)\n")
    for c in cue_cols:
        L.append(f"- {c}: {int((uni[c] > 0).sum())} ({100*(uni[c] > 0).mean():.0f}%)\n")
    (RES / "gen_labeling_set_summary.md").write_text("".join(L))
    print("".join(L))


if __name__ == "__main__":
    main()
