# Co-author review round 1 — disposition tracker

Source files (Downloads, 2026-08-19): `LENS-slowing-manuscript_mms_wg.docx` (Shafi + Ganglberger, 50 comments),
`LENS-slowing-manuscript_edits_RT.docx` (Thomas: 1 inserted paragraph + 4 reference comments),
`LENS-slowing-manuscript_edits_sfz.docx` (Zafar: authorship only).
`LENS-slowing-manuscript_edits_RT[55].docx` is a byte-identical duplicate of the RT file.

**Base-version note.** `mms_wg` was reviewed against a build matching `origin/main@fd165d7`; `sfz`/`RT` were
reviewed against an older build that had been hand-edited in Word (co-senior author line present, sex-specific
claim already removed, DOI paragraph still `[TBD]`). Canonical source of truth is `docs/manuscript_draft.md`;
the `.docx` is generated from it by `scripts/build_manuscript_docx.py`.

Status: `done` · `partial` · `open` · `blocked`

**Round-1 outcome: 75 of 76 items done. One remains open -- REL-4 (bdsp.io version bump), deliberately held
until the draft is agreed. Nothing is blocked: the SAI-100 workbook was recovered from Box, so 3.4b is now
scored at top-20 like ON-100 and Figure 3 regenerates at page width. Zero figures trip the width legibility guard -- but see round 2 below: the guard only measured WIDTH, and four figures were failing on printed HEIGHT.** The open items are listed at the
bottom of this file with the reason each was not closed.

