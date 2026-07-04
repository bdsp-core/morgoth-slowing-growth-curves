"""Doable-now evaluations that complete the analysis pipeline before the fleet (Brandon's ② list):
  (A) Cross-site generalization: train detector on S0001, test on S0002 (and vice versa).
  (B) Stage-accentuation: in which sleep stage does pathological slowing accentuate?
  (C) Homologous-asymmetry (delta AND theta) norms vs age (growth curves for the lateralization deviation).
Writes results/extra_evals.md + results/figs/{crosssite.png, stage_accentuation.png, asym_norms.png}.
Run: PYTHONPATH=src python scripts/49_extra_evals.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score

AGE_BINS = list(range(0, 96, 5))
out = ["# Extra evaluations (pre-fleet)\n"]
Path("results/figs").mkdir(parents=True, exist_ok=True)


def pct_curve(ax, age, val, label, color):
    d = pd.DataFrame({"age": pd.to_numeric(age, errors="coerce"), "v": val}).dropna()
    d = d[(d.age >= 0) & (d.age <= 95)]; d["ab"] = pd.cut(d.age, AGE_BINS)
    g = d.groupby("ab", observed=True).v; mid = [iv.mid for iv in g.median().index]
    ax.plot(mid, g.median().values, color=color, lw=2, label=label)
    ax.fill_between(mid, g.quantile(.1).values, g.quantile(.9).values, color=color, alpha=0.12)


def main():
    global out
    # ---- (A) cross-site generalization ----
    az = pd.read_parquet("data/derived/adjusted_z.parquet")
    az["fr"] = az.feature + "@" + az.region
    X = az.pivot_table(index="bdsp_id", columns="fr", values="z")
    meta = pd.read_csv("metadata/cohort_metadata.csv").drop_duplicates("bdsp_id").set_index("bdsp_id")
    df = X.join(meta[["label"]], how="inner").dropna(subset=["label"])
    df["site"] = df.index.str[:5]
    y = (df.label != "normal").astype(int)
    feats = df.drop(columns=["label", "site"]).fillna(0.0)
    res = {}
    for tr, te in [("S0001", "S0002"), ("S0002", "S0001")]:
        mtr, mte = df.site == tr, df.site == te
        if mtr.sum() < 100 or mte.sum() < 100:
            continue
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=1.0))
        clf.fit(feats[mtr.values], y[mtr.values])
        res[f"train {tr} → test {te}"] = roc_auc_score(y[mte.values], clf.predict_proba(feats[mte.values])[:, 1])
    out += ["## (A) Cross-site generalization (abnormal-vs-normal AUROC)\n"]
    for k, v in res.items():
        out.append(f"- {k}: **{v:.3f}**")
    fig, ax = plt.subplots(figsize=(5, 3.6))
    ax.bar(list(res), list(res.values()), color="#4a90e2"); ax.set_ylim(0.5, 1.0)
    for i, v in enumerate(res.values()): ax.text(i, v + 0.01, f"{v:.2f}", ha="center")
    ax.set_ylabel("AUROC (held-out site)"); ax.set_title("Cross-site generalization")
    fig.tight_layout(); fig.savefig("results/figs/crosssite.png", dpi=130); plt.close(fig)

    # ---- (B) stage-accentuation ----
    out.append("\n## (B) Stage-accentuation of pathological slowing\n")
    try:
        acc = pd.read_parquet("data/derived/scores_v2.parquet")   # already has label + accentuated_stage
        ab = acc[(acc.label != "normal") & acc.accentuated_stage.notna() & (acc.accentuated_stage != "W")]
        dist = ab.accentuated_stage.value_counts()
        out.append(f"- among abnormal recordings with a non-wake accentuation stage (n={len(ab)}): "
                   + ", ".join(f"{k} {v}" for k, v in dist.items()))
        fig, ax = plt.subplots(figsize=(5, 3.6))
        dist.plot.bar(ax=ax, color="#2ec4b6"); ax.set_ylabel("recordings"); ax.set_title("Stage that accentuates slowing (abnormal)")
        fig.tight_layout(); fig.savefig("results/figs/stage_accentuation.png", dpi=130); plt.close(fig)
    except Exception as e:
        out.append(f"- (skipped: {type(e).__name__})")

    # ---- (C) homologous-asymmetry (delta & theta) norms vs age ----
    out.append("\n## (C) Homologous temporal asymmetry norms vs age (normal)\n")
    asym = pd.read_parquet("data/derived/recording_asymmetry.parquet")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for b, color in [("delta", "#4a90e2"), ("theta", "#e0568a")]:
        nm = asym[asym.label == "normal"]
        pct_curve(ax, nm.age, nm[f"asym_temporal_{b}"].abs(), f"|temporal {b} asym|", color)
    ax.set_xlabel("age (years)"); ax.set_ylabel("|homologous asymmetry|")
    ax.set_title("Temporal asymmetry norms vs age (normal, delta & theta)"); ax.legend(); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig("results/figs/asym_norms.png", dpi=130); plt.close(fig)
    out.append("- delta & theta homologous-asymmetry magnitude curves saved (norms for the lateralization deviation).")

    Path("results/extra_evals.md").write_text("\n".join(out))
    print("\n".join([l for l in out if l.startswith("-") or l.startswith("##")]))


if __name__ == "__main__":
    main()
