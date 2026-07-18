# Getting the manuscript ready for *Clinical Neurophysiology* (CN)

*Target: CN Original Article (IFCN journal, Elsevier). Requirements below are from the CN/Elsevier guide for
authors (verified points cited; a few numeric limits I could not re-confirm on the journal site — ScienceDirect
blocks automated fetch — are flagged **[verify]**). Prepared 2026-07-18.*

## 1. CN requirements — where we stand

| Requirement | CN rule | Us now | Action |
|---|---|---|---|
| **Title** | ≤ **135 characters** incl. spaces; only common abbrevs (EEG/EMG/MEG/MRI/tDCS/TMS) | ~200 chars | **Shorten** (draft below) |
| **Structured abstract** | Required; IFCN uses **Objective / Methods / Results / Conclusions / Significance** | Have all five ✓ | Keep structure |
| **Abstract length** | ≤ **200 words** | ~260 | **Trim to ≤200** |
| **Highlights** | **3–5 bullets, ≤85 chars each** [verify char cap] | **Missing** | **Add** (draft below) |
| **Keywords** | 4–6 [verify] | **Missing** | **Add** (draft below) |
| **Section structure** | Intro / Methods / Results / Discussion (+ Conclusions) | ✓ | Keep |
| **Main-text length** | conciseness expected; no hard cap confirmed [verify] | long | Tighten Results prose |
| **Figures + tables** | economy expected; excess → supplementary (no numeric cap confirmed) [verify] | too many (see §2) | **Triage main↔supp (§2)** |
| **References** | **Vancouver numbered**, in citation order | inline author–year, **no reference list** | **Convert + build numbered list** |
| **Author block** | authors, affiliations, corresponding author, ORCIDs | **Missing** | Add before submission |
| **Declarations** | Conflict of interest; Funding; **Ethical approval/IRB + consent**; Data availability; **CRediT** author contributions; Acknowledgements | Only a data/code-availability paragraph | **Add all** |
| **Abbreviations** | non-common ones defined at first use (abstract + text) | partial | Sweep + define |
| **Figure files** | high-resolution (≥300 dpi halftone; vector for line art) [verify exact] | 140–150 dpi PNG | Re-export ≥300 dpi / vector |

Verified from the guide: title ≤135 chars (common-abbrev list), abstract ≤200 words, non-standard
abbreviations defined at first use in Abstract/Highlights, Original Articles must be a substantial
contribution. Other numeric caps flagged **[verify]** should be confirmed on the CN submission site.

## 2. Figure / table triage — the paper currently has too many display items

**Now (all "main"):** Table 1, Table 2 (van Putten), Figure 1 (a–d = 4 sub-panels), Figure 2 (+2b),
Figure 3 (van Putten), Figure 4 (**D1–D6 = 6 panels**), Figure 5 (sleep). Plus supplements S1, S2. Figure 4
alone is six panels — far too dense for one main figure.

**Proposed MAIN set (7 display items):**

| # | Main display item | Built from |
|---|---|---|
| Table 1 | Cohort characteristics | `results/table1.md` |
| Figure 1 | Normative model: (a) growth curves + (b) age×stage topoplot | keystone + topoplot |
| Figure 2 | Detection vs 18 experts vs Morgoth (ROC/PR, focal+generalized, CIs) | s0d + s0e |
| Figure 3 | **External validation on Sandor_100** — ours vs SCORE-AI vs Morgoth vs experts | `sandor100_slowing.png` |
| Figure 4 | **Example automated reports** (6 cases; brief+full vs clinical report) — *new* | `s4_examples_panel.png` |
| Figure 5 | Description validated by contrast — condensed to **2 panels**: laterality (D2) + by-stage (D5) | s4_d2 + s4_d5 |
| Figure 6 | Readers under-report slowing in sleep | `v4a_wake_sleep.png` |

**Move to SUPPLEMENTARY:** the deviation-field calibration panel (old Fig 1b) and the curve bank (old Fig 1d);
the van Putten bar chart + full table (Fig 3/Table 2) — the +0.14–0.17 margin can be one sentence + a supp
table; description panels D1, D3, D4, D6 (keep D2+D5 in main); the localized-focal design-search panel (2b);
severity null (S1); human-ceiling detail (S2); the region-focality dose-response.

Net: **6 figures + 1 table** in the main text (down from ~8 figures with many sub-panels + 2 tables), with a
Supplementary Material section holding ~8 items. This matches CN's economy expectation and foregrounds the
two things reviewers will care most about — the **external validation (Fig 3)** and the **example reports
(Fig 4)**.

## 3. Ready-to-use drafts

**Title (≤135 chars):** *"Lifespan, sleep-stage-resolved normative EEG: deviation-from-normal detection and
automated reporting of slowing"* (109 chars). Alt: *"Normative growth curves for EEG slowing across age and
sleep: detection and automated reporting"* (94 chars).

**Highlights (≤85 chars each):**
- Lifespan × sleep-stage normative growth curves score EEG slowing as deviation-from-normal
- One interpretable model detects slowing above an 18-expert panel and a foundation model
- It exceeds the published qEEG (van Putten) indices by 0.14–0.17 AUROC
- It generates clinical slowing reports validated against the clinical record
- External validation on an independent 100-EEG set vs SCORE-AI and experts

**Keywords:** EEG; quantitative EEG; slowing; normative modelling; sleep; automated reporting.

## 4. Prioritized action plan

**P0 — compliance blockers (do before submission)**
1. Trim abstract to ≤200 words (keep the five structured headings incl. Significance).
2. Shorten title to ≤135 chars.
3. Add Highlights (3–5 ≤85-char bullets) + Keywords.
4. Convert citations to Vancouver numbered style and build the numbered reference list (currently absent).
5. Add author block (authors/affiliations/corresponding author/ORCID) + Declarations (CoI, Funding,
   **Ethics/IRB + consent**, Data availability, **CRediT**, Acknowledgements).
6. Execute the figure/table triage (§2): create the Supplementary Material file, renumber main figures.

**P1 — strengthen for review**
7. Finish the **Sandor_100 external validation** (Fig 3) — in progress — and write its Results paragraph.
8. Fold the van Putten benchmark to one paragraph + a supplementary table.
9. Tighten Results prose (the current Results is long); move method detail to Methods/Supp.
10. Re-export all main figures at ≥300 dpi (or vector).

**P2 — polish**
11. Abbreviation sweep (define at first use).
12. Pipeline schematic (Figure 0 / graphical abstract candidate).
13. Consider a graphical abstract (Elsevier optional) — the topoplot or the examples panel work well.

*The new **example-reports figure** (`figures/story/s4_examples_panel.png`; `scripts/62`) is built and
addresses the requested main-text panel of 6 focal/generalized cases across degree and sleep stage with our
brief + full reports beside the clinical report's structured descriptors (raw report text withheld as PHI).*
