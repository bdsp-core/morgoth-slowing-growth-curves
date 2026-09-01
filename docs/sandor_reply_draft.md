# Draft reply to Sándor Beniczky

*Subject: RE: Slowing paper — the focal column, and the two recordings*

---

Dear Sandor,

Thank you — this is an exceptionally useful review, and you were right on the point that mattered most.

**The two recordings are ID060 and ID086.** If you are able to re-export those we will re-run the full
pipeline and report SAI-100 on all 100.

**On the focal column.** We checked your workbook against your description and your diagnosis reproduces
exactly. In "Raters aggregated", `he_con_nonepifoc` (column N) agrees with the majority of the 11 individual
`nonepifoc` ratings on 100 of 100 recordings, so your export is internally consistent and our statement that
it was corrupted is wrong. We will remove it. I am sorry it went out in that form.

We also found where our confusion came from, and it was not your file. We did not read the focal labels from
`validation_study_excel_export.xlsx` directly; we read them from the derived workbook we were working from,
`Morgoth_results/FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx`. That file is internally inconsistent: its
per-expert columns carry focal non-epileptiform ratings, but its single `majority` column matches
`he_con_intictepifoc` — the focal *interictal epileptiform* consensus — on 100 of 100 recordings. Comparing
that column against the focal-slowing majority reproduces precisely the pattern you predicted: 23
disagreements, 10 in one direction and 13 in the other. So you identified the exact mechanism; it was one
step downstream of your export.

The one piece of good news is that this did not reach the results. Our analysis script never uses that
summary column — it recomputes the majority from the individual expert votes — and that recomputed majority
agrees with the correct `nonepifoc` majority on 100 of 100 recordings (26 positives). Figure 3 and all
SAI-100 focal numbers are therefore scored against the correct focal non-epileptiform ground truth. We will
still fix the text, the audit file and the code comment, all of which describe the cause wrongly.

**On your other comments,** we are taking essentially all of them:

- *Asymmetric model-versus-expert comparison.* This is fair and we had not stated the limitation. We will
  additionally score the model against the same leave-one-out majority each expert is scored against, put a
  bootstrap interval on the "percentage of experts under the curve", and reword the claim as a visualisation
  of relative standing rather than a formal test against any individual reader.
- *Missing intervals and no test of differences.* We will report bootstrap CIs for SCORE-AI and the Morgoth
  gate as well as LENS, and add a paired bootstrap of the AUROC difference so any comparative claim is
  supported by an interval rather than by point estimates.
- *Age as a possible shortcut.* This is the sharpest scientific comment and we are running the analyses you
  suggest: age-only, deviation-only, deviation-plus-age, age-stratified AUROC and calibration, and external
  performance after age matching. We will report the outcome whichever way it falls, including if it bounds
  the claim that performance comes from the deviation field.
- *"Does not depend on any label."* You are correct — the normal reference group is itself report-selected.
  We will describe the field as unsupervised conditional on a report-defined normal reference.
- *Under-reporting in sleep.* We accept the criticism and will adopt your phrasing, that sleep-confined LENS
  deviations are less often mentioned in clinical reports, and drop the stronger reading. Thank you also for
  the 1997 reference on the low specificity of focal slowing in sleep; that is a better explanation than ours
  for why readers may deliberately not report it.
- *Length and register.* Agreed, and this is the biggest job. The target is *Clinical Neurophysiology*. We
  will strip the script and dataset paths out of the running text into a supplement and compress the Methods
  substantially.
- *"Beats" -> "outperforms"*, "in two external datasets", the internal inconsistencies you flagged in the
  fitting set and the physiologic-slowing sentence (both already corrected in our working draft), and your
  suggested references — all taken.

We will send a revised draft once the age analyses and the paired comparisons are done.

Thank you again for reading it this carefully, and for re-checking the database on your side.

Best wishes,
Brandon