| ID | Reviewer | Item | Phase | Status | Where addressed |
|---|---|---|---|---|---|
| sfz-1 | Zafar | Add † (co-senior author) | 0 | done | author block |
| aut-1 | Westover | Beniczky retained (removal reversed); email still needed | 0 | done | author emails block |
| aut-2 | Westover | Insert 15 author emails; corresponding → mbwest@stanford.edu | 0 | done | front matter |
| aut-3 | Westover | Affiliations confirmed (Zafar MGH; Struck + Nascimento WashU) | 0 | done | no change needed |
| C3 | Shafi | "Mouhsin M. Shafi" middle initial | 0 | done | author block |
| C180 | Shafi | "sex-specific" contradicts Methods — strike | 0 | done | gap ¶ + Discussion ×2 |
| RT-¶ | Thomas | Insert sleep-variability paragraph in Introduction | 0 | done | §1, refs 19–28 |
| C7 | Thomas | Heritability references | 0 | done | refs 19–22 |
| C12 | Thomas | Polymorphism references | 0 | done | refs 23–25 |
| C15 | Thomas | Slow-wave-activity aging references | 0 | done | refs 26–27 |
| C18 | Thomas | Medication references | 0 | done | ref 28 |
| C93 | Shafi | Table 1 absent from document | 1 | done | builder change |
| C141 | Shafi | Table S1 absent (S2, S3 likewise) | 1 | done | builder change |
| C103 | Shafi | Figure 1 illegible (140–150 dpi) | 1 | done | re-export ≥300 dpi |
| C111 | Shafi | "Figure 1d" missing — it is Figure S3 | 1 | done | renumber |
| C115 | Shafi | "Figure 1b" missing — it is Figure S2 | 1 | done | renumber |
| C138 | Shafi | S7 cited before S1 | 1 | done | renumber |
| C119 | Shafi | LENS-v1 / v2 undefined in Figure 2 | 1 | done | define or remove |
| C191 | Ganglberger | Same as C119 | 1 | done | — |
| C96 | Shafi | 2,671 recordings unaccounted (10,189 + 12,676 ≠ 25,536) | 1 | done | §3.1 + Table 1 |
| C149 | Shafi | Collapse D1–D6 into one figure | 1 | done | figure assembly |
| C153 | Shafi | D1 → panel letter; violins underplay effect | 1,4 | done | — |
| C156 | Shafi | D2 → panel letter; plot named−unnamed difference | 1,4 | done | — |
| C159 | Shafi | D3 → panel letter | 1 | done | — |
| C162 | Shafi | D4 → panel letter | 1 | done | — |
| C165 | Shafi | D5 → panel letter | 1 | done | — |
| C168 | Shafi | D6 → panel letter | 1 | done | — |
| fig-S8 | Westover | Orphan Figure S8 — legend missing (producer exists) | 1 | done | figure list |
| C146-f | Shafi | Figure 4 text illegible | 1 | done | re-export |
| C125 | Shafi | Figure 2b call-out missing | 1 | done | renumber |
| C175 | Shafi | Is N3 delta pathological? (SWS rebound) | 2 | done | abnormality reframe |
| C183 | Shafi | Same, Discussion; suggests focal-only narrowing | 2 | done | abnormality reframe |
| C146-a | Shafi | Staging circularity in encephalopathy (MAJOR) | 2,3 | done | N3 spindle verification |
| C198 | Ganglberger | Held-out centile calibration figure | 3 | done | new Figure S9 |
| C100 | Shafi | Occipital PDR (not C3/C4); split log/linear age axis (MAJOR) | 3 | done | Figure 1 |
| C171 | Shafi | Benchmark concordance vs human readers | 3 | done | new analysis |
| C51 | Shafi | Lateralize anterior/posterior regions | 3 | done | region config |
| C40 | Shafi | Uncontrolled state in overnight studies | 4 | done | Limitations |
| C122 | Shafi | Move two-axes ablation to supplementary | 4 | done | §3.4a |
| C67 | Ganglberger | Delete support-aware refit paragraph | 4 | done | §2.4 |
| C85 | Shafi | No beta-excess measure | 4 | done | Limitations |
| C130 | Shafi | State LENS weakest of three on SAI-100 generalized | 4 | done | §3.4b |
| C133 | Ganglberger | "beats SCORE-AI" is focal-only (incl. Highlight 5) | 4 | done | §3.4b + Highlights |
| C146-b | Shafi | Fig 4 panel (1,1) shows periodic discharges | 4 | done | verify commit 22cad20 |
| C146-c | Shafi | Fig 4 panel (1,2) "3–5 Hz" vs "theta–delta" | 4 | done | tested; null (rho 0.13/0.04) -- documented as a limitation |
| C146-d | Shafi | Fig 4 panel (3,1) "abnormal in 0% of segments" | 4 | done | contradiction |
| C146-e | Shafi | Fig 4 panel (3,2) define "episodes"; 556 implausible | 4 | done | — |
| C6 | Shafi | Abstract "(focal 0.93)" unclear | 4 | done | Abstract |
| C9 | Shafi | "generated reports tracked statements" unclear | 4 | done | Abstract |
| C13 | Shafi | Define "one normative field" | 4 | done | Abstract |
| C19 | Shafi | Cite textbooks for "textbook-settled" | 4 | done | §1 |
| C26 | Shafi | "closest to us" → "the current work" | 4 | done | §1 |
| C31 | Shafi | Give N for Petersén & Eeg-Olofsson | 4 | done | §1 |
| C34 | Shafi | Clarify which John et al. paper the N belongs to | 4 | done | §1 |
| C43 | Shafi | Define "one-vs-clean-normal" | 4 | done | §2.1 |
| C54 | Shafi | Explain relative-delta ≈0.34 calibration | 4 | done | §2.2 |
| C57 | Shafi | Define "EMG-dominated" | 4 | done | §2.2 |
| C46 | Ganglberger | Focal∩generalized overlap N or % | 4 | done | §2.1 |
| C63 | Ganglberger | GAMLSS design matrix / unit / weighting | 4 | done | §2.4 |
| C65 | Ganglberger | Does BCT carry a tail parameter? | 4 | done | §2.4 |
| C70 | Ganglberger | Deviation-field tensor dimensions | 4 | done | §2.5 |
| C72 | Ganglberger | Report→EEG pairing explanation confusing | 4 | done | §2.6 |
| C76 | Ganglberger | What model class is LENS? (reject risk) | 4 | done | §2.7 |
| C77 | Ganglberger | CV scheme / hyperparameter selection | 4 | done | §2.7 |
| C78 | Ganglberger | Justify top-5 aggregation | 4 | done | §2.7 |
| C79 | Shafi | Recording-level call for intermittent focal slowing | 4 | done | §2.7 |
| CN-1 | — | Abstract 236 → ≤200 words | 4 | done | Abstract |
| CN-2 | — | ORCIDs; CRediT; Acknowledgements | 4 | done | Declarations |
| CN-3 | — | Figures ≥300 dpi / vector | 1 | done | assembly |
| CN-4 | — | References not in citation order (pre-existing) | 6 | done | final renumber |
| REL-1 | — | Verify S3 derived + panels + raw EDF resolution | 5 | done | 66.7 GiB / 164,718 objects |
| REL-2 | — | Run `results` reproduce tier; verify contract table | 5 | done | — |
| REL-3 | — | Stale bdsp.io slug in `DATA_SOURCE.md` | 5 | done | — |
| REL-4 | — | Publish updated bdsp.io version; refresh DOI | 5 | open | — |
| REL-5 | — | `REPRODUCE.md` names nonexistent `opendata` profile | 5 | done | replaced with the placeholder `<your-bdsp-profile>` + a `aws s3 ls` check, since the working profile name is per-machine (`bdsp` and `opendata` both work here; `bidmc` does not exist) |

