"""Figure 6 — Readers under-report slowing that is only visible in sleep.

The P6 within-subject naming test (scripts/95b_v4a_spindle_check.py) writes results/p6_sleep_underreporting.md
with, per recording whose slowing is visible in wake / only in sleep / neither, the fraction of reports that
NAME slowing. This is the manuscript's Figure 6 (a clean 3-bar chart). It replaces the deleted stopgap
`make_missing_figures.py` with a proper, reproducible producer that reads those numbers directly.

Run: MPLBACKEND=Agg python3 scripts/fig6_sleep_naming.py  ->  figures/growth_v2/v4a_wake_sleep.png
"""
from __future__ import annotations
import re
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from morgoth_slowing.viz import palette  # noqa: F401  (shared Tufte publication style)
from morgoth_slowing.viz.palette import NORMAL, ABNORMAL, EXPERTS

MD = Path("results/p6_sleep_underreporting.md")
OUT = Path("figures/growth_v2/v4a_wake_sleep.png")
ROW = re.compile(r"\|\s*(?:slowing visible in \*\*wake\*\*|slowing visible \*\*only in sleep\*\*|"
                 r"visible in neither \(base rate\))\s*\|\s*([\d,]+)\s*\|\s*\*?\*?([\d.]+)%", re.I)


def main():
    rows = ROW.findall(MD.read_text())
    if len(rows) != 3:
        raise SystemExit(f"expected 3 naming-stat rows in {MD}, found {len(rows)}")
    ns = [int(n.replace(",", "")) for n, _ in rows]
    rates = [float(r) for _, r in rows]
    labels = ["visible in\nwake", "visible only\nin sleep", "visible in\nneither (base)"]
    colors = ["#2c7fb8", ABNORMAL, EXPERTS]                    # wake (blue) / sleep-only (red) / base (grey)

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    bars = ax.bar(labels, rates, color=colors, width=0.62)
    for b, r, n in zip(bars, rates, ns):
        ax.text(b.get_x() + b.get_width() / 2, r + 1.2, f"{r:.0f}%\n(n={n:,})",
                ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.axhline(rates[2], ls="--", lw=1, color="#bbb")          # base-rate reference
    ax.set_ylabel("reports that name slowing (%)")
    ax.set_ylim(0, max(rates) + 14)
    ax.set_yticks(range(0, 81, 20))
    ax.tick_params(axis="x", length=0)
    ax.set_title("Slowing is named less often when visible only in sleep", fontsize=12)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150); plt.close(fig)
    print(f"wrote {OUT}  ({rates[0]:.0f}% wake vs {rates[1]:.0f}% sleep-only, base {rates[2]:.0f}%)")


if __name__ == "__main__":
    main()
