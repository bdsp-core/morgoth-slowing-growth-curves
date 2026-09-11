"""Build the figure files for journal upload: one vector PDF and one 1000-dpi TIFF per figure.

The committed set (figures/manuscript/, scripts/assemble_manuscript_figures.py) is raster: 300-dpi PNG panels
composited into PNGs, good for review copies and the .docx. It does not meet Elsevier's artwork requirements,
which are, at FINISHED printed size:

  * lettering >= 7 pt for normal text (6 pt is allowed only for sub/superscripts);
  * line art 1000 dpi, combination art 500 dpi, halftones 300 dpi -- or vector (EPS/PDF);
  * width 90 / 140 / 190 mm; EPS, PDF, TIFF or JPEG.

Upsampling a 300-dpi composite to 1000 dpi invents pixels and adds no detail. So this builds from VECTOR panels
(the PDF twins every figure script writes when MORGOTH_VECTOR_DIR is set -- see palette._install_vector_twin),
composites them with the SAME geometry as the assembler (panels scaled to a 7-in column, rows spaced at 0.115 of
the mean row height, bold 17-pt letters just outside each panel's top-left), scales the result to its printed
size on a 190 x 240 mm page, and only then rasterizes. Every text object's size is read back from the finished PDF
at printed scale -- measured, not estimated from the scripts' fontsize= arguments.

Run (after the panel producers have run with MORGOTH_VECTOR_DIR=build/vector):
  PYTHONPATH=src python3 scripts/export_journal_figures.py [--vector-dir build/vector] [--out figures/journal]
                                                           [--dpi 1000] [--outdir ~/Downloads/...]
"""
from __future__ import annotations
import argparse
import importlib.util
import math
import shutil
import subprocess
from pathlib import Path

MM = 72.0 / 25.4
PAGE_W_PT, PAGE_H_PT = 190.0 * MM, 240.0 * MM
COLW_PT = 7.0 * 72.0            # scripts/assemble_manuscript_figures.py COLW
HSPACE = 0.115                  # ... its gridspec hspace
LETTER_PT = 17.0                # ... its panel-letter size, at composite scale
PAD_PT = 0.06 * 72.0            # ... its pad_inches
MIN_PT = 7.0                    # Elsevier: normal lettering at printed size


def _assembler():
    spec = importlib.util.spec_from_file_location("asm", "scripts/assemble_manuscript_figures.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _bold_font():
    """DejaVu Sans Bold -- the figures' own face -- registered for reportlab so the letters embed as TrueType."""
    import matplotlib
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    ttf = Path(matplotlib.__file__).parent / "mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"
    if "DejaVuSans-Bold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(ttf)))
    return "DejaVuSans-Bold"


def compose(panel_pdfs: list[Path], out_pdf: Path) -> dict:
    """Stack vector panels as the assembler does, scale to the printed page, write one PDF. Returns geometry."""
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
    from reportlab.pdfgen import canvas

    pages = [PdfReader(str(p)).pages[0] for p in panel_pdfs]
    sizes = [(float(pg.mediabox.width), float(pg.mediabox.height)) for pg in pages]
    n = len(pages)
    # A single-panel figure is placed at its native geometry, with no column rescale and no pad: the panel
    # already carries its own margins, and scripts such as 63 author at exactly the printed width, so any extra
    # rescale shows up directly as type below 7 pt (it took the EEG figures from 7.00 to 6.88 pt).
    s_panel = [1.0] if n == 1 else [COLW_PT / w for w, _ in sizes]
    colw = sizes[0][0] if n == 1 else COLW_PT
    heights = [h * s for (_, h), s in zip(sizes, s_panel)]
    gap = HSPACE * (sum(heights) / n) if n > 1 else 0.0
    lettered = n > 1
    # room for the letters: they sit outside the panel's top-left corner, right- and bottom-aligned
    pad = PAD_PT if lettered else 0.0
    left = pad + (0.015 * colw + 0.75 * LETTER_PT if lettered else 0.0)
    top = pad + (0.015 * heights[0] + LETTER_PT if lettered else 0.0)
    W = left + colw + pad
    H = top + sum(heights) + gap * (n - 1) + pad
    # The journal fits the figure inside 190 x 240 mm: width-limited unless the figure is tall.
    scale = min(PAGE_W_PT / W, PAGE_H_PT / H)
    Wp, Hp = W * scale, H * scale

    out = PageObject.create_blank_page(width=Wp, height=Hp)
    y_top = H - top                                   # composite coordinates, origin bottom-left
    letters = []
    for i, (pg, s, h) in enumerate(zip(pages, s_panel, heights)):
        y0 = y_top - h
        out.merge_transformed_page(pg, Transformation().scale(s * scale, s * scale).translate(left * scale, y0 * scale))
        if lettered:
            letters.append((chr(65 + i), (left - 0.015 * colw) * scale, (y0 + h + 0.015 * h) * scale))
        y_top = y0 - gap

    if letters:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=(Wp, Hp))
        font = _bold_font(); size = LETTER_PT * scale
        for ch, x, y in letters:
            c.setFont(font, size)
            c.drawRightString(x, y, ch)
        c.save(); buf.seek(0)
        out.merge_page(PdfReader(buf).pages[0])

    w = PdfWriter(); w.add_page(out)
    w.add_metadata({"/Title": out_pdf.stem, "/Creator": "scripts/export_journal_figures.py"})
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pdf, "wb") as f:
        w.write(f)
    return dict(w_mm=Wp / MM, h_mm=Hp / MM, scale=scale, panels=n)


