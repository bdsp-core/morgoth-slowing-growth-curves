# The two-stage system, end to end

**Morgoth gates; our normative field describes; and we report where the two disagree.** The features are never used to *detect* — only to describe, and only along the axis the gate opened.

## 1. The gate (25,390 recordings)

Morgoth's two EEG-level heads are **independent** binary sigmoids, so `BOTH` is a real cell, not a tie-break. Operating points by Youden J on `clean_pair` (p_focal ≥ 0.103, p_generalized ≥ 0.241).

| gate call | n | % |
|---|---|---|
| neither | 12,702 | 50.0% |
| focal only | 1,478 | 5.8% |
| generalized only | 2,778 | 10.9% |
| BOTH | 8,432 | 33.2% |

## 2a. Generalized branch — 11,210 recordings

| descriptor | value |
|---|---|
| amount (median whole-head z) | **+0.70** [IQR +0.21, +1.24] |
| prevalence (median) | 0.12 |
| longest continuous run (median) | 0.9 min |
| episodes (median) | 9 |

**How much of the record (ACNS-style):**

| frequency | n | % |
|---|---|---|
| frequent (10-50%) | 3,285 | 29.3% |
| occasional (1-10%) | 2,711 | 24.2% |
| none/rare (<1%) | 2,616 | 23.3% |
| abundant (50-90%) | 1,822 | 16.3% |
| continuous (>90%) | 776 | 6.9% |

**Topography (anterior–posterior gradient):**

| call | n | % |
|---|---|---|
| no clear gradient | 5,732 | 51.1% |
| posteriorly predominant | 4,013 | 35.8% |
| frontally predominant | 1,465 | 13.1% |

## 2b. Focal branch — 9,910 recordings

**Side:**

| side | n | % |
|---|---|---|
| no clear side | 6,343 | 64.0% |
| left | 1,975 | 19.9% |
| right | 1,592 | 16.1% |

**Region (largest deviation relative to its homologue):**

| region | n | % |
|---|---|---|
| L_temporal | 3,213 | 32.4% |
| R_temporal | 2,463 | 24.9% |
| R_parasagittal | 2,144 | 21.6% |
| L_parasagittal | 2,090 | 21.1% |

## 3. The discordance audit

Of the recordings the gate flagged, how many show **no feature evidence** of what it flagged? The bar is set by the **normal population**, not by hand: for each descriptor it is the clean-normals' own **95th centile**, so by definition 5% of normals exceed it (prevalence 0.27, amount z +1.02, asymmetry |z| 2.34). A recording counts as showing *no evidence* only when it is inside the normal range on **every** descriptor of that axis — the conservative choice.

| disagreement | n | % |
|---|---|---|
| gate says GENERALIZED, yet prevalence AND amount both inside the normal range | 6,811 / 11,210 | **60.8%** |
| gate says FOCAL, yet both homologous asymmetries inside the normal range | 6,117 / 9,910 | **61.7%** |
| gate says NEITHER, yet prevalence AND amount both elevated | 394 / 12,702 | **3.1%** (normals: 3.6%) |

### Read the binary rate together with the continuous one

Taken alone, "61% show no evidence" would badly misrepresent the system. The gated groups are **clearly shifted** — they simply do not mostly clear a 95th-centile bar:

| gated group | median position in the clean-normal distribution |
|---|---|
| generalized — amount z | **88th centile** |
| generalized — prevalence | **87th centile** |
| focal — max asymmetry | **88th centile** |

The median gated recording sits near the **88th centile of normals** on every axis. It is elevated; it is just not in the top 5%. A ~60% "no evidence" rate at a 95th-centile bar is exactly what a descriptor with AUROC ≈ 0.72–0.74 against the label should produce — the two statements are the same fact seen twice, not a contradiction.

### What the disagreement means

These are the cases where Morgoth and the normative field genuinely disagree, and both directions are reported rather than only the flattering one. Note the asymmetry between them: the gate very rarely misses what our features see (the converse rate is **at the normals' own base rate**), but our features frequently fail to corroborate what the gate sees. That is the signature of a detector that is strictly stronger than the descriptor, which is what Table 6 already says (gate 0.875–0.911 vs spectral deviation ~0.72). The most likely explanation is that the gate reads **morphology** — waveform shape, rhythmicity, reactivity — that a band-power deviation cannot represent at all. That is especially plausible for focal slowing, which is a *shape* judgement more than a *power* judgement, and it is where the focal branch is weakest (64% of gated-focal recordings have no clear side).

This is the honest limit of the current descriptor set, and it is the right place to look next.
