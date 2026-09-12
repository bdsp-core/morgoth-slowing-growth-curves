M. Brandon Westover, MD, PhD
Department of Neurology and Neurological Sciences
Stanford University School of Medicine
Stanford, CA, USA
mbwest@stanford.edu

12 September 2026

The Editors
*Clinical Neurophysiology*

Dear Editors,

Please consider the enclosed Original Article, **"Lifespan and sleep-stage-resolved normative EEG
background: deviation-from-normal detection and automated reporting of slowing,"** for publication in
*Clinical Neurophysiology*.

Background slowing is among the most frequently reported findings in clinical EEG and among the least
reliably judged. It is also the finding for which normative reference data are weakest: published norms rest
on small, predominantly awake samples, so the reader deciding whether a given record is abnormal for a
4-month-old in N3, or for an 80-year-old in wakefulness, has little quantitative footing.

We address this with LENS (Lifespan EEG Normative Scoring). From 25,536 clinical EEGs in 21,757 patients
spanning infancy to over 90 years, we estimated age x sleep-stage percentile curves for spectral power and
its ratios, and scored every 15-second segment as a deviation from its own age- and stage-matched normal.
The resulting deviation field is a single intermediate representation from which both detection and
structured description follow. We believe four points will interest your readership:

1. **The norms are lifespan- and sleep-stage-resolved.** The curves recover known maturation and aging and
   quantify the stage-dependence of physiological slowing (W = N1 < N2 < N3), so an EEG is judged against
   the right normal rather than an adult waking average.

2. **Detection was validated externally, twice, against multi-expert panels.** On ON-100 (100 EEGs from five
   US centers, 18 readers) LENS reached AUROC 0.961 for generalized and 0.908 for focal slowing. On SAI-100,
   the holdout set of the SCORE-AI validation study (three hospitals in two countries, a 14-reader pool with
   11 calls per recording), it reached 0.930 focal and 0.908 generalized, comparable to SCORE-AI itself with
   no site-specific refitting. No parameter or threshold was tuned on either panel.

3. **We quantify the human ceiling rather than assume it.** Between-rater agreement for slowing was
   kappa 0.373 (focal) and 0.450 (generalized), well below the same panel's agreement on epileptiform
   discharges, and readers re-reading their own records reproduced their slowing calls at kappa 0.563/0.642.
   This bounds every "agreement with the report" figure in this literature, including ours, and is why we
   evaluate against panel majorities and place individual readers on the model's ROC curve.

4. **It sees what reports omit.** Slowing confined to sleep was named in 54% of reports versus 75% when
   present in wakefulness, precisely the regime where visual reading is hardest and where a stage-aware
   normative measure helps most.

We have also tried to make the work verifiable. The de-identified derived data are published on the Brain
Data Science Platform (LENS v1.1.0, DOI 10.60508/1aw8-tk12) under a credentialed data use agreement, the
analysis code is public at github.com/bdsp-core/morgoth-slowing-growth-curves, and the repository carries an
automated certificate confirming that every figure, table and numerical claim in the manuscript regenerates
from that release on a clean installation.

We report negative and null results alongside the positive ones: severity grading is a null result, band
determination (delta/theta/mixed) is near chance and we do not claim it, and on SAI-100 none of the
differences between LENS, SCORE-AI and the foundation-model comparator reaches significance, which we state
plainly rather than selecting a favourable comparison.

Given its focus on standardizing and quantifying routine EEG interpretation, and its direct engagement with
the SCORE and SCORE-AI line of work, we believe this manuscript is well suited to *Clinical
Neurophysiology* and its IFCN readership.

This manuscript is original, has not been published previously, and is not under consideration elsewhere.
All authors have read and approved the submitted version and agree to its submission. The work was
conducted under IRB protocol 2022P000417 (Beth Israel Deaconess Medical Center), with a waiver of consent.
Conflicts of interest and funding are disclosed in full in the manuscript; in brief, Dr. Westover is a
co-founder of, advisor and consultant to, and holds equity in Beacon Biosignals, and the remaining authors
declare no competing interests.

We note that Dr. Sandor Beniczky is a co-author on this manuscript. We leave it entirely to the editorial
office to assign independent handling and review as your policy requires, and none of the authors should
have any role in the editorial evaluation of this submission.

Thank you for your consideration.

Sincerely,

M. Brandon Westover, MD, PhD
on behalf of all co-authors
