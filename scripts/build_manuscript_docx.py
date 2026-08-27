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
# Keyed on the table's IDENTIFIER, not on its caption prose. The map used to hold the full legend string,
# so the builder died the first time a caption was reworded -- and the .docx is the copy co-authors read.
TABLES = {
    "Table 1":  Path("results/table1.md"),
    "Table S1": Path("results/vanputten_fullcoverage.md"),
    "Table S2": Path("results/table5_human_ceiling.md"),
    "Table S3": Path("results/story/band_calibration.md"),
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
    """Drop each table's rows in under its caption, found by identifier rather than by exact wording."""
    for tid, src in TABLES.items():
        pat = re.compile(rf"^- \*\*{re.escape(tid)} ---.*$", re.M)
        m = pat.search(body)
        if not m:
            raise SystemExit(f"no caption line for {tid} in the manuscript "
                             f"(expected a bullet starting '- **{tid} --- ')")
        if not src.exists():
            raise SystemExit(f"table source missing: {src} (regenerate via the results reproduce tier)")
        tbl = pipe_tables(src.read_text())
        if not tbl:
            raise SystemExit(f"no pipe table found in {src}")
        j = m.end()
        body = body[:j] + "\n\n" + tbl + "\n" + body[j:]
        print(f"  inlined {src} ({tbl.count(chr(10)) + 1} rows) under {tid}")
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
