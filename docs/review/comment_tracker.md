# Co-author review round 1 — disposition tracker

Source files (Downloads, 2026-08-19): `LENS-slowing-manuscript_mms_wg.docx` (Shafi + Ganglberger, 50 comments),
`LENS-slowing-manuscript_edits_RT.docx` (Thomas: 1 inserted paragraph + 4 reference comments),
`LENS-slowing-manuscript_edits_sfz.docx` (Zafar: authorship only).
`LENS-slowing-manuscript_edits_RT[55].docx` is a byte-identical duplicate of the RT file.

**Base-version note.** `mms_wg` was reviewed against a build matching `origin/main@fd165d7`; `sfz`/`RT` were
reviewed against an older build that had been hand-edited in Word (co-senior author line present, sex-specific
claim already removed, DOI paragraph still `[TBD]`). Canonical source of truth is `docs/manuscript_draft.md`;
the `.docx` is generated from it by `scripts/build_manuscript_docx.py`.

Status: `done` · `open` · `deferred` · `blocked`

| ID | Reviewer | Item | Phase | Status | Where addressed |
|---|---|---|---|---|---|
| sfz-1 | Zafar | Add † (co-senior author) | 0 | done | author block |
| aut-1 | Westover | Beniczky retained (removal reversed); email still needed | 0 | blocked | author emails block |
| aut-2 | Westover | Insert 15 author emails; corresponding → mbwest@stanford.edu | 0 | done | front matter |
| aut-3 | Westover | Affiliations confirmed (Zafar MGH; Struck + Nascimento WashU) | 0 | done | no change needed |
| C3 | Shafi | "Mouhsin M. Shafi" middle initial | 0 | done | author block |
| C180 | Shafi | "sex-specific" contradicts Methods — strike | 0 | done | gap ¶ + Discussion ×2 |
| RT-¶ | Thomas | Insert sleep-variability paragraph in Introduction | 0 | done | §1, refs 19–28 |
| C7 | Thomas | Heritability references | 0 | done | refs 19–22 |
| C12 | Thomas | Polymorphism references | 0 | done | refs 23–25 |
| C15 | Thomas | Slow-wave-activity aging references | 0 | done | refs 26–27 |
| C18 | Thomas | Medication references | 0 | done | ref 28 |
| C93 | Shafi | Table 1 absent from document | 1 | open | builder change |
| C141 | Shafi | Table S1 absent (S2, S3 likewise) | 1 | open | builder change |
| C103 | Shafi | Figure 1 illegible (140–150 dpi) | 1 | open | re-export ≥300 dpi |
| C111 | Shafi | "Figure 1d" missing — it is Figure S3 | 1 | open | renumber |
| C115 | Shafi | "Figure 1b" missing — it is Figure S2 | 1 | open | renumber |
| C138 | Shafi | S7 cited before S1 | 1 | open | renumber |
| C119 | Shafi | LENS-v1 / v2 undefined in Figure 2 | 1 | open | define or remove |
| C191 | Ganglberger | Same as C119 | 1 | open | — |
| C96 | Shafi | 2,671 recordings unaccounted (10,189 + 12,676 ≠ 25,536) | 1 | open | §3.1 + Table 1 |
| C149 | Shafi | Collapse D1–D6 into one figure | 1 | open | figure assembly |
| C153 | Shafi | D1 → panel letter; violins underplay effect | 1,4 | open | — |
| C156 | Shafi | D2 → panel letter; plot named−unnamed difference | 1,4 | open | — |
| C159 | Shafi | D3 → panel letter | 1 | open | — |
| C162 | Shafi | D4 → panel letter | 1 | open | — |
| C165 | Shafi | D5 → panel letter | 1 | open | — |
| C168 | Shafi | D6 → panel letter | 1 | open | — |
| fig-S8 | Westover | Orphan Figure S8 — legend missing (producer exists) | 1 | open | figure list |
| C146-f | Shafi | Figure 4 text illegible | 1 | open | re-export |
| C125 | Shafi | Figure 2b call-out missing | 1 | open | renumber |
| C175 | Shafi | Is N3 delta pathological? (SWS rebound) | 2 | open | abnormality reframe |
| C183 | Shafi | Same, Discussion; suggests focal-only narrowing | 2 | open | abnormality reframe |
| C146-a | Shafi | Staging circularity in encephalopathy (MAJOR) | 2,3 | open | N3 spindle verification |
| C198 | Ganglberger | Held-out centile calibration figure | 3 | open | new Figure S9 |
| C100 | Shafi | Occipital PDR (not C3/C4); split log/linear age axis (MAJOR) | 3 | open | Figure 1 |
| C171 | Shafi | Benchmark concordance vs human readers | 3 | open | new analysis |
| C51 | Shafi | Lateralize anterior/posterior regions | 3 | open | region config |
| C40 | Shafi | Uncontrolled state in overnight studies | 4 | open | Limitations |
| C122 | Shafi | Move two-axes ablation to supplementary | 4 | open | §3.4a |
| C67 | Ganglberger | Delete support-aware refit paragraph | 4 | open | §2.4 |
| C85 | Shafi | No beta-excess measure | 4 | open | Limitations |
| C130 | Shafi | State LENS weakest of three on SAI-100 generalized | 4 | open | §3.4b |
| C133 | Ganglberger | "beats SCORE-AI" is focal-only (incl. Highlight 5) | 4 | open | §3.4b + Highlights |
| C146-b | Shafi | Fig 4 panel (1,1) shows periodic discharges | 4 | open | verify commit 22cad20 |
| C146-c | Shafi | Fig 4 panel (1,2) "3–5 Hz" vs "theta–delta" | 4 | open | precision gap |
| C146-d | Shafi | Fig 4 panel (3,1) "abnormal in 0% of segments" | 4 | open | contradiction |
| C146-e | Shafi | Fig 4 panel (3,2) define "episodes"; 556 implausible | 4 | open | — |
| C6 | Shafi | Abstract "(focal 0.93)" unclear | 4 | open | Abstract |
| C9 | Shafi | "generated reports tracked statements" unclear | 4 | open | Abstract |
| C13 | Shafi | Define "one normative field" | 4 | open | Abstract |
| C19 | Shafi | Cite textbooks for "textbook-settled" | 4 | open | §1 |
| C26 | Shafi | "closest to us" → "the current work" | 4 | open | §1 |
| C31 | Shafi | Give N for Petersén & Eeg-Olofsson | 4 | open | §1 |
| C34 | Shafi | Clarify which John et al. paper the N belongs to | 4 | open | §1 |
| C43 | Shafi | Define "one-vs-clean-normal" | 4 | open | §2.1 |
| C54 | Shafi | Explain relative-delta ≈0.34 calibration | 4 | open | §2.2 |
| C57 | Shafi | Define "EMG-dominated" | 4 | open | §2.2 |
| C46 | Ganglberger | Focal∩generalized overlap N or % | 4 | open | §2.1 |
| C63 | Ganglberger | GAMLSS design matrix / unit / weighting | 4 | open | §2.4 |
| C65 | Ganglberger | Does BCT carry a tail parameter? | 4 | open | §2.4 |
| C70 | Ganglberger | Deviation-field tensor dimensions | 4 | open | §2.5 |
| C72 | Ganglberger | Report→EEG pairing explanation confusing | 4 | open | §2.6 |
| C76 | Ganglberger | What model class is LENS? (reject risk) | 4 | open | §2.7 |
| C77 | Ganglberger | CV scheme / hyperparameter selection | 4 | open | §2.7 |
| C78 | Ganglberger | Justify top-5 aggregation | 4 | open | §2.7 |
| C79 | Shafi | Recording-level call for intermittent focal slowing | 4 | open | §2.7 |
| CN-1 | — | Abstract 236 → ≤200 words | 4 | open | Abstract |
| CN-2 | — | ORCIDs; CRediT; Acknowledgements | 4 | open | Declarations |
| CN-3 | — | Figures ≥300 dpi / vector | 1 | open | assembly |
| CN-4 | — | References not in citation order (pre-existing) | 6 | open | final renumber |
| REL-1 | — | Verify S3 derived + panels + raw EDF resolution | 5 | done | 66.7 GiB / 164,718 objects |
| REL-2 | — | Run `results` reproduce tier; verify contract table | 5 | open | — |
| REL-3 | — | Stale bdsp.io slug in `DATA_SOURCE.md` | 5 | open | — |
| REL-4 | — | Publish updated bdsp.io version; refresh DOI | 5 | open | — |
| REL-5 | — | `REPRODUCE.md` names nonexistent `opendata` profile | 5 | open | working profile is `bidmc` |
