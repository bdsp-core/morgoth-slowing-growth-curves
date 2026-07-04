"""Assemble a phone-viewable ANALYSIS dashboard (separate from the ingestion burndown): age-dependent
AUROC + the gate-validation summary + any figures in results/figs/. Self-contained HTML (PNGs embedded
as data URIs) -> results/analysis_dashboard.html, published as an Artifact.

Run: PYTHONPATH=src python scripts/build_analysis_dashboard.py
"""
from __future__ import annotations
import base64
from pathlib import Path
import pandas as pd

OUT = Path("results/analysis_dashboard.html")
FIG_ORDER = ["age_auroc.png", "growth_curves_v2.pdf"]  # preferred order; others appended


def img(p: Path) -> str:
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b64}" alt="{p.name}"><figcaption>{p.name}</figcaption></figure>'


def table_html(csv: Path, caption: str) -> str:
    if not csv.exists():
        return ""
    d = pd.read_csv(csv)
    return f"<h2>{caption}</h2>\n" + d.to_html(index=False, border=0, classes="tbl", na_rep="—")


def main():
    figs_dir = Path("results/figs")
    pngs = []
    for name in FIG_ORDER:
        p = figs_dir / name
        if p.exists() and p.suffix == ".png":
            pngs.append(p)
    for p in sorted(figs_dir.glob("*.png")):
        if p not in pngs:
            pngs.append(p)
    figs_html = "".join(img(p) for p in pngs) or "<p class='dim'>No figures yet.</p>"

    gate_md = Path("results/expansion_gate_validation.md")
    gate_html = ""
    if gate_md.exists():
        gate_html = "<h2>Gate validation (new recordings)</h2><pre>" + gate_md.read_text() + "</pre>"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"""<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Morgoth slowing — analysis</title>
<style>
 :root{{--bg:#0e1420;--panel:#161f2f;--line:#233047;--ink:#e8eef7;--dim:#8798b3;--accent:#35e0c4}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
   font:15px/1.6 ui-sans-serif,-apple-system,system-ui,sans-serif}}
 .wrap{{max-width:820px;margin:0 auto;padding:22px 16px 60px}}
 h1{{font-size:1.2rem;margin:0 0 4px}} .sub{{color:var(--dim);font-size:.85rem;margin-bottom:20px}}
 h2{{font-size:.9rem;text-transform:uppercase;letter-spacing:.05em;color:var(--accent);
   margin:26px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}}
 figure{{margin:0 0 18px}} img{{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}}
 figcaption{{color:var(--dim);font-size:.78rem;margin-top:6px}}
 .tbl{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.82rem}}
 .tbl td,.tbl th{{border:1px solid var(--line);padding:.3rem .5rem;text-align:right}}
 .tbl th{{background:var(--panel);color:var(--dim);text-transform:uppercase;font-size:.7rem}}
 .tbl td:first-child,.tbl td:nth-child(2){{text-align:left}}
 pre{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;
   overflow:auto;font-size:.78rem;white-space:pre-wrap}}
 .dim{{color:var(--dim)}}
 .note{{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
   border-radius:8px;padding:12px 14px;font-size:.9rem;margin:14px 0}}
</style>
<div class="wrap">
  <h1>Morgoth slowing — analysis</h1>
  <div class="sub">Gate discrimination + validation. Original 12,379-recording cohort (+ newly-ingested
    as they accumulate). Companion to the ingestion burndown.</div>

  <h2>Age-dependent AUROC</h2>
  <div class="note">Gate discrimination vs. report labels, by age band (each contrast vs. normal, 95%
    bootstrap CI). <b>Abnormal detection is weaker in children (~0.79 at 0–12) and strongest in older
    adults (~0.95 at 61–75)</b>, dipping slightly in the very elderly. Focal detection is strong at all
    ages (0.97–0.99); generalized climbs 0.88→0.96. Useful caveat for pediatric reporting.</div>
  {figs_html}
  {table_html(Path("results/age_auroc.csv"), "Age-band AUROC (table)")}
  {gate_html}
</div>
""")
    print(f"wrote {OUT} ({len(pngs)} figures)")


if __name__ == "__main__":
    main()
