"""Convert docs/manuscript_draft.md -> docs/manuscript_draft.docx (for circulating to colleagues), with the
composited submission figures embedded at the end so the review copy is self-contained. Requires pandoc.

Run: python3 scripts/build_manuscript_docx.py
"""
from __future__ import annotations
import re, subprocess, tempfile
from pathlib import Path

MD = Path("docs/manuscript_draft.md")
OUT = Path("docs/manuscript_draft.docx")
FIGDIR = Path("figures/manuscript")

# Tables live in results/ and are cited by legend in the manuscript, but the legend alone is not the table.
# Round-1 review asked "where is Table 1? I don't see it anywhere" — so the table BODY is inlined here,
# directly under its legend, and a missing source is fatal rather than silently omitted.
TABLES = {
    "**Table 1 --- Cohort characteristics**":                  Path("results/table1.md"),
    "**Table S1 --- van Putten qEEG full-family benchmark**":   Path("results/vanputten_fullcoverage.md"),
    "**Table S2 --- Human ceiling**":                           Path("results/table5_human_ceiling.md"),
    "**Table S3 --- Band calibration.**":                       Path("results/story/band_calibration.md"),
}


def pipe_tables(md: str) -> str:
    """Every pipe-table block in a results file, in order, with the surrounding prose dropped.

    A results file is a working note: heading, commentary, then one or more tables. Only the tables belong
    in the manuscript, so blocks of consecutive '|' lines are kept and everything else discarded.
    """
    blocks, cur = [], []
    for line in md.splitlines():
        if line.lstrip().startswith("|"):
            cur.append(line.rstrip())
        elif cur:
            blocks.append(cur); cur = []
    if cur:
        blocks.append(cur)
    return "\n\n".join("\n".join(b) for b in blocks)


def inline_tables(body: str) -> str:
    for legend, src in TABLES.items():
        if legend not in body:
            raise SystemExit(f"table legend not found in manuscript: {legend}")
        if not src.exists():
            raise SystemExit(f"table source missing: {src} (regenerate via the results reproduce tier)")
        tbl = pipe_tables(src.read_text())
        if not tbl:
            raise SystemExit(f"no pipe table found in {src}")
        # insert the table body after the full legend line (legend runs to the end of its paragraph)
        i = body.index(legend)
        j = body.index("\n", i)
        body = body[:j] + "\n\n" + tbl + "\n" + body[j:]
        print(f"  inlined {src} ({tbl.count(chr(10)) + 1} rows) under {legend[:34]}...")
    return body


def _order(p: Path):
    m = re.match(r"Figure(S?)(\d+)", p.name)
    return (1 if m and m.group(1) else 0, int(m.group(2)) if m else 99)


def main():
    figs = sorted((p for p in FIGDIR.glob("Figure*.png")), key=_order)
    body = inline_tables(MD.read_text().rstrip()) + "\n\n\\newpage\n\n# Figures\n\n"
    for p in figs:
        m = re.match(r"Figure(S?)(\d+)", p.name)
        label = f"Figure {'S' if m.group(1) else ''}{m.group(2)}" if m else p.stem
        body += f"**{label}.**\n\n![]({p.as_posix()})\n\n"
    with tempfile.NamedTemporaryFile("w", suffix=".md", dir=".", delete=False) as tf:
        tf.write(body); tmp = tf.name
    try:
        subprocess.run(["pandoc", tmp, "-o", str(OUT), "--resource-path=.", "--from", "markdown+pipe_tables",
                        "--reference-doc" if Path("docs/_reference.docx").exists() else "--metadata",
                        "docs/_reference.docx" if Path("docs/_reference.docx").exists() else "title=manuscript"],
                       check=True)
    finally:
        Path(tmp).unlink(missing_ok=True)
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB) with {len(figs)} figures embedded")


if __name__ == "__main__":
    main()
