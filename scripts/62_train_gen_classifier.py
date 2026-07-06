"""Distill the LLM gen-slowing phys/path labels into a SIMPLE, scalable classifier (no LLM at
inference). Compares two interpretable models and applies the better to the whole generalized-slowing
universe.

Task: binary  pathologic  vs  not-pathologic (normal/physiologic).  'unsure' rows are dropped from
training and reported separately.

Models:
  A. rule-cue logistic regression — the hand-built cue features from scripts/61 (fully interpretable).
  B. TF-IDF (word 1-2 grams) + logistic regression on the impression+report text.
Both are cheap to run on millions of reports. 5-fold stratified CV picks the winner (by macro-F1 / AUROC).

Inputs:
  <scratch>/genlabel/labels_*.json        the LLM labels
  data/derived/gen_labeling_set.parquet   text + cue features for the labeled cases
  data/reports_raw/MGB_EEGs_And_Reports.csv (to score the full universe)

Outputs:
  data/derived/gen_labels_llm.csv         collated LLM gold labels (id, gen_class, confidence, ...)
  data/derived/gen_class_predictions.parquet   predicted gen_class + prob for the whole universe
  results/gen_classifier.md               CV metrics, confusion, top features/weights
  models/gen_classifier.joblib            the fitted pipeline (scalable inference)
Run: python scripts/62_train_gen_classifier.py
"""
from __future__ import annotations
import json, glob, re
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib

DER = Path("data/derived"); RES = Path("results"); MOD = Path("models")
SCRATCH = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
               "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/genlabel")
CUES = ["imp_normal", "path_cues", "phys_cues", "bg_scoped", "state_scoped", "epileptiform",
        "wake", "gen_flag", "abn_flag", "nrm_flag", "foc_flag"]


def collate_labels():
    rows = []
    for f in sorted(SCRATCH.glob("labels_*.json")):
        try:
            for r in json.loads(Path(f).read_text()):
                rows.append(r)
        except Exception as e:
            print("WARN could not parse", f, e)
    lab = pd.DataFrame(rows).drop_duplicates("id")
    lab["gen_class"] = lab.gen_class.str.lower().str.strip()
    lab.to_csv(DER / "gen_labels_llm.csv", index=False)
    print(f"collated {len(lab)} LLM labels from {len(list(SCRATCH.glob('labels_*.json')))} files")
    print("class dist:", lab.gen_class.value_counts().to_dict())
    return lab


def build_text(df):
    return (df.impression.fillna("") + " . " + df.reports.fillna("")).str.lower().map(
        lambda t: re.sub(r"\s+", " ", t)[:4000])


