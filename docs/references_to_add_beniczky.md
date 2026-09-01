# References suggested by S. Beniczky — to verify before insertion

I did **not** insert these into the manuscript, because I cannot verify author lists, titles, journals, years
or page numbers from a DOI alone, and inventing plausible-looking bibliographic detail is exactly the error
that survives review and embarrasses everyone. Each needs its metadata pulled from the DOI (or from Sandor)
and then inserting at the noted location with `scripts/renumber_display_items.py` to keep citation order.

Two of the seven appear to duplicate references we already carry — flagged below, please confirm before
adding a second entry.

| # | DOI | comment | where it belongs | status |
|---|---|---|---|---|
| 1 | 10.1016/j.jneumeth.2011.06.008 | 10 | §1 lifespan/normative qEEG; likely the 2011 *J Neurosci Methods* revised-BSI paper | **check vs existing ref 9** (van Putten, revised BSI, *Clin Neurophysiol* 2007 — probably a different paper, so likely additive) |
| 2 | 10.1016/j.cnp.2020.11.001 | 10 | §1, SCORE reporting standard | new |
| 3 | 10.1371/journal.pone.0085966 | 10 | §1 lifespan/normative qEEG | new |
| 4 | 10.1016/j.clinph.2012.07.007 | 10 | §1 / §4 qEEG in ischemia | new |
| 5 | 10.1001/jamaneurol.2023.1645 | 39 | human ceiling, §3.3 | **DUPLICATE of existing ref 31** (Tveit et al., SCORE-AI, *JAMA Neurol* 2023) — cite 31, do not add |
| 6 | 10.1111/epi.18082 | 39 | human ceiling, §3.3 | new |
| 7 | 10.1016/s0013-4694(97)00083-7 | 42 | §3.8 / §4 — low specificity of focal slowing in sleep | **new, and load-bearing**: already cited in the Discussion as the reason readers may omit sleep-confined focal slowing deliberately. Currently cited as `\[43\]`, a placeholder that must be renumbered once inserted. |

**Action:** resolve the seven DOIs, add the five-or-six genuinely new ones, then run
`scripts/renumber_display_items.py` and re-run `scripts/certify_reproducibility.py`.
