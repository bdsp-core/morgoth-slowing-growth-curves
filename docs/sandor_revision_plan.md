# Revision plan — Beniczky review (LENS_manuscript_2026-08-27.SB.docx)

17 comments on the 2026-08-27 draft. Each is listed with what we verified, the action, and how the action
is checked. Two are already resolved by edits made after he received his copy; those are marked and need
only confirmation in the next .docx we send.

**Closing step (mandatory):** `PYTHONPATH=src python3 scripts/certify_reproducibility.py --fresh` must
return CERTIFIED before the revised draft goes out. Every numeric change below flows through a producer, so
the certificate is what proves the manuscript still matches the code.

---

## A. The SAI-100 focal label question (comment 32) — highest priority

**His claim.** We used column K (`he_con_intictepifoc`, focal *epileptiform*) instead of column H/N
(`nonepifoc`, focal *non-epileptiform* = slowing), and our statement that his workbook is corrupted is wrong.

**What we verified (all three reproduce exactly):**

| check | result |
|---|---|
| `he_con_nonepifoc` (col N) vs the 11-rater individual majority | **100/100 agree** — his workbook is internally consistent |
| `he_con_intictepifoc` (col K) vs the focal-slowing majority | **23 disagreements, 10 one way / 13 the other** — exactly the pattern he predicted |
| our analysis's ground truth vs the true `nonepifoc` majority | **100/100 agree** (26 positives) |

**Conclusion: he is right about his data, and our results are unaffected.** The corrupted column is not in
`validation_study_excel_export.xlsx` at all. It is in the derived file we work from,
`Morgoth_results/FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx`, whose `majority` column matches the
*epileptiform* consensus 100/100 while its `expert_*` columns carry focal *slowing*. That internal
inconsistency is what we detected and mis-attributed to his export.
`scripts/sandor100_external_validation.py` never reads that column — it recomputes the majority from the
per-expert votes (`y = wide.mean(axis=1) >= 0.5`) — so Figure 3 and every SAI-100 focal number are scored
against the correct ground truth.

**Actions.**
1. Delete the "the workbook's focal summary label is corrupted" claim from §3.4b and the Figure 3 legend. It
   wrongly implicates his data.
2. Replace with an accurate, neutral note: the intermediate results workbook carried the epileptiform
   consensus in its summary column, so ground truth is recomputed from the per-expert votes.
3. Rename `docs/audits/sandor_focal_label_correction.csv` -> `sandor_focal_majority_recomputation.csv` and
   rewrite its header for the same reason.
4. Update the comment block at `scripts/sandor100_external_validation.py:116-118`, which still says the
   workbook is corrupted.
5. Reply to him with the column-level evidence (see the draft email) so the record is corrected on both sides.

**Check.** `certify` check C re-traces every SAI-100 number; Figure 3 must regenerate byte-identically,
since no label actually changes.

---

## B. Statistical rigour (comments 7, 8, 34, 35, 36)

**7 — the model-vs-expert comparison is asymmetric.** He is right, and this is the most substantive
methodological objection after age. The model gets a full ROC scored against the full-panel majority; each
expert gets a single operating point scored against a leave-one-out majority of the other readers. So the two
are not always measured against the same reference, a curve can have its threshold chosen retrospectively at
each specificity, and "% of experts under the curve" carries no uncertainty interval.

*Action.* (a) Score the model against the same leave-one-out majority each expert is scored against, so the
reference standard is identical, and report that alongside the current figure. (b) Put a bootstrap CI on the
"% of experts under the curve" statistic (resample recordings; experts are fixed). (c) Reword the claim: it
is a visualisation of relative standing, not a formal test that LENS matches or outperforms any individual
expert. State that explicitly.

**8, 34, 35, 36 — missing CIs and no test of differences.** CIs are given for LENS but not for Morgoth or
SCORE-AI, and no paired test supports "outperforms SCORE-AI on focal".

*Action.* Emit recording-level bootstrap CIs for **all three** models on both axes, and add a **paired**
bootstrap of the AUROC *difference* (same resamples for both models) with its CI and p-value, for
LENS-vs-SCORE-AI and LENS-vs-Morgoth on each axis. Producer: `scripts/sandor100_external_validation.py`
(SAI-100) and the ON-100 equivalent. Any comparative claim that the paired CI does not support gets softened.

**Check.** New numbers land in `results/sandor/sandor100_external.md`; certify check C traces them.

---

## C. Age as a possible shortcut (comment 14) — most substantive scientific point

Abnormal recordings are ~17 y older than clean-normals (Table 2). Deviations are age-normalised, but
chronological age is then fed directly into both logistic heads, so the classifier could recover the strong
age-label association and use age as a diagnostic shortcut rather than reading the deviation field.

*Action — run the ablations he asks for, as one new script (`scripts/112_age_ablation.py`):*
1. **age-only** baseline (age as the sole feature) on both axes, internal and both external sets;
2. **deviation-only** (age dropped from the heads);
3. **deviation + age** (current model);
4. **age-stratified** AUROC and calibration (decade bands);
5. **external performance after age matching / reweighting** on ON-100 and SAI-100.