## Not closed in this pass

*(This table used to list ~15 items as open while the header above said 75 of 76 were done. It was left
behind by an earlier pass and contradicted the disposition table, which is the authority. It is replaced by
the round-2 log below; the only round-1 item still open is REL-4.)*

| ID | Why |
|---|---|
| REL-4 | bdsp.io version bump + DOI refresh. Deliberately not done: it publishes outward and should follow the co-authors' sign-off on this draft, not precede it. |

---

# Round 2 — automated pre-submission audit, 2026-08-26

Run of the two BDSP checker pipelines against this draft, plus the reproducibility certificate:

- `bdsp-core/paper-agents-figures` on all 16 composited submission figures (8 agents: story, composition,
  colour, typography, format, caption, statistics, cross-figure consistency).
- `bdsp-core/paper-agents-manuscript` on `docs/manuscript_draft.md` with `--repo-path .` (13 agents incl.
  truthfulness/code-grounding and internal consistency).
- `scripts/certify_reproducibility.py` (checks A/B/C/E) and `scripts/verify_fresh_install.sh` (check D).

**Both checkers were broken on Claude Opus 5 before this run** — they read `resp.content[0].text`, which is a
`ThinkingBlock` on any model with thinking on, so every agent failed with an `AttributeError`. Both were
patched locally (`_text_of()` + a real `max_tokens`); those patches are in the checker clones, not in this
repo, and should be pushed upstream.

