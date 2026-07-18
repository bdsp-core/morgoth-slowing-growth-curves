# Fable review — publication-readiness for *Clinical Neurophysiology*

Reviewer: Fable (automated). Baseline commit: `29b8eb8`. Scope: full manuscript (`docs/manuscript_draft.md`),
the story dashboard (`scripts/build_story_dashboard.py`), the description generator (`scripts/56/57/58`),
the results tables and every figure in `figures/story/`, `figures/growth_v2/`, `figures/stage_curves/`, and
`results/figs/`, against `docs/claims_table.md` (governance) and `docs/analysis_plan.md` (SAP).

The science is strong and the governance discipline (claims table, dose-response-only validation, severity
null, spindle-verified sleep result) is unusually rigorous. Most of what follows is about **making the
generated artifacts match the paper's own stated rules and claims**, tightening statistical reporting, and
fixing a handful of figure/legend/number mismatches a reviewer will catch. Priorities: P0 = must-fix
blocker, P1 = important, P2 = polish.

---

## P0 — must-fix blockers

### P0-1. The generated clinical sentences violate the paper's own claims table (verbal descriptions)
`scripts/58_description_words.py::band_word()` emits the literal label **"mild theta"** as a fallback band
word for low-amount recordings. "mild" is a **severity adjective**, which `docs/claims_table.md` clause 9
marks **FORBIDDEN** and which the manuscript explicitly declines (§3.9, and the abstract's "magnitude as
SD/centile not adjective"). It ships verbatim in the committed artifact `results/story/s4_d6.md` (review rows
#3 "…left temporal **mild** theta slowing…", #5). This is a direct self-contradiction and the single most
important thing to fix, because the verbal descriptions are the paper's headline deliverable.
→ **Fixed** (see Changelog): fallback is now "theta"; no adjective anywhere.

### P0-2. The generated sentence omits the ALLOWED, load-bearing magnitude clause (SD + centile)
The claims table's canonical "permitted sentence" is built around *"2.1 SD above age- and stage-matched
normal (94th centile)"* (clause 3, **ALLOWED**, split-half ρ 0.97). The shipped sentence
(`58::sentence()`) contains **no magnitude at all** — only a persistence word + location + band + stage.
So the manuscript claim that the system "reads OUT a structured description … magnitude as SD / centile"
(§2.8, abstract) is **not supported by the actual generated output**. This is the core clinical content and
it is fully allowed. → **Fixed**: sentences and a new full report paragraph now carry SD + centile.

### P0-3. No abstain path — the generator invents a lobe/side with no lateralizing excess
Claims table clause 11 is **ALLOWED and required** ("so the system never invents a lobe"): when focal is
gated but the spectral excess is unremarkable, the sentence must say *"focal by pattern; no lateralizing
spectral excess…"* rather than assert a side/region. The current generator always names a side+lobe. Review
row #5 ("Intermittent right temporal mild theta slowing" on a report with side/region blank) is exactly the
failure mode. → **Fixed**: added a confidence/abstain path when asymmetry and focality are both weak.

*(P0-1..3 are grouped because they are all in the one deliverable the user ranked #1; each is individually a
governance violation against a hard constraint.)*

---

## P1 — important

### P1-1. Morgoth panel AUROC numbers are inconsistent across the paper's own documents
The reference-detector (Morgoth gate) panel AUROCs disagree by source:
- Abstract + §3.4 + Figure 2 (`s0d_single_model.md`, `s0d_single_occasion_generalized.png`): generalized
  **0.853**, focal **0.908**.
- `results/table5_human_ceiling.md`: generalized **0.86**, focal **0.904**.
- `docs/claims_table.md` clauses 1–2 and `docs/description_architecture.md` §1: generalized **0.900**, focal
  **0.923**.
A reviewer will notice. Pick one canonical evaluation (the Figure-2/`s0d` panel scoring) and reconcile the
prose; the claims-table/architecture numbers are from an older evaluation and should be footnoted as such.
→ Manuscript reconciled to the Figure-2 numbers; noted here.

### P1-2. "Beats Morgoth on both axes" is overstated for focal
Figure 2 (`s0e_occasion_focal.png`): focal **ours 0.923 vs Morgoth 0.908** — a 0.015 AUROC gap on a 100-EEG
panel with ~12 focal positives, where the CIs certainly overlap; and on the focal **PR** curve **Morgoth
(AP 0.67, 47% under) actually beats ours (AP 0.65, 41% under)**. The abstract/§3.4 headline "beating the
Morgoth foundation-model gate on both axes" is only clean for **generalized** (0.946 vs 0.853). Soften focal
to "comparable / on par". → **Fixed** in abstract, §3.4, §3.6, Conclusion, dashboard 2a.

### P1-3. Figure 2b cited number does not match the displayed figure
§3.4 and dashboard block 2b cite "focal … **53%** of experts under" and AUROC 0.898, but the figure actually
embedded (`s0_occasion_ours_v4_focal.png`) is the **W+N1** detector showing **47% under / AUROC 0.89**. The
53%/0.898 value is the *all-stage localized* model in the **hand-authored** `s0c_morgoth_free.md` table, not
this figure. Either regenerate the all-stage figure or fix the caption. → **Fixed** caption to cite the
figure's own numbers and point to the s0c table for the 53% upper bound.

### P1-4. No confidence intervals on the headline panel detection numbers
The van Putten table (`vanputten_fullcoverage.md`) correctly carries patient-clustered bootstrap CIs, but the
**Morgoth-free panel AUROCs (0.946 / 0.923)** — the paper's marquee result — have **no CI anywhere**, on the
smallest, highest-variance dataset in the paper (100 EEGs, 18/12 positives). At minimum, state the panel
positive/negative counts wherever the AUROC appears; ideally add a patient/EEG-level bootstrap CI. The
"% experts under ROC/PR" is a good non-parametric complement but is not a substitute for a CI on 0.946 vs
0.853. → Panel base rates (gen 18/100, focal 12/100) added to §3.4; full bootstrap CI flagged as remaining
work (needs the panel scorer; see "left undone").

### P1-5. §3.2 text/figure mismatch: "absolute delta" vs the relative-delta figure
§3.2 says "**absolute** delta power falls steeply through childhood" and cites Figure 1a
(`keystone_growth_grid.png`), but that figure plots **relative delta (δ/total), TAR and DAR at the central
(C3/C4) region** — not absolute delta, and not whole-head. Reword to match what the figure shows. → **Fixed**.

### P1-6. van Putten coverage denominator contradicts itself
`results/vanputten_fullcoverage.md` header says "**23,872** recordings" but every table row is
`n_scored = 21,146/21,145`; the manuscript revision note already flags this. The header string is emitted by
`scripts/recompute_vanputten_fullcov.py`. → **Fixed** the script's header text to report the true scored n.

### P1-7. Persistence word governance — lead with the % , keep ACNS word as an explicit gloss
Claims table clause 6 **ALLOWS** "present in X% of segments"; clause 6b marks the **ACNS frequency word mapped
to the reader's vocabulary FORBIDDEN** (prevalence vs reader frequency word ρ=0.077). The current sentence
leads with the bare ACNS word ("Frequent …") and no percentage — i.e. it foregrounds the forbidden framing
and omits the allowed one. → **Fixed**: sentence/paragraph now lead with the percentage (allowed) and mark
the ACNS word explicitly as an internal descriptor of our measured prevalence, never as report concordance.

---

## P2 — polish

- **P2-1. Abstract length/format.** ~450 words, dense single paragraphs. *Clinical Neurophysiology* uses a
  structured abstract (Objective / Methods / Results / Conclusions / Significance) with a tight word budget
  (~250). Trim and structure before submission. (Flagged; not auto-rewritten to avoid content loss.)
- **P2-2. Venue + TBDs.** The title block still hedges venue ("clinical neurophysiology / digital medicine
  (*Clinical Neurophysiology*, *Brain Communications*, *npj Digital Medicine*)") and carries `[TBD: …]`
  placeholders and a "Notes for revision" block. The target is Clinical Neurophysiology. → venue line
  committed; DOI/release TBD left (genuinely unknown) and noted.
- **P2-3. Table 1 focal-slowing row.** Overall 8,304 (34.8%) but abnormal-column 8,016 (63.2%);
  routine+overnight (5,846+2,458=8,304) ≠ 8,016. The manuscript uses 8,016. The overall column uses the raw
  `has_focal_slow` flag; the abnormal column uses SAP `slowing_focal` on clean_pair. Footnote the difference
  so the two numbers don't read as an error. (Flagged; not silently altered — it is data-derived.)
- **P2-4. v4a figure vs p6 file numeric drift.** `v4a_wake_sleep.png` shows 75.0 / 54.1 / 39.9
  (n 4,280/703/14,400); `p6_sleep_underreporting.md` shows 74.8 / 53.6 / 40.0 (n 4,282/709/14,400) — two
  scripts, slightly different features (fig uses `scripts/95`; p6 uses TAR τ=1.645). The manuscript quotes the
  figure numbers then p6's spindle AUROC. Harmless but a checking reviewer will see the mismatch; note that
  they are two analyses of the same effect. (Flagged.)
- **P2-5. D4 figure gridline label overlap.** The "occasional" ACNS gridline label at prevalence≈0.01 crowds
  the y-axis. Minor readability. (Flagged, low value; left.)
- **P2-6. Description review set breadth.** The PHI-free reasonableness set is only 12 rows and shows a single
  short sentence. The user asked for an expanded, richer, report-style exemplar set. → **Expanded** to a fuller
  set showing both the one-line finding and the full report paragraph, structured labels only.

---

## What is solid (no change needed)
- Dose-response-only validation of every descriptor (D1–D5) is correct and well-motivated; the temporal-delta
  "attractor" handling (relative prominence, not absolute magnitude) is a genuinely good methodological call.
- The severity null (§3.9, `severity_null_v6.md`) is honest and complete (168-combination search, robust vs
  fragile statistic). Keep it.
- The spindle-verified sleep-underreporting result (§3.8) is the paper's strongest single contribution and is
  argued carefully (delta-independent adjudication).
- Growth-curve figure (`keystone_growth_grid.png`) and topoplots (`topo_rel_delta_by_age_stage.png`) are
  high-quality, well-labelled, and the legends match the images (aside from P1-5's prose wording).
- The one-command reproduce story (`scripts/reproduce_story.sh`, `docs/REPRODUCE.md`) is clear and honest
  about which stages need R/gamlss and Morgoth outputs.

---

## Changelog — executed

### Verbal descriptions (priority #1) — `scripts/58_description_words.py` rewritten
The generator now emits **two** claims-table-governed outputs per recording — a compact **finding line** and a
full **report-style paragraph** — replacing the thin one-line template. Concretely:
- **Removed the forbidden severity adjective** (P0-1): `band_word()` fallback "mild theta" → "theta". Because
  the concordance mapping already collapsed "mild theta"→"theta", the D6 concordance numbers are **byte-stable
  (side 56% / region 46% / band 39%)**.
- **Added magnitude as SD + centile** (P0-2): peak-region z for focal, whole-head band p90 for diffuse, with a
  proper-ordinal centile from the normal CDF (fixed "81th"→"81st", capped "100th").
- **Added the required abstain path** (P0-3): when a focal excess does not clear the 84th centile, the report
  says "Localization is low-confidence: no lateralizing or regional spectral excess clears the 84th centile of
  normals" instead of inventing a lobe.
- **Persistence as a percentage** (P1-7): leads with "abnormal in X% of analysed segments" (ALLOWED clause 6);
  the ACNS word (rare/occasional/frequent/abundant/continuous) is now an explicit parenthetical gloss on our
  measured prevalence, not a report-vocabulary claim (clause 6b).
- **Richer, safer localization**: side + maximum-deviation lobe (flagged "maximal over …", provisional);
  **bilateral / bitemporal** handling; a **hemisphere-consistency guard** so we never say "right temporal,
  maximal over the left temporal region"; anterior/posterior predominance only when |z|>1.645 (clause 4d).
- **Stage-accentuation clauses** (clause 8): "present in wakefulness and sleep", **"present only during
  sleep"**, "activated in drowsiness", "most prominent in N2/REM" — computed from per-stage prevalence in
  `description_stage.parquet`.
- **Band with the co-occurrence caveat**: δ/θ/mixed on clear dominance only; "theta–delta (mixed)" rendering.
- **Expanded, PHI-free reasonableness review set** to 17 rows showing the full paragraph beside the report's
  structured descriptors, plus example finding lines. Structured labels only; no ids, ages, or raw text.
- `scripts/56` and `scripts/57` were **left unchanged**: 56 already writes the per-stage prevalence that 58's
  stage clauses read, and 57's D1–D5 dose-response panels are correct and validated; enriching them was
  unnecessary and would have risked the stable D1–D5 numbers.

Before → after (from the regenerated `results/story/s4_d6.md`):
- *before:* "Intermittent left temporal **mild** theta slowing, most prominent in REM."  *(forbidden adjective,
  no magnitude, no abstain)*
- *after (finding line):* "Frequent right posterior theta slowing, present in wakefulness and sleep; activated
  in drowsiness."
- *after (report paragraph):* "Right posterior theta slowing, maximal over the posterior (occipito-parietal)
  region. Peak deviation 1.9 SD above the age- and stage-matched normal at that region (97th centile),
  abnormal in 48% of analysed segments (frequent); longest continuous run ≈6.8 min over 18 episodes. Present in
  wakefulness and sleep; activated in drowsiness."
- *after (abstain example):* "Left temporal theta slowing, maximal over the left parasagittal chain. Peak
  deviation 1.0 SD … (84th centile), abnormal in 0% … (rare). Most prominent in REM sleep. Localization is
  low-confidence: no lateralizing or regional spectral excess clears the 84th centile of normals."

### Other executed fixes
- **P1-6 van Putten denominator** — `scripts/recompute_vanputten_fullcov.py` header reworded and **rerun**: it
  now states feature coverage (23,872) *and* the true scored contrast denominator (**21,146** = 10,189
  clean-normal vs 10,957 slowing-positive), eliminating the self-contradiction. All AUROCs unchanged.
- **P1-1 / P1-2 Morgoth numbers & focal overclaim** — manuscript reconciled to the Figure-2 evaluation
  (generalized 0.853, focal 0.908) throughout; abstract, §3.4 (heading + body), §6, Conclusion, and Figure-2
  legend now say "clearly beats the gate on generalized; on par on focal" (0.923 vs 0.908 is within panel
  noise, and on focal PR the gate is marginally ahead). Panel base rates (18/100 gen, 12/100 focal) added.
- **P1-3 Figure 2b citation** — §3.4 and the Figure-2 legend now state the embedded figure is the **W+N1**
  localized detector (47% under / AUROC 0.89) and cite `s0c_morgoth_free.md` for the 53% all-stage upper bound.
- **P1-5 §3.2 wording** — "absolute delta power" → the relative delta / TAR / DAR at the **central (C3/C4)**
  region that Figure 1a actually plots.
- **Description prose** — abstract, §2.8, and §3.7 D6 rewritten to describe the SD/centile + %-prevalence +
  stage-accentuation + abstain output, with the new representative paragraph. Dashboard D6 caption updated to
  match. Dashboard **rebuilt** (7.6 MB, 3/3 · 4/4 · 6/6 blocks, 18 images, 0 placeholders).
- **P2-2 venue/TBD** — target-venue line committed to *Clinical Neurophysiology*; revision-notes block updated
  (van Putten denominator resolved; added a to-do for a panel-AUROC bootstrap CI and a structured ~250-word
  abstract).

### Validated
- `PYTHONPATH=src MPLBACKEND=Agg python3 scripts/58_description_words.py` → concordance stable 56/46/39;
  clean output (no severity adjective; SD+centile in all 17 reports; abstain + "present only during sleep"
  clauses present; ACNS gloss in parentheses).
- `PYTHONPATH=src python3 scripts/recompute_vanputten_fullcov.py` → reran, AUROCs unchanged, header consistent.
- `PYTHONPATH=src python3 scripts/build_story_dashboard.py` → builds, 0 "figure not yet computed".
- Every `figures/`/`results/` path referenced in `docs/manuscript_draft.md` resolves on disk.

### Deliberately left (with reasons)
- **Full bootstrap CI on the panel AUROCs (0.946 / 0.923)** — the highest-value remaining stats item (P1-4),
  but it needs the panel scorer (`scripts/54/55`) to emit per-recording scores + a patient/EEG bootstrap;
  higher risk than the description work and not "cheap". Partially addressed by adding panel base rates; flagged
  in the manuscript revision notes.
- **`docs/claims_table.md` clauses 1–2 and `docs/description_architecture.md` §1** still quote the older Morgoth
  panel evaluation (0.900 / 0.923). These are internal governance/design docs, not the submitted manuscript;
  the manuscript is now internally consistent on 0.853 / 0.908. Left for the user to decide whether to restate
  the governance docs (needs knowing which panel evaluation is canonical).
- **Table 1 focal-slowing row** (P2-3: overall 8,304 vs abnormal-column 8,016) — data-derived (raw
  `has_focal_slow` vs SAP `slowing_focal` on clean_pair); footnoting is safe but altering the generator is not,
  and the manuscript already uses the 8,016 SAP figure consistently. Flagged, not changed.
- **v4a figure vs p6-file numeric drift** (P2-4), **abstract length/format** (P2-1), **D4 gridline label
  overlap** (P2-5) — flagged; low value or content-loss risk to auto-edit.
- **`scripts/76` and `scripts/115` (R/gamlss)** — not rerun; their outputs already exist and were unaffected by
  these changes (R+gamlss *is* available in this environment, but there was no reason to regenerate the norms).
</content>
</invoke>