Report all five even-handedly. If deviation-only is close to deviation+age, the claim that performance comes
from the deviation field stands and is now demonstrated. If age-only is strong, we say so plainly and scope
the claim. Pre-commit to reporting the outcome either way, as we did for the severity null.

**Check.** New `results/story/age_ablation.md`; add the script to `reproduce_story.sh` stage 4 so certify
check B sees it.

---

## D. Claims to soften (comments 19, 42)

**19 — "it does not depend on any label (it is fit to the normal population only)".** He is right: the normal
population is itself selected by the clinical report label, so the field is unsupervised only *conditional
on* a report-defined reference group.

*Action.* Rewrite to exactly that: "unsupervised conditional on a report-defined normal reference — the
scoring uses no labels, but the reference group is report-selected." Also sweep for any other "label-free"
phrasing.

**42 — "Readers under-report slowing in sleep".** He objects that the data do not demonstrate
under-reporting: reports still name slowing in 40% of patients where LENS finds it in neither wake nor sleep,
so "visible" is not a clean detection/no-detection partition, and slow-wave rebound, medication and
constitutional sleep depth may explain some deviations. He proposes: *"Sleep-confined LENS deviations are
less often mentioned in clinical reports."*

*Action.* Adopt his wording for the section heading and the claim, and keep the mechanistic evidence
(spindle-verified N2, sleep-verified N3) as support for the deviations being real rather than for reader
error. This is consistent with §2.11, which already declines to call a deviation a diagnosis. Add his
reference (Clin Neurophysiol 1997, low specificity of focal slowing in sleep) as the clinical explanation
for why readers may deliberately not report it.

---

## E. Internal consistency (comments 6, 13) — already fixed, confirm only

**6 — "we fitted".** His copy says the norm-fitting reference is "every clean-normal, cleanly paired
recording with a known age (10,216)", while Methods says a seeded 3,000-recording sample with 7,216 held out.
Verified: `scripts/115` line 407 caps the fitting set at a seeded 3,000, so 10,216 is the *pool*, not the
fitting set, and his reading of the contradiction was correct. **The current draft no longer contains
"10,216"** — the sentence was rewritten when the split was made reproducible, and 3,000 / 7,216 / 6,779 are
now emitted by `scripts/78`. Confirm in the next .docx.

**13 — "a physiologic-slowing recording never enters the clean-normal reference".** Contradicted by Table 1,
which shows 3,009 physiologic-generalized recordings in the clean-normal column; the data give 3,045.
**That sentence is not in the current draft**, which says physiologic generalized slowing "is left in the
clean-normal reference" — the correct statement. Confirm, and make the two numbers explicit (3,382 total,
3,009 in the clean-normal column) so the relationship is unambiguous.

---

## F. Editorial (comments 1, 3, 4)

**1 — length and register.** Main text is **11,737 words**, far over what *Clinical Neurophysiology* takes,
and it reads as an internal project report: dataset paths, script numbers and file names in running text.

*Action.* (a) Answer his question: target journal is *Clinical Neurophysiology*. (b) Strip every
`scripts/NN`, `results/...` and `data/...` path from the main text into a supplementary "code and data map"
— the certifier keeps the mapping honest, so the prose does not need to carry it. (c) Compress Methods hard,
moving detail to supplement. (d) Target ~6,000 words. This is the largest single task and should be done
**last**, after B, C and D settle the content.

**3 — "beats" -> "outperforms"** throughout. **4 — "at two external sites" -> "in two external datasets."**

---

## G. References to add (comments 10, 39)

Comment 10, lifespan/normative qEEG: doi 10.1016/j.jneumeth.2011.06.008; 10.1016/j.cnp.2020.11.001;
10.1371/journal.pone.0085966; 10.1016/j.clinph.2012.07.007.
Comment 39, consistent with our human-ceiling result: 10.1001/jamaneurol.2023.1645; 10.1111/epi.18082.
Comment 42, sleep-slowing specificity: 10.1016/s0013-4694(97)00083-7.
Renumber with `scripts/renumber_display_items.py` so citation order stays correct.

---

## H. Data request (comment 33)

He asks which recordings we could not read, so his group can re-export and we can use n = 100.
**They are `ID060` and `ID086`** (our `SB_060`, `SB_086`; 98/100 currently featurized). Send these in the
reply. When the re-export arrives: re-run `sandor100_stage_extract` -> `sandor100_external_validation`,
update every SAI-100 number from 98 to 100, and re-certify.

---

## Order of work

1. **A** (label statement) and **H** (send the two IDs) — both unblock him, today.
2. **C** (age ablations) — changes what we can claim; run before rewriting.
3. **B** (CIs, paired tests, symmetric expert comparison) — changes numbers.
4. **D**, **E**, **G** — wording, confirmations, references.
5. **F** (compression to ~6,000 words) — last, once content is final.
6. **Re-certify:** `scripts/certify_reproducibility.py --fresh` -> CERTIFIED, then rebuild the .docx.
