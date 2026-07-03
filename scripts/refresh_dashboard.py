"""Live monitoring dashboard for the slowing-ingestion job (pilot or full wave).

Reads the accumulating data/derived/expansion_pilot_features.parquet (written incrementally by the
ingestion) plus the original cohort, and emits:
  - health checks with PASS/WARN flags (are the features sane as data lands?)
  - ingestion progress (n recordings, per-label, stage distribution, usable %)
  - a combined Table 1 (original cohort + newly ingested)  -> docs/table1_live.md
  - a self-contained HTML dashboard (embeds any PNGs in results/figs/) -> results/live_dashboard.html

Safe to run repeatedly while the job runs (read-only on the parquet). Run:
    PYTHONPATH=src python scripts/refresh_dashboard.py
    watch -n 300 'PYTHONPATH=src python scripts/refresh_dashboard.py'   # every 5 min
"""
from __future__ import annotations
import base64, glob
from pathlib import Path
import numpy as np, pandas as pd

PARQUET = Path("data/derived/expansion_pilot_features.parquet")
COHORT = Path("metadata/cohort_metadata.csv")
FIGDIR = Path("results/figs")
OUT_HTML = Path("results/live_dashboard.html")
OUT_MD = Path("docs/table1_live.md")

# physiologic expectations used as sanity gates
EXPECT = {
    "rel_delta_whole_head": (0.20, 0.45),   # cohort median ~0.30; wildly outside => artifact/units bug
    "usable_frac_min": 0.30,                 # <30% usable segments => aggressive rejection or bad signal
}
STAGE_ORDER = ["W", "N1", "N2", "N3", "REM", "Other"]


def _flag(ok):  # noqa
    return "✅ PASS" if ok else "⚠️ WARN"