| ID | Source | Item | Status | Where addressed |
|---|---|---|---|---|
| R2-1 | manuscript checker | Highlights claim "detects slowing above experts and a foundation model" and "beats SCORE-AI", contradicting §3.4b where LENS is last of three on SAI-100 generalized. Same overclaim in the Conclusion. (This is C133 re-opening: it was closed in §3.4b but never propagated to the Highlights.) | done | Highlights rewritten axis- and site-explicit; Conclusion states both sites and both axes |
| R2-2 | manuscript checker | Discussion never confronts the SAI-100 generalized negative | done | new §4 subsection "Generalized detection does not yet transfer; focal does" — three candidate explanations, and what we would deploy |
| R2-3 | manuscript checker | Abstract "identify, localize **and describe**" conflates the supervised detectors with the unsupervised description layer | done | Abstract Methods |
| R2-4 | manuscript checker | Abstract "median centile error 1.0 point" vs `results/story/centile_calibration.md` median 1.1 | done | Abstract |
| R2-5 | manuscript checker | Abstract "exceeding … by 0.09--0.14" excludes the actual focal margin (+0.08) and misstates the gate margin | done | Abstract; `vanputten_panel_s7.py` now emits the margins so they cannot drift again |
| R2-6 | manuscript checker | "83% and 53% of **the 18 experts**" — 53% is not attainable at n=18; the focal panel has 17 operating points | done | §3.4a explains the operating-point rule; Figure 2 caption states it |
| R2-7 | manuscript checker | SAI-100: paper says 14 experts, `sandor_focal_label_correction.csv` says `n_raters = 11` | done | Settled from the source workbook: **14 expert columns, exactly 11 non-null per recording** (incomplete design). §2.7/§3.4b now say so and reconcile both numbers |
| R2-8 | manuscript checker | `docs/claims_table.md` clause 1 says the Morgoth-free detector reaches 0.946 / 0.923; the paper says 0.961 / 0.908 | done | claims table refreshed and the superseded pre-C51 numbers labelled as such |
| R2-9 | manuscript checker | 7,216 held out vs 10,189 − 3,000 = 7,189 | done | The reference is 10,216 (norm fitting is not gated on the cohort inclusion filter); §3.3 and `centile_calibration.md` now state the denominator and the 27-recording difference |
| R2-10 | manuscript checker | §2.2 cites `config/channels_regions.yaml` for eleven regions; that file defines six and says it is not read by the fleet | done | §2.2 now cites `scripts/43` (`REGIONS`, 11) and `recording.py` (`AGG_REGIONS`, 6) |
| R2-11 | manuscript checker | Discussion quotes van Putten focal 0.723 vs gate 0.870 while §3.5 quotes 0.825 vs 0.908, unlabelled | done | Both sets now named (full report cohort vs clean ON-100 panel) with the reason they differ |
| R2-12 | manuscript checker | `docs/audits/audit-report-1.md` ships unresolved, alleging the norms are a Gaussian kernel not GAMLSS, no cross-fitting, and a headline AUROC collapse | done | Marked **SUPERSEDED** with a per-finding resolution table and the command that verifies each. Verified: 110 BCT + 220 normal-family cells in `grid_norm.json`, held-out calibration in `scripts/78`, and neither 0.848 nor `scripts/96` exists any more |
| R2-13 | manuscript checker | "open-source package" vs a CC BY-NC 4.0 licence | done | "openly available"/"under CC BY-NC 4.0" |
| R2-14 | manuscript checker | Missing limitation: the normal reference is clinically-normal EEG from referred patients, not healthy volunteers | done | new first paragraph of §5, incl. the expected direction of the bias |
| R2-15 | manuscript checker | Captions are file paths, not prose | done | every caption rewritten self-contained; provenance moved to one table at the end of the section |
| R2-16 | figure checker + own inspection | **Figure 1 axis labels print at ~4 pt.** C103 was closed by re-exporting at 300 dpi, which raises resolution but not printed point size: the composite is too tall for a 190×240 mm page, so the journal scales it down and every label with it | done | `scripts/76` shorter rows + no in-figure title, type raised to ≥6.6 pt; `assemble_manuscript_figures.py` now measures printed size and type scale and fails loudly below 6 pt |
| R2-17 | own inspection | Figure 1A row label "REM" clipped off the canvas | done | `scripts/76` margins + `bbox_inches="tight"` |
| R2-18 | own inspection | Figure 1B in-figure title overprints the first row's n= labels | done | title moved to the caption (`scripts/77`) |
| R2-19 | own inspection | **Figure 6 / S8 panel titles clipped at both edges**; the right subplot's y-label overprints the left subplot's title | done | `scripts/57` suptitles removed to the captions, labels shortened, `bbox_inches="tight"` everywhere |
| R2-20 | own inspection | Figure 2 PRC legend struck through by its own curve; legend type 5.6 pt | done | `scripts/54`/`55` legend moved to lower-left, 6.5 pt |
| R2-21 | own inspection | **Figure 4/5: 10 of 18 channel labels overprint their neighbour** — unreadable exactly where a clinical reader needs it. C146-f was closed by re-export and did not fix this | done | `scripts/63` lays out in absolute inches derived from the type size, and `check_label_spacing()` now fails the build if labels are ever closer together than they are tall |
| R2-22 | C153 (round 1, marked done) | "violins underplay the effect" — the violins were still bare | done | `contrast()` overlays mean + bootstrap 95% CI and per-group n |
| R2-23 | C156 (round 1, marked done) | "plot the named−unnamed difference" — two absolute bars were still plotted | done | `scripts/57` D2 now plots the difference with a bootstrap 95% CI |
| R2-24 | own inspection | Figures S2, S5, S8 authored too tall to fit a page; type printed at 62–88% | done | `scripts/78`, `111`, `57`, `58` reshaped; every figure now prints its smallest type at ≥6 pt |
| R2-25 | reproducibility | `scripts/verify_fresh_install.sh` hardcoded `/Users/mbwest/Desktop/...`, read `/tmp/exids.txt`, required `.venv`, and **never checked byte-identity** despite being the check-D evidence | done | rewritten: repo-root-relative, pins read from `PINNED_EXAMPLES` in `scripts/62`, results/ compared byte-for-byte and figures by blurred intensity |
| R2-26 | reproducibility | Nothing pinned the environment, so "bit-identical figures" could not hold | done | `requirements.lock.txt` (measured: numbers reproduce byte-for-byte across matplotlib versions, PNGs do not) |
| R2-27 | reproducibility | Table S4 (the full generated-vs-clinical report text) existed as `results/story/s4_examples.md` but was cited by no display item | done | promoted to Table S4, wired into `REPRODUCE.md`, and `scripts/62` now writes the report's own sentences into it |

