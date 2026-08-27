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
    # SS3.8 quotes the classified total, which is the sum of the three groups; nothing emitted it, so the
    # reader was left to add three numbers that do not obviously sum to any denominator stated elsewhere.
    Path("results/story").mkdir(parents=True, exist_ok=True)
    Path("results/story/p6_naming_totals.md").write_text(
        "# Figure 7 denominators (where LENS finds the slowing visible)\n\n"
        "One cleanly paired recording per patient. Groups are exclusive and exhaust the classified set.\n\n"
        "| group | n | reports that name slowing |\n|---|---|---|\n"
        + "".join(f"| {l.replace(chr(10), ' ')} | {n:,} | {r:.1f}% |\n"
                 for l, n, r in zip(labels, ns, rates))
        + f"| **classified total** | **{sum(ns):,}** | |\n")
    colors = ["#2c7fb8", ABNORMAL, EXPERTS]                    # wake (blue) / sleep-only (red) / base (grey)

    # 6.4 in wide made this the largest type in the set (ticks ~11 pt against ~7 pt elsewhere) once the
    # journal scaled it to column width. Page-width canvas, so a specified point size IS the printed size.
    fig, ax = plt.subplots(figsize=(7.1, 3.6))
    # Three proportions with n in the thousands and no uncertainty shown at all was the one place in the
    # figure set where a point estimate carried no interval. Wilson score 95% CI -- exact for a proportion,
    # and it does not run off the axis near 0 or 100% the way a normal-approximation interval does.
    def wilson(k, n, z=1.959963985):
        ph = k / n; d = 1 + z * z / n
        c = (ph + z * z / (2 * n)) / d
        h = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / d
        return 100 * (c - h), 100 * (c + h)

    cis = [wilson(round(r / 100 * n), n) for r, n in zip(rates, ns)]
    bars = ax.bar(labels, rates, color=colors, width=0.62, zorder=2)
    ax.errorbar(range(len(rates)), rates,
                yerr=[[r - lo for r, (lo, _) in zip(rates, cis)],
                      [hi - r for r, (_, hi) in zip(rates, cis)]],
                fmt="none", ecolor="#333", elinewidth=1.2, capsize=4, zorder=3)
    for b, r, n, (lo, hi) in zip(bars, rates, ns, cis):
        ax.text(b.get_x() + b.get_width() / 2, hi + 1.4, f"{r:.1f}% [{lo:.0f}\u2013{hi:.0f}]\n(n={n:,})",
                ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.axhline(rates[2], ls="--", lw=1, color="#bbb")          # base-rate reference
    ax.set_ylabel("reports that name slowing (%)", fontsize=9)
    ax.set_ylim(0, max(rates) + 20)
    ax.set_yticks(range(0, 81, 20))
    ax.tick_params(axis="x", length=0)
    # Title in the Figure 7 caption (Clinical Neurophysiology).
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=300, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {OUT}  ({rates[0]:.0f}% wake vs {rates[1]:.0f}% sleep-only, base {rates[2]:.0f}%)")


if __name__ == "__main__":
    main()