def main():
    MOD.mkdir(exist_ok=True)
    lab = collate_labels()
    feat = pd.read_parquet(DER / "gen_labeling_set.parquet")
    d = feat.merge(lab[["id", "gen_class", "confidence"]], left_on="bdsp_id", right_on="id", how="inner")
    print(f"labeled cases joined to features: {len(d)}")

    # binary target: pathologic vs not
    d = d[d.gen_class.isin(["normal", "physiologic", "pathologic", "unsure"])].copy()
    train = d[d.gen_class != "unsure"].copy()
    train["y"] = (train.gen_class == "pathologic").astype(int)
    print(f"train (excl unsure): {len(train)}  positives (pathologic): {int(train.y.sum())} "
          f"({100*train.y.mean():.0f}%)  | unsure held out: {int((d.gen_class=='unsure').sum())}")

    X_text = build_text(train)
    X_cue = train[CUES].astype(float).values
    y = train.y.values
    cv = StratifiedKFold(5, shuffle=True, random_state=0)

    L = ["# Generalized-slowing phys/path classifier (distilled from LLM labels)\n\n",
         f"- labeled cases: **{len(d)}**  (unsure {int((d.gen_class=='unsure').sum())} held out)\n",
         f"- training: **{len(train)}**, pathologic **{int(train.y.sum())}** "
         f"({100*train.y.mean():.0f}%)\n\n"]

    results = {}
    # --- Model A: rule-cue logreg ---
    A = Pipeline([("sc", StandardScaler()), ("lr", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    pa = cross_val_predict(A, X_cue, y, cv=cv, method="predict")
    pap = cross_val_predict(A, X_cue, y, cv=cv, method="predict_proba")[:, 1]
    results["A_cue"] = (pa, pap)
    # --- Model B: tfidf logreg ---
    B = Pipeline([("tf", TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=20000, sublinear_tf=True)),
                  ("lr", LogisticRegression(max_iter=2000, class_weight="balanced", C=4.0))])
    pb = cross_val_predict(B, X_text, y, cv=cv, method="predict")
    pbp = cross_val_predict(B, X_text, y, cv=cv, method="predict_proba")[:, 1]
    results["B_tfidf"] = (pb, pbp)

    for name, (pred, prob) in results.items():
        auc = roc_auc_score(y, prob)
        rep = classification_report(y, pred, target_names=["not-path", "pathologic"], digits=3)
        cm = confusion_matrix(y, pred)
        f1m = classification_report(y, pred, output_dict=True)["macro avg"]["f1-score"]
        L += [f"## Model {name} — 5-fold CV\n- AUROC **{auc:.3f}**, macro-F1 **{f1m:.3f}**\n",
              f"```\n{rep}\nconfusion (rows=true not/path):\n{cm}\n```\n"]
        results[name] = (pred, prob, auc, f1m)

    winner = max(["A_cue", "B_tfidf"], key=lambda k: results[k][3])  # by macro-F1
    L.append(f"\n**Winner: {winner}** (higher macro-F1).\n")
    print("".join(L[-6:]))

    # fit winner on all training data; interpretability
    if winner == "A_cue":
        A.fit(X_cue, y); model, kind = A, "cue"
        w = A.named_steps["lr"].coef_[0]
        L.append("\n## Rule-cue weights (standardized)\n")
        for c, wi in sorted(zip(CUES, w), key=lambda z: -abs(z[1])):
            L.append(f"- {c}: {wi:+.2f}\n")
    else:
        B.fit(X_text, y); model, kind = B, "text"
        vocab = np.array(B.named_steps["tf"].get_feature_names_out())
        w = B.named_steps["lr"].coef_[0]
        top_p = vocab[np.argsort(w)[-20:]][::-1]; top_n = vocab[np.argsort(w)[:20]]
        L.append("\n## Top n-grams → pathologic\n" + ", ".join(top_p) +
                 "\n\n## Top n-grams → not-pathologic\n" + ", ".join(top_n) + "\n")
    joblib.dump({"model": model, "kind": kind, "cues": CUES}, MOD / "gen_classifier.joblib")

    # ---- apply to the FULL generalized-slowing universe ----
    apply_universe(model, kind)

    (RES / "gen_classifier.md").write_text("".join(L))
    print("wrote results/gen_classifier.md and models/gen_classifier.joblib")


def apply_universe(model, kind):
    """Re-derive the full universe (same logic as scripts/61) and score every recording."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("s61", "scripts/61_build_gen_labeling_set.py")
    s61 = importlib.util.module_from_spec(spec); spec.loader.exec_module(s61)
    rep = pd.read_csv(s61.REP, usecols=lambda c: c in
                      ["SiteID", "BDSPPatientID", "StartTime", "impression", "reports"], low_memory=False, dtype=str)
    rep["pid"] = rep.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    rep["date"] = pd.to_datetime(rep.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    rep["impression"] = rep.impression.fillna(""); rep["reports"] = rep.reports.fillna("")
    rep = rep.dropna(subset=["date"]).drop_duplicates(["pid", "date"])
    fnd = pd.concat([pd.read_csv(f, low_memory=False, dtype=str)
                     for f in glob.glob("data/findings/S000*_EEG__reports_findings.csv")], ignore_index=True)
    fnd["pid"] = fnd.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    fnd["date"] = pd.to_datetime(fnd["StartTime(EEG)"], errors="coerce").dt.strftime("%Y%m%d")
    for out, col in [("gen_flag", "gen slowing"), ("abn_flag", "abnormal"), ("nrm_flag", "normal"), ("foc_flag", "foc slowing")]:
        fnd[out] = (~fnd[col].astype(str).str.lower().isin(["nan", ""])).astype(int)
    fnd = fnd.dropna(subset=["date"]).drop_duplicates(["pid", "date"])
    meta = pd.read_csv("metadata/cohort_metadata.csv", dtype={"eeg_datetime": str})
    meta["pid"] = meta.bdsp_id.str.replace(r"^S000\d", "", regex=True); meta["date"] = meta.eeg_datetime.str[:8]
    df = meta.merge(rep, on=["pid", "date"], how="inner").merge(
        fnd[["pid", "date", "gen_flag", "abn_flag", "nrm_flag", "foc_flag"]], on=["pid", "date"], how="left")
    for c in ["gen_flag", "abn_flag", "nrm_flag", "foc_flag"]:
        df[c] = df[c].fillna(0).astype(int)
    df["full"] = df.impression + " || " + df.reports
    df["gen_text"] = df.full.str.contains(s61.GEN_SLOW_TEXT).fillna(False)
    uni = df[(df.gen_flag == 1) | df.gen_text].copy()
    uni["imp_normal"] = uni.impression.map(s61.imp_normal).astype(int)
    uni["path_cues"] = uni.full.str.count(s61.PATH_CUE); uni["phys_cues"] = uni.full.str.count(s61.PHYS_CUE)
    uni["bg_scoped"] = uni.full.str.contains(s61.BG_SCOPED).astype(int)
    uni["state_scoped"] = uni.full.str.contains(s61.STATE_SCOPED).astype(int)
    uni["epileptiform"] = uni.full.str.contains(s61.EPILEPTIFORM).astype(int)
    uni["wake"] = uni.full.str.contains(s61.WAKE).astype(int)
    if kind == "cue":
        prob = model.predict_proba(uni[CUES].astype(float).values)[:, 1]
    else:
        prob = model.predict_proba(build_text(uni))[:, 1]
    uni["p_pathologic"] = prob
    uni["gen_class_pred"] = np.where(prob >= 0.5, "pathologic", "physiologic")
    out = uni[["bdsp_id", "eeg_datetime", "age", "p_pathologic", "gen_class_pred", *CUES]]
    out.to_parquet(DER / "gen_class_predictions.parquet")
    print(f"scored universe: {len(out)} | predicted pathologic "
          f"{int((out.gen_class_pred=='pathologic').sum())} ({100*(out.gen_class_pred=='pathologic').mean():.0f}%)")


if __name__ == "__main__":
    main()
