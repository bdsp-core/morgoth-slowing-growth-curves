"""Build the co-author review bundle: manuscript, figures and tables as three .docx files.

Round 1 asked "where is Table 1? I don't see it anywhere", so for a while everything was inlined into one
document. Reviewing a draft is easier the other way round -- text you read straight through, figures and
tables you flip to and annotate separately -- and it is also how the journal wants the submission. So:

  docs/manuscript_draft.docx      main text. Every figure and table CAPTION is still here, in the display-item
                                  section, so a reader always knows what each item is and can comment on the
                                  caption without opening anything else. The images and table bodies are not.
  docs/manuscript_figures.docx    the 16 composited submission figures, one per page, each under its full
                                  caption taken verbatim from the manuscript.
  docs/manuscript_tables.docx     the five tables, each under its full caption.

The captions are read out of the manuscript rather than retyped, so the three documents cannot disagree.

Run: python3 scripts/build_manuscript_docx.py [--outdir DIR]
"""
from __future__ import annotations
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

MD = Path("docs/manuscript_draft.md")
FIGDIR = Path("figures/manuscript")
DOCS = Path("docs")
REF = Path("docs/_reference.docx")

# Keyed on the table's IDENTIFIER, not on its caption prose: the map used to hold the full legend string, so
# the build died the first time a caption was reworded -- and these are the copies co-authors read.
TABLES = {
    "Table 1":  Path("results/table1.md"),
    "Table S1": Path("results/vanputten_fullcoverage.md"),
    "Table S2": Path("results/table5_human_ceiling.md"),
    "Table S3": Path("results/story/band_calibration.md"),
    "Table S4": Path("results/story/s4_examples.md"),
}


def pipe_tables(md: str) -> str:
    """Every pipe-table block in a results file, in order, with the surrounding prose dropped."""
    blocks, cur = [], []
    for line in md.splitlines():
        if line.lstrip().startswith("|"):
            cur.append(line.rstrip())
        elif cur:
            blocks.append(cur); cur = []
    if cur:
        blocks.append(cur)
    return "\n\n".join("\n".join(b) for b in blocks)


def table_body(src: Path) -> str:
    """The table itself. Falls back to the file's prose for the one display item that is not a grid."""
    text = src.read_text()
    tbl = pipe_tables(text)
    if tbl:
        return tbl
    # Table S4 is six worked examples, not a grid; keep its body and drop the file's own H1.
    return "\n".join(l for l in text.splitlines() if not l.startswith("# ")).strip()


def captions(body: str) -> dict[str, str]:
    """{'Figure 1': '**Figure 1 --- ...** ...', ...} straight out of the display-item section.

    The WHOLE bullet is kept, not the text after the label: the caption opens with a bolded title that
    closes mid-sentence, so splitting on the label leaves a dangling '**' and the rest of the caption
    renders bold in Word. Verbatim is also the point -- the three documents cannot drift apart.
    """
    out = {}
    for m in re.finditer(r"^- (\*\*((?:Figure|Table) [A-Za-z0-9]+) --- .*)$", body, re.M):
        out[m.group(2)] = m.group(1).rstrip()
    return out


def _order(p: Path):
    m = re.match(r"Figure(S?)(\d+)", p.name)
    return (1 if m and m.group(1) else 0, int(m.group(2)) if m else 99)


def _fig_label(p: Path) -> str:
    m = re.match(r"Figure(S?)(\d+)", p.name)
    return f"Figure {'S' if m.group(1) else ''}{m.group(2)}" if m else p.stem


def render(md_body: str, out: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".md", dir=".", delete=False) as tf:
        tf.write(md_body); tmp = tf.name
    try:
        cmd = ["pandoc", tmp, "-o", str(out), "--resource-path=.", "--from", "markdown+pipe_tables"]
        cmd += ["--reference-doc", str(REF)] if REF.exists() else ["--metadata", "title=manuscript"]
        subprocess.run(cmd, check=True)
    finally:
        Path(tmp).unlink(missing_ok=True)
    print(f"  wrote {out}  ({out.stat().st_size / 1e6:.1f} MB)")


def _repo_date() -> str:
    """The manuscript's last-commit date, so the stamp names the draft rather than the day it was exported."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d", "--", str(MD)],
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    from datetime import date
    return date.today().isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", default=None,
                    help="also copy the three .docx files here, date-stamped (e.g. ~/Downloads)")
    ap.add_argument("--date", default=None,
                    help="stamp to use instead of the manuscript's last-commit date (YYYY-MM-DD)")
    args = ap.parse_args()

    src = MD.read_text().rstrip()
    caps = captions(src)
    figs = sorted(FIGDIR.glob("Figure*.png"), key=_order)
    if not figs:
        raise SystemExit(f"no figures in {FIGDIR} — run scripts/assemble_manuscript_figures.py first")

    missing = [_fig_label(p) for p in figs if _fig_label(p) not in caps]
    missing += [t for t in TABLES if t not in caps]
    if missing:
        raise SystemExit(f"no caption in the manuscript for: {missing}")

    # ---- 1. the manuscript ---------------------------------------------------------------------------
    note = ("\n\n*The figures are in* `manuscript_figures.docx` *and the tables in* `manuscript_tables.docx`*, "
            "each item under the same caption it carries here. They are separate so that the text can be read "
            "straight through and the display items annotated on their own.*\n")
    anchor = "## Figures and Tables\n"
    if anchor not in src:
        raise SystemExit("no '## Figures and Tables' section in the manuscript")
    manuscript = src.replace(anchor, anchor + note, 1)
    print("manuscript:")
    render(manuscript, DOCS / "manuscript_draft.docx")

    # ---- 2. the figures ------------------------------------------------------------------------------
    parts = ["# Figures\n",
             "*Companion to* `manuscript_draft.docx`*. Captions are verbatim from the manuscript.*\n"]
    for i, p in enumerate(figs):
        lbl = _fig_label(p)
        parts.append(f"{caps[lbl]}\n\n![]({p.as_posix()})\n")
        if i < len(figs) - 1:
            parts.append("\\newpage\n")
    print("figures:")
    render("\n".join(parts), DOCS / "manuscript_figures.docx")

    # ---- 3. the tables -------------------------------------------------------------------------------
    parts = ["# Tables\n",
             "*Companion to* `manuscript_draft.docx`*. Captions are verbatim from the manuscript.*\n"]
    for i, (tid, tsrc) in enumerate(TABLES.items()):
        if not tsrc.exists():
            raise SystemExit(f"table source missing: {tsrc} (regenerate via the results reproduce tier)")
        parts.append(f"{caps[tid]}\n\n{table_body(tsrc)}\n")
        if i < len(TABLES) - 1:
            parts.append("\\newpage\n")
    print("tables:")
    render("\n".join(parts), DOCS / "manuscript_tables.docx")

    print(f"\n{len(figs)} figures, {len(TABLES)} tables, captions taken from {MD}")

    if args.outdir:
        import shutil
        # Date-stamped, because co-authors accumulate versions and "manuscript_draft.docx" in a Downloads
        # folder is indistinguishable from the last three.
        stamp = args.date or _repo_date()
        dest = Path(args.outdir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        for src_name, out_name in (("manuscript_draft", "manuscript"),
                                   ("manuscript_figures", "figures"),
                                   ("manuscript_tables", "tables")):
            s = DOCS / f"{src_name}.docx"
            d = dest / f"LENS_{out_name}_{stamp}.docx"
            shutil.copy2(s, d)
            print(f"  {d}  ({d.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