| R2-31 | figure checker | **Figure S9's in-figure title read "Figure S1"** — the actual S1 is the architecture schematic, so every cross-reference would have landed on the wrong figure | done | in-figure titles removed from S6 and S9 (they belong in captions, where a renumber cannot desync them) |
| R2-32 | figure checker | Two contradictory sleep-stage colour maps: Figure 1A had W gold / N3 navy, Figure S5 had W dark blue / N3 red — same five categories, unrelated hues | done | one mapping in `viz/palette.STAGE`; both producers read it |
| R2-33 | figure checker | Four ROC figures at four aspect ratios, so the chance diagonal was at 45° in two and flattened in two | done | `aspect="equal"` on every ROC/PRC axis (54, 55, 49, sandor100, vanputten_panel_s7); S3 given the height square axes need |
| R2-34 | figure checker | Four phrasings of "% experts under the curve", on a denominator of 14–18 | done | one convention: `15/18 experts under` |
| R2-35 | figure checker | Panel letters on fewer than half the multi-panel figures | done | added to Figures 3, S3, S7, S9; assembler letters given their own line |
| R2-36 | figure checker | "Morgoth-FREE" used "Morgoth" as a negation while the same word names the sleep stager and the reference detector | done | removed from Figure S7 |
| R2-37 | figure checker | Figure 2 and Figure S3 report the same curves on the same cohort and neither said so — reads as independent replication | done | stated in both captions |
| R2-38 | figure checker | **Figure S1 unusable**: every box's label overflowed and overprinted its neighbours, five strings illegible. `matplotlib` wraps to the FIGURE width, not the artist's | done | `architecture_diagram.py` rewritten: text wrapped to the box width, boxes grow to fit, so a label cannot overflow however it is edited |
| R2-39 | figure checker | Figure S6's y-axis label clipped by the canvas, taking the error-bar definition with it; clean-normal drawn green against red abnormal (invisible under deuteranopia and in greyscale, and grey elsewhere for the same group) | done | label shortened, definition to the caption; grey vs the paper's orange |
| R2-40 | figure checker | Figure 6's `***` markers and error bars undefined anywhere in the figure | done | one key line under the panel, worded identically in the caption |
| R2-41 | figure checker | Figure 7 set 1.5–2× the rest of the set, and the only figure with point estimates at n in the thousands and no uncertainty | done | page-width canvas; Wilson score 95% CIs |
| R2-42 | figure checker | Red carries eight meanings across the set (left hemisphere, report slowing, delta-excess, visible-only-in-sleep, abnormal, anterior, experts-above-curve) and blue nearly as many | done | `viz/palette` now holds a REGISTRY, not a palette: `BAND`, `SIDE`, `TOPO` and `NEUTRAL` families that share no hue with each other or with the reserved method colours (LENS orange, Morgoth purple, SCORE-AI blue, experts grey, abnormal brick). Every producer reads it. Where the x-axis already names the categories (Figure 6A-right, Figure 7, S8D) the bars are now neutral — a hue is not spent on something the axis has said |
| R2-43 | figure checker | Three warm tones read as one colour: LENS vermillion, ON-100 rust, brick red medians | done | orange is reserved for LENS; brick is reserved for abnormal/report-slowing; nothing else is warm |
| R2-44 | figure checker | Quantity names differ between figures ("Relative delta (δ / total)" / "rel_delta" / "relative delta"; "TAR" / "log TAR" / "theta/alpha ratio") | done | `palette.FEATURE_LABEL` / `flabel()`; scripts 44, 76, 77, 78 and 111 all look the display name up rather than printing the column name |
| R2-46 | figure checker | Figure 2 gave Morgoth's focal AUROC with no CI while Figure S3 gave [0.83–0.97] for the same quantity | done | both comparators now carry a bootstrap 95% CI in `scripts/55` |
| R2-47 | figure checker | Panel letters missing on Figures 4, 5 and S6 | done | one letter per example in Figures 4/5, one per feature panel in S6 |
| R2-48 | own | **`verify_fresh_install.sh` emptied 198 local panel partitions.** It moved the real tables to a temp directory and relied on a trap; anything running concurrently against `data/derived` — including a producer I ran myself — saw a partial tree, and the restore lost them | done | The hidden copies now stay inside `data/derived/.fresh_install_stash`, so a crash leaves them one rename from correct; `recover_stash()` restores them automatically on the next run; and an atomic `mkdir` lock plus a loud banner stop anything else running against the checkout mid-verification. Data was re-synced from S3 (it is the published cache, so nothing was permanently lost) |
| R2-28 | reproducibility | **Figure 3 did not reproduce from git + S3** — it read the SAI-100 expert workbook from a Box mount, so it rebuilt on exactly one machine | done | `scripts/export_sai100_panel.py` exports a de-identified panel (study pseudonyms, integer rater ids, ages > 89 binned to 90, every other workbook column dropped, checks asserted rather than assumed) and it is published to the credentialed prefix. Verified: with `SANDOR_DIR` pointed at a nonexistent path, Figure 3 rebuilds with **identical numbers**. The SCORE-AI workbooks and the EEG signal are not redistributed |
| R2-49 | figure checker | **Every one of the 16 figures printed below 300 DPI** (209–266), while the file metadata said 300 and every checker read that back and passed it. A figure scaled UP to fill the column spreads the same pixels over more paper — the same trap as the type-size one, one layer down | done | `assemble_manuscript_figures.py` renders once to learn the natural size, computes the page scale, then re-renders at 300 × that scale. All 16 now print at exactly 300 DPI, reported per figure in `figures/manuscript/MANIFEST.md` and failed loudly below it |
| R2-50 | figure checker | Purple meant "expert above the curve" in Figure S7 and "Morgoth" in the adjacent Figures 2/3/S3 — a collision I introduced in the previous pass | done | filled vs hollow markers instead of a second hue; S7 also gains the bootstrap 95% CI the rest of the ROC family carries |
| R2-45 | figure checker | Figure 1B/S4 and Figure S5 report per-stage n that differ tenfold for the same cohort (N2 817 vs 7,823) | done | Real and explainable: Figure 1B applies the source-appropriate rule (wake from routine, sleep from overnight, never pooled, because ratio features are not comparable across acquisition types) and Figure S5 does not. Stated in both captions. **Whether S5 should apply the same restriction is an author call** — it would change a committed supplementary figure |

## Still open after round 2

| ID | Item | Why it is not closed |
|---|---|---|
| REL-4 | bdsp.io version bump + DOI refresh | Publishes outward; should follow co-author sign-off |
| R2-29 | Promote Figure S1 (the architecture schematic) to Figure 1 | The manuscript checker's strongest structural suggestion: S1 is the only image that carries the thesis and skimmers never see it. It reorders the whole display set and changes what the co-authors reviewed, so it is a call for the senior authors |
| R2-30 | Related-work gaps: SCORE-AI in the Introduction, normative-modelling toolkits, HarMNqEEG / Cuban lifespan qEEG norms, the aperiodic-component literature | Needs the Scholar-backed reference agents (skipped in this run to avoid Google Scholar rate-limiting) and an author decision on which to cite |
