"""Cache every figure's inputs into data/derived so all figures regenerate WITHOUT the scratchpad.

The scratchpad is ephemeral and holds PHI (raw report text) and third-party Box data (expert votes).
Figures 4, 6 and the severity figure read from it, which means they could not be reproduced from the repo.
This script distils those sources into PHI-free derived tables committed alongside the code:

  data/derived/report_ordinals.parquet       (bdsp_id, date, rep_sev, rep_frq)   <- scripts/86  (Fig. S-sev)
  data/derived/v4a_report_flags.parquet      (bdsp_id, date, 2 booleans)         <- scripts/95  (Fig. 6)
  data/derived/occasion_expert_votes.parquet (fid, rater R##, FS/FN/GS/GN x2)    <- scripts/91/92/94 (Fig. 4)
  data/derived/occasion_files.parquet        (fid, signed-report category)
  data/derived/occasion_morgoth_preds.parquet(fid, axis, M_pred, M_pred_class, majority)
  data/derived/v4a_spindle_results.parquet   (spindle sub-study, per recording)  <- scripts/95b (Fig. 6)

NOTHING here contains raw report text, patient identifiers beyond the existing de-identified `bdsp_id`,
report dates beyond the recording date already in `cohort_metadata.csv`, or rater names (anonymized to R##).

Run: PYTHONPATH=src python scripts/100_cache_figure_inputs.py
"""
from __future__ import annotations
import importlib.util, shutil
from pathlib import Path
import numpy as np, pandas as pd

SC = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
          "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")
DER = Path("data/derived")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def cache_report_ordinals():
    out = DER / "report_ordinals.parquet"
    if out.exists():
        return f"exists ({len(pd.read_parquet(out)):,} rows)"
    m86 = _load("m86", "scripts/86_recalibrate_severity.py")
    r = m86.report_ordinals()                       # derived ordinals only; no text
    r[["bdsp_id", "date", "rep_sev", "rep_frq"]].to_parquet(out)
    return f"wrote {len(r):,} rows"


def cache_v4a_flags():
    out = DER / "v4a_report_flags.parquet"
    if out.exists():
        return f"exists ({len(pd.read_parquet(out)):,} rows)"
    m95 = _load("m95", "scripts/95_v4a_wake_sleep.py")
    f = m95.report_flags()                          # two booleans; no text
    keep = [c for c in ["bdsp_id", "date", "names_slowing", "mentions_sleep_slowing"] if c in f.columns]
    f[keep].to_parquet(out)
    return f"wrote {len(f):,} rows"


def cache_occasion():
    msgs = []
    occ = SC / "moe/occ"
    votes_out = DER / "occasion_expert_votes.parquet"
    if not votes_out.exists():
        xl = pd.ExcelFile(occ / "Occasion.xlsx")
        db = xl.parse("DB")
        uids = sorted(db.uid.unique())
        anon = {u: f"R{i+1:02d}" for i, u in enumerate(uids)}   # never write real uids
        db["rater"] = db.uid.map(anon)
        cols = ["fid", "rater"] + [c for c in db.columns if c.startswith(("r1.", "r2."))]
        db[cols].to_parquet(votes_out)
        xl.parse("Files").to_parquet(DER / "occasion_files.parquet")
        msgs.append(f"votes {len(db):,} rows, {len(uids)} raters -> R01..R{len(uids):02d}")
    else:
        msgs.append("votes exist")
    mp_out = DER / "occasion_morgoth_preds.parquet"
    if not mp_out.exists():
        rows = []
        for f, ax in [("FocalSlowingOutput_Morgoth_experts.xlsx", "FN"),
                      ("GenSlowingOutput_Morgoth_experts.xlsx", "GN")]:
            d = pd.read_excel(occ / "results" / f)
            ex = [c for c in d.columns if c.startswith("expert_")]
            ren = {c: f"R{i+1:02d}" for i, c in enumerate(sorted(ex))}
            d = d.rename(columns=ren); d["axis"] = ax
            rows.append(d[["fid", "axis", "M_pred", "M_pred_class", "majority"] + sorted(ren.values())])
        pd.concat(rows, ignore_index=True).to_parquet(mp_out)
        msgs.append("morgoth preds written")
    else:
        msgs.append("morgoth preds exist")
    return "; ".join(msgs)