def health_checks(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Return list of (check, value, PASS/WARN)."""
    out = []
    wh = df[df.region == "whole_head"] if "region" in df.columns else df
    # 1. whole-head rel_delta in physiologic range
    if "rel_delta" in wh.columns and len(wh):
        med = float(wh.rel_delta.median())
        lo, hi = EXPECT["rel_delta_whole_head"]
        out.append(("whole-head rel_delta median", f"{med:.3f} (expect {lo}-{hi})", _flag(lo <= med <= hi)))
    # 2. N3 shows MORE slowing than Wake (physiologic: deep sleep = more delta)
    if {"stage", "rel_delta"} <= set(wh.columns):
        by = wh.groupby("stage").rel_delta.median()
        if {"W", "N3"} <= set(by.index):
            out.append(("N3 rel_delta > W rel_delta (physiologic)",
                        f"N3={by['N3']:.3f} vs W={by['W']:.3f}", _flag(by["N3"] > by["W"])))
    # 3. staging actually produced stages (not all 'Other')
    if "stage" in wh.columns and len(wh):
        other = float((wh.stage == "Other").mean())
        out.append(("staged segments (not 'Other')", f"{100*(1-other):.0f}% staged", _flag(other < 0.5)))
    # 4. no all-NaN feature columns
    featcols = [c for c in df.columns if c not in ("bdsp_id", "age", "sex", "label", "stage", "region")]
    nan_cols = [c for c in featcols if df[c].isna().all()]
    out.append(("no all-NaN feature columns", f"{len(nan_cols)} all-NaN" if nan_cols else "none", _flag(not nan_cols)))
    # 5. labels represented
    if "label" in df.columns:
        n = df.groupby("label").bdsp_id.nunique().to_dict()
        out.append(("label coverage", ", ".join(f"{k}={v}" for k, v in n.items()) or "none",
                    _flag(len(n) >= 2)))
    return out


def combined_table1(newdf: pd.DataFrame | None):
    """Old cohort + newly ingested -> docs/table1_live.md via tableone (best effort)."""
    try:
        from tableone import TableOne
    except Exception:
        return None
    frames = []
    if COHORT.exists():
        c = pd.read_csv(COHORT)[["bdsp_id", "label", "age", "sex"]].copy()
        c["Cohort"] = "Original"
        frames.append(c)
    if newdf is not None and len(newdf):
        n = newdf.drop_duplicates("bdsp_id")[["bdsp_id", "label", "age", "sex"]].copy()
        n["Cohort"] = "Newly ingested"
        frames.append(n)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df["Age (years)"] = pd.to_numeric(df.age, errors="coerce").where(lambda a: (a >= 0) & (a <= 120))
    df["sex"] = (df.sex.astype(str).str[0].str.upper()
                 .map({"M": "M", "F": "F"}))            # Male/male/M -> M, Female/female/F -> F
    lab = {"normal": "Normal", "focal_slow": "Focal slowing", "general_slow": "Generalized slowing"}
    df["Group"] = df.label.map(lab).fillna(df.label)
    t = TableOne(df, columns=["Age (years)", "sex", "Cohort"], categorical=["sex", "Cohort"],
                 groupby="Group", nonnormal=["Age (years)"], pval=False, missing=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("# Table 1 (live) — original cohort + newly ingested\n\n" +
                      t.tabulate(tablefmt="github") + "\n")
    return t.tabulate(tablefmt="github")


def _img_tag(p: Path) -> str:
    b64 = base64.b64encode(p.read_bytes()).decode()
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f'<figure><img src="data:{mime};base64,{b64}"><figcaption>{p.name}</figcaption></figure>'


def write_html(checks, progress, table1_md, stage_tbl):
    figs = sorted(glob.glob(str(FIGDIR / "*.png")))
    rows = "".join(f"<tr><td>{c}</td><td>{v}</td><td>{s}</td></tr>" for c, v, s in checks)
    prog = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in progress.items())
    imgs = "".join(_img_tag(Path(f)) for f in figs) or "<p><em>No figures yet.</em></p>"
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(f"""<!doctype html><meta charset=utf8>
<title>Slowing ingestion — live dashboard</title>
<style>
 body{{font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1a1f2b}}
 h1{{font-size:1.5rem}} h2{{font-size:1.1rem;margin-top:2rem;border-bottom:1px solid #e3e6ee;padding-bottom:.3rem}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0;font-variant-numeric:tabular-nums}}
 td,th{{border:1px solid #e3e6ee;padding:.35rem .6rem;text-align:left}} th{{background:#f5f7fb}}
 figure{{margin:1rem 0}} img{{max-width:100%;border:1px solid #e3e6ee;border-radius:6px}}
 figcaption{{color:#6b7280;font-size:.85rem;margin-top:.25rem}}
 pre{{background:#f5f7fb;padding:1rem;overflow:auto;border-radius:6px;font-size:.8rem}}
</style>
<h1>Slowing ingestion — live dashboard</h1>
<h2>Health checks</h2><table><tr><th>Check</th><th>Value</th><th>Status</th></tr>{rows}</table>
<h2>Ingestion progress</h2><table>{prog}</table>
<h2>rel_delta by sleep stage (whole head)</h2><pre>{stage_tbl}</pre>
<h2>Table 1 (live)</h2><pre>{table1_md or 'tableone unavailable'}</pre>
<h2>Figures</h2>{imgs}
""")


def main():
    if not PARQUET.exists():
        print(f"no {PARQUET} yet — ingestion hasn't written features. (dashboard will populate once it does)")
        df = pd.DataFrame()
    else:
        df = pd.read_parquet(PARQUET)

    checks = health_checks(df) if len(df) else []
    progress = {}
    stage_tbl = "(no data yet)"
    if len(df):
        wh = df[df.region == "whole_head"] if "region" in df.columns else df
        progress = {
            "recordings ingested": df.bdsp_id.nunique(),
            "feature rows": len(df),
            "by label": ", ".join(f"{k}={v}" for k, v in df.groupby("label").bdsp_id.nunique().items()),
        }
        if {"stage", "rel_delta"} <= set(wh.columns):
            by = wh.groupby("stage").rel_delta.median().reindex(
                [s for s in STAGE_ORDER if s in wh.stage.unique()]).round(3)
            dist = wh.stage.value_counts().reindex(by.index).fillna(0).astype(int)
            stage_tbl = pd.DataFrame({"n_segments": dist, "median_rel_delta": by}).to_string()

    table1_md = combined_table1(df if len(df) else None)
    write_html(checks, progress, table1_md, stage_tbl)

    # console summary (what you watch during the run)
    print("=" * 60)
    for c, v, s in checks:
        print(f"  {s}  {c}: {v}")
    for k, v in progress.items():
        print(f"  • {k}: {v}")
    if stage_tbl != "(no data yet)":
        print("\n", stage_tbl, sep="")
    print(f"\nwrote {OUT_HTML}  (open in a browser)  +  {OUT_MD}")


if __name__ == "__main__":
    main()
