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


def _order(p: Path):
    m = re.match(r"Figure(S?)(\d+)", p.name)
    return (1 if m and m.group(1) else 0, int(m.group(2)) if m else 99)


def main():
    figs = sorted((p for p in FIGDIR.glob("Figure*.png")), key=_order)
    body = MD.read_text().rstrip() + "\n\n\\newpage\n\n# Figures\n\n"
    for p in figs:
        m = re.match(r"Figure(S?)(\d+)", p.name)
        label = f"Figure {'S' if m.group(1) else ''}{m.group(2)}" if m else p.stem
        body += f"**{label}.**\n\n![]({p.as_posix()})\n\n"
    with tempfile.NamedTemporaryFile("w", suffix=".md", dir=".", delete=False) as tf:
        tf.write(body); tmp = tf.name
    try:
        subprocess.run(["pandoc", tmp, "-o", str(OUT), "--resource-path=.", "--from", "gfm",
                        "--reference-doc" if Path("docs/_reference.docx").exists() else "--metadata",
                        "docs/_reference.docx" if Path("docs/_reference.docx").exists() else "title=manuscript"],
                       check=True)
    finally:
        Path(tmp).unlink(missing_ok=True)
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB) with {len(figs)} figures embedded")


if __name__ == "__main__":
    main()
