"""Validation #2: does a simple LR on our deviation-from-normal features agree with Morgoth?

Morgoth's probabilities are well-calibrated to expert reads, so a logistic regression built only on
our age/sex-adjusted deviation z-scores should (a) discriminate about as well and (b) produce
probabilities that track Morgoth's. If yes -> our simple objective features capture what the experts
(via Morgoth) capture.

Metrics: OOF LR AUC vs Morgoth AUC (both vs clinical label); Pearson/Spearman of LR prob vs Morgoth
prob; and distillation R^2 (LR trained to reproduce Morgoth's probability directly).
Outputs: results/lr_vs_morgoth.md, figures/lr_vs_morgoth.png
Run: after 06 (adjusted_z) + 14 (gate_probs).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
from scipy.stats import pearsonr, spearmanr
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

DER = Path("data/derived"); RES = Path("results"); FIG = Path("figures")


def feature_matrix():
    # (a) region×band age/sex-adjusted deviations
    az = pd.read_parquet(DER / "adjusted_z.parquet")
    az["fr"] = az.feature + "@" + az.region
    X = az.pivot_table(index="bdsp_id", columns="fr", values="z", aggfunc="mean")
    # (b) asymmetry: standardize each L/R homologous-pair feature vs normals
    asym = pd.read_parquet(DER / "recording_asymmetry.parquet")
    acols = [c for c in asym.columns if c.startswith("asym_")]
    A = asym.set_index("bdsp_id")[acols + ["label"]]
    nm = A[A.label == "normal"][acols]
    Az = (A[acols] - nm.mean()) / (nm.std() + 1e-9)
    Az.columns = [c + "_z" for c in acols]
    # (c) descriptive stage-aware features (prevalence/burden/persistence/stage)
    sc = pd.read_parquet(DER / "scores_v2.parquet").set_index("bdsp_id")
    D = sc[["prevalence", "burden", "peak_z", "longest_run_min", "n_episodes", "wake_prev", "sleep_prev"]]
    return X.join(Az, how="outer").join(D, how="outer")


def main():
    X = feature_matrix()
    gate = pd.read_parquet(DER / "gate_probs.parquet").set_index("bdsp_id")
    df = X.join(gate[["p_slowing", "p_abnormal", "label"]], how="inner").dropna(subset=["label"])
    feats = df.drop(columns=["p_slowing", "p_abnormal", "label"]).fillna(0.0)
    Xv = feats.values
    y = (df.label != "normal").astype(int).values
    out = ["# LR-on-deviations vs Morgoth\n",
           f"n={len(df)}, {feats.shape[1]} age/sex-adjusted feature@region deviations.\n"]

    for mprob_name in ["p_abnormal", "p_slowing"]:
        mprob = df[mprob_name].values
        lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
        oof = cross_val_predict(lr, Xv, y, cv=5, method="predict_proba")[:, 1]
        auc_lr = roc_auc_score(y, oof); auc_m = roc_auc_score(y, mprob)
        pr = pearsonr(oof, mprob)[0]; sr = spearmanr(oof, mprob)[0]
        # distillation: LR-features -> Morgoth prob directly
        ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        oof_reg = cross_val_predict(ridge, Xv, mprob, cv=5)
        r2 = 1 - np.sum((mprob - oof_reg) ** 2) / np.sum((mprob - mprob.mean()) ** 2)
        out += [f"\n## vs Morgoth **{mprob_name}**",
                f"\n- Discrimination vs clinical label: **our-LR AUC {auc_lr:.3f}** | Morgoth AUC {auc_m:.3f}",
                f"\n- Agreement of probabilities: **Pearson r={pr:.3f}**, Spearman ρ={sr:.3f}",
                f"\n- Distillation (our features → Morgoth prob): **R²={r2:.3f}**\n"]
        if mprob_name == "p_abnormal":
            fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
            ax[0].scatter(mprob, oof, s=4, alpha=0.15, c=y, cmap="coolwarm")
            ax[0].plot([0, 1], [0, 1], "k--", lw=1); ax[0].set_xlabel("Morgoth p_abnormal")
            ax[0].set_ylabel("our LR P(abnormal), OOF"); ax[0].set_title(f"agreement r={pr:.2f}")
            # calibration-style: mean our-prob per Morgoth decile
            dec = pd.qcut(mprob, 10, duplicates="drop")
            g = pd.DataFrame({"m": mprob, "o": oof, "d": dec}).groupby("d", observed=True).mean()
            ax[1].plot(g.m, g.o, "o-"); ax[1].plot([0, 1], [0, 1], "k--", lw=1)
            ax[1].set_xlabel("Morgoth p_abnormal (decile mean)"); ax[1].set_ylabel("our LR prob (mean)")
            ax[1].set_title("binned agreement")
            fig.tight_layout(); fig.savefig(FIG / "lr_vs_morgoth.png", dpi=110); plt.close(fig)
    (RES / "lr_vs_morgoth.md").write_text("".join(out))
    print("".join(out))


if __name__ == "__main__":
    main()