def type_sizes(pdf: Path) -> list[tuple[float, str]]:
    """(printed size in pt, text) for every non-blank text run in the finished PDF."""
    from pypdf import PdfReader
    runs = []

    def visit(text, cm, tm, font_dict, font_size):
        if not text or not text.strip():
            return
        a = tm[0] * cm[0] + tm[1] * cm[2]; b = tm[0] * cm[1] + tm[1] * cm[3]
        c = tm[2] * cm[0] + tm[3] * cm[2]; d = tm[2] * cm[1] + tm[3] * cm[3]
        eff = abs(font_size) * math.sqrt(abs(a * d - b * c))
        if eff > 0:
            runs.append((eff, text.strip()))
    PdfReader(str(pdf)).pages[0].extract_text(visitor_text=visit)
    return runs


def rasterize(pdf: Path, tif: Path, dpi: int) -> tuple[int, int]:
    stem = tif.with_suffix("")
    subprocess.run(["pdftocairo", "-tiff", "-tiffcompression", "lzw", "-r", str(dpi), "-singlefile",
                    str(pdf), str(stem)], check=True)
    from PIL import Image
    with Image.open(tif) as im:
        return im.size


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vector-dir", default="build/vector")
    ap.add_argument("--out", default="figures/journal")
    ap.add_argument("--dpi", type=int, default=1000)
    ap.add_argument("--outdir", default=None, help="also copy the finished set here")
    a = ap.parse_args()

    asm = _assembler()
    vec, out = Path(a.vector_dir), Path(a.out)
    if out.exists():
        shutil.rmtree(out)                      # rebuilt whole, so a renamed figure never leaves an orphan
    out.mkdir(parents=True)

    rows, failures = [], []
    for name, (srcs, ncols, producers) in asm.FIGS.items():
        if ncols != 1:
            failures.append(f"{name}: ncols={ncols} not supported by the vector compositor"); continue
        pdfs = [vec / Path(p).with_suffix(".pdf") for p in srcs]
        missing = [str(p) for p in pdfs if not p.exists()]
        if missing:
            failures.append(f"{name}: no vector panel {missing} -- rerun {producers} with MORGOTH_VECTOR_DIR set")
            continue
        stem = Path(name).stem
        pdf = out / f"{stem}.pdf"
        g = compose(pdfs, pdf)
        runs = type_sizes(pdf)
        small = sorted({(round(sz, 2), t[:40]) for sz, t in runs if sz < MIN_PT - 1e-3})
        tif = out / f"{stem}.tif"
        px = rasterize(pdf, tif, a.dpi)
        rows.append(dict(name=stem, **g, min_pt=min((sz for sz, _ in runs), default=float("nan")),
                         n_small=len(small), small=small[:6], px=px,
                         tif_mb=tif.stat().st_size / 1e6, pdf_mb=pdf.stat().st_size / 1e6))
        flag = "" if not small else f"   {len(small)} text run(s) < {MIN_PT} pt"
        print(f"  {stem:34s} {g['w_mm']:5.1f} x {g['h_mm']:5.1f} mm  min type {rows[-1]['min_pt']:.2f} pt  "
              f"{px[0]}x{px[1]} px{flag}", flush=True)

    md = ["# Journal figure set", "",
          f"Vector PDF + {a.dpi}-dpi LZW TIFF per figure, at printed size on a 190 x 240 mm page. Built by "
          "`scripts/export_journal_figures.py` from vector panels; type sizes are read from the finished PDF.", "",
          "| figure | printed (mm) | smallest type (pt) | runs < 7 pt | TIFF px | TIFF MB | PDF MB |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['name']} | {r['w_mm']:.0f} x {r['h_mm']:.0f} | {r['min_pt']:.2f} | {r['n_small']} | "
                  f"{r['px'][0]} x {r['px'][1]} | {r['tif_mb']:.1f} | {r['pdf_mb']:.1f} |")
    for r in rows:
        if r["small"]:
            md += ["", f"**{r['name']}** below {MIN_PT} pt: " + "; ".join(f"{sz} pt \"{t}\"" for sz, t in r["small"])]
    if failures:
        md += ["", "## Not built", ""] + [f"- {f}" for f in failures]
    (out / "MANIFEST.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[-(len(failures) + 2):]) if failures else f"\nwrote {len(rows)} figures to {out}/")

    if a.outdir and rows:
        dest = Path(a.outdir).expanduser(); dest.mkdir(parents=True, exist_ok=True)
        for f in sorted(out.iterdir()):
            shutil.copy2(f, dest / f.name)
        print(f"copied to {dest}")
    return 1 if failures or any(r["n_small"] for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