def cache_spindle():
    out = DER / "v4a_spindle_results.parquet"
    src = SC / "v4a_spindle_results_v2.parquet"
    if out.exists():
        return f"exists ({len(pd.read_parquet(out)):,} rows)"
    if not src.exists():
        return "SOURCE MISSING — Figure 6's spindle panel cannot be regenerated"
    d = pd.read_parquet(src)
    d.to_parquet(out)
    for extra in ["v4a_edf_sizes.parquet", "v4a_groups.parquet"]:
        if (SC / extra).exists():
            shutil.copy(SC / extra, DER / extra)
    return f"wrote {len(d):,} rows ({(d.status=='ok').sum()} usable)"


def cache_abn_stage_probs():
    """Per-segment stager class probabilities for the ABNORMAL recordings (the confidence check in
    scripts/95). Derived only: bdsp_id, segment, predicted class, p_wake, p_assigned."""
    import glob
    out = DER / "abn_stage_probs.parquet"
    if out.exists():
        return f"exists ({len(pd.read_parquet(out)):,} rows)"
    files = glob.glob(str(SC / "abn_stages" / "*.csv"))
    if not files:
        return "SOURCE MISSING (scratchpad/abn_stages) — the stager-confidence check cannot regenerate"
    seg = pd.read_parquet("data/derived/segment_features.parquet", columns=["bdsp_id", "region", "segment"])
    nseg = seg[seg.region == "whole_head"].groupby("bdsp_id").segment.max().add(1).to_dict()
    rows = []
    for f in files:
        bid = Path(f).name.split("_")[0]
        n = nseg.get(bid)
        if n is None:
            continue
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        pc = [c for c in d.columns if c.startswith("class_") and c.endswith("_prob")]
        if "pred_class" not in d or not pc:
            continue
        P = d[sorted(pc)].to_numpy(); pred = d.pred_class.to_numpy()
        idx = np.arange(int(n))
        wi = ((14.0 * idx + 7.5) / 5.0).astype(int)      # same mapping as scripts/87
        ok = wi < len(pred)
        if not ok.any():
            continue
        w = wi[ok]
        rows.append(pd.DataFrame({"bdsp_id": bid, "segment": idx[ok],
                                  "abn_pred": pred[w].astype(int),
                                  "p_wake": P[w, 0],
                                  "p_sleep": P[w, 2] + P[w, 3],      # p(N2)+p(N3): "confidently not wake"
                                  "p_assigned": P[w, pred[w].astype(int)]}))
    if not rows:
        return "no usable CSVs"
    d = pd.concat(rows, ignore_index=True)
    d.to_parquet(out)
    return f"wrote {len(d):,} segment-probabilities over {d.bdsp_id.nunique():,} abnormal recordings"


def main():
    DER.mkdir(parents=True, exist_ok=True)
    for name, fn in [("report_ordinals (Fig. severity)", cache_report_ordinals),
                     ("v4a_report_flags (Fig. 6)", cache_v4a_flags),
                     ("occasion expert votes + morgoth (Fig. 4)", cache_occasion),
                     ("abn stager probabilities (Fig. 6)", cache_abn_stage_probs),
                     ("v4a spindle results (Fig. 6)", cache_spindle)]:
        try:
            print(f"{name:44s} {fn()}")
        except Exception as e:
            print(f"{name:44s} FAILED: {type(e).__name__}: {e}")
    print("\nPHI check — none of these tables may contain report text or rater names:")
    for p in sorted(DER.glob("occasion_*.parquet")) + sorted(DER.glob("v4a_*.parquet")) + [DER / "report_ordinals.parquet"]:
        if not p.exists(): continue
        d = pd.read_parquet(p)
        obj = [c for c in d.columns if d[c].dtype == object]
        long = [c for c in obj if d[c].astype(str).str.len().max() > 40]
        print(f"  {p.name:38s} {d.shape}  object cols: {obj if obj else 'none'}"
              + (f"  <-- LONG STRINGS in {long}" if long else ""))


if __name__ == "__main__":
    main()
