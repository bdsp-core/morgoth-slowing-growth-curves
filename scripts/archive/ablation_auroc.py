"""AUROC ablation — attribute the headline detection move (audit finding §1).

The manuscript quotes W-TAR AUROC 0.848 (old legacy data + old labels). The auditor observed 0.638 on the
freshly rebuilt tables. After fixing the label bug (physiologic generalized slowing was being counted as
pathologic) it is 0.784. This script attributes the remaining gap by toggling, ONE AT A TIME, the factors
that changed between the old pipeline and the new one:

  (a) LABELS            contaminated (has_gen_slow => pathologic)  vs  corrected (named-as-abnormality)
  (b) ARTIFACT SEGMENTS kept (old behaviour: flat/suppressed segments slipped through)  vs  dropped (new)
  (c) SOURCE            pooled (cohort+expansion)  vs  cohort-only   [SAP §8.1 warns against pooling]
  (d) theta BAND EDGE   NOT ablatable here — 4-7 -> 4-8 Hz is baked into the PSD features at fleet time;
                        toggling it would require re-running the fleet. Recorded as a known un-ablated term.

Primary cell (as in the manuscript): stage W, whole_head, TAR, positives = pathologic generalized slowing,
negatives = clean_normal. Reads ONLY new-run segment_master + the corrected labels.
Run: PYTHONPATH=src python scripts/ablation_auroc.py
"""
from __future__ import annotations
import glob
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

FEAT, STAGE = "TAR", "W"


def aggregate(keep_artifact: bool) -> pd.DataFrame:
    """Per (recording, stage) whole-head median TAR from segment_master, optionally KEEPING artifact
    segments (which is what the old pipeline effectively did)."""
    rows = []
    for f in sorted(glob.glob("data/derived/segment_master/eeg_id=*/part.parquet")):
        d = pd.read_parquet(f, columns=["segment", "channel", "stage", "artifact_flag", "log_TAR"])
        if not keep_artifact:
            d = d[d.artifact_flag == False]
        if d.empty:
            continue
        d["TAR"] = np.exp(d.log_TAR)                     # whole_head = all 18 channels
        g = d.groupby("stage", observed=True)["TAR"].median()
        eid = f.split("eeg_id=")[1].split("/")[0]
        for st, v in g.items():
            rows.append({"bdsp_id": eid, "stage": st, "TAR": v})
    return pd.DataFrame(rows)


def auroc(d, lab, pos_col, src=None):
    m = d.merge(lab, on="bdsp_id", how="inner")
    m = m[(m.stage == STAGE) & m.clean_pair.eq(True)]
    if src:
        m = m[m.src == src]
    pos = m[m[pos_col] == True]
    neg = m[m.clean_normal == True]
    m2 = pd.concat([pos.assign(y=1), neg.assign(y=0)])
    m2 = m2[np.isfinite(m2[FEAT]) & (m2[FEAT] > 0)]
    if m2.y.nunique() < 2 or len(m2) < 50:
        return np.nan, 0, 0
    return roc_auc_score(m2.y, m2[FEAT]), int((m2.y == 1).sum()), int((m2.y == 0).sum())


def main():
    sap = pd.read_parquet("data/derived/recording_labels_sap.parquet")
    man = pd.read_parquet("data/manifest/report_manifest_v6.parquet")[["eeg_id", "bids_task", "has_gen_slow", "is_abnormal"]]
    man["src"] = np.where(man.bids_task.eq("rEEG"), "cohort", "expansion")

    lab = sap[["eeg_id", "clean_normal", "clean_pair", "slowing_gen_pathologic"]].merge(man, on="eeg_id", how="left")
    lab = lab.rename(columns={"eeg_id": "bdsp_id"})
    # the CONTAMINATED label the auditor saw: has_gen_slow (any mention) => "pathologic"
    lab["gen_contaminated"] = lab.has_gen_slow == True
    lab["gen_corrected"] = lab.slowing_gen_pathologic == True

    print("aggregating segment_master (artifact DROPPED — the new pipeline)…", flush=True)
    d_clean = aggregate(keep_artifact=False)
    print("aggregating segment_master (artifact KEPT — mimics the old pipeline)…", flush=True)
    d_dirty = aggregate(keep_artifact=True)

    rows = []
    for lname, pcol in [("contaminated (has_gen_slow)", "gen_contaminated"),
                        ("CORRECTED (named-as-abnormality)", "gen_corrected")]:
        for aname, dd in [("dropped (new)", d_clean), ("KEPT (old-like)", d_dirty)]:
            for sname, src in [("pooled", None), ("cohort-only", "cohort")]:
                a, npos, nneg = auroc(dd, lab, pcol, src)
                rows.append({"labels": lname, "artifact_segments": aname, "source": sname,
                             "AUROC (W, whole_head, TAR)": round(a, 3) if np.isfinite(a) else None,
                             "n_pos": npos, "n_neg": nneg})
    t = pd.DataFrame(rows)
    out = "results/ablation_auroc.md"
    md = ["# AUROC ablation — attributing the headline detection move (audit §1)", "",
          "Primary cell: stage **W**, whole_head, **TAR**; positives = pathologic generalized slowing, "
          "negatives = clean_normal; `clean_pair` only.", "",
          "Manuscript (old legacy data + old labels): **0.848**.", "",
          t.to_markdown(index=False), "",
          "**Not ablatable here:** the θ band edge (4–7 → 4–8 Hz) is baked into the PSD features at fleet "
          "time; toggling it requires re-running the fleet. It remains an un-attributed term.", ""]
    open(out, "w").write("\n".join(md))
    print("\n" + t.to_string(index=False))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
